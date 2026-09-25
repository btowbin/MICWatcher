"""Monitor an acquisition folder and email when image production stops."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import smtplib
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Iterable


LOG = logging.getLogger("microscope_watcher")
DEFAULT_CONFIG = "watcher_config.json"
DEFAULT_STATE = "watcher_state.json"


def now_local() -> datetime:
    return datetime.now().astimezone()


def parse_timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if size < 1024 or unit == "PiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    security: str
    username: str
    password_env: str
    password: str
    from_address: str
    to_addresses: tuple[str, ...]
    timeout_seconds: float


@dataclass(frozen=True)
class Config:
    microscope_name: str
    watch_folder: Path
    recursive: bool
    check_interval_seconds: float
    daily_report_interval_hours: float
    state_file: Path
    log_file: Path
    email: EmailConfig


@dataclass(frozen=True)
class FolderSnapshot:
    file_count: int
    newest_mtime_ns: int
    newest_file: str | None


def _require(mapping: dict[str, Any], key: str, location: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing required setting: {location}.{key}")
    return mapping[key]


def load_config(path: Path) -> Config:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Configuration file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    email = _require(raw, "email", "config")
    base = path.resolve().parent

    def config_path(value: str) -> Path:
        candidate = Path(os.path.expandvars(os.path.expanduser(value)))
        return candidate if candidate.is_absolute() else base / candidate

    recipients = _require(email, "to_addresses", "email")
    if isinstance(recipients, str):
        recipients = [recipients]
    if not recipients:
        raise ValueError("email.to_addresses must contain at least one address")

    result = Config(
        microscope_name=str(raw.get("microscope_name", socket.gethostname())),
        watch_folder=config_path(str(_require(raw, "watch_folder", "config"))),
        recursive=bool(raw.get("recursive", True)),
        check_interval_seconds=float(raw.get("check_interval_seconds", 300)),
        daily_report_interval_hours=float(raw.get("daily_report_interval_hours", 24)),
        state_file=config_path(str(raw.get("state_file", DEFAULT_STATE))),
        log_file=config_path(str(raw.get("log_file", "microscope_watcher.log"))),
        email=EmailConfig(
            smtp_host=str(_require(email, "smtp_host", "email")),
            smtp_port=int(email.get("smtp_port", 587)),
            security=str(email.get("security", "starttls")).lower(),
            username=str(email.get("username", "")),
            password_env=str(email.get("password_env", "MICROSCOPE_WATCHER_SMTP_PASSWORD")),
            password=str(email.get("password", "")),
            from_address=str(_require(email, "from_address", "email")),
            to_addresses=tuple(str(item) for item in recipients),
            timeout_seconds=float(email.get("timeout_seconds", 30)),
        ),
    )
    if result.check_interval_seconds <= 0:
        raise ValueError("check_interval_seconds must be greater than zero")
    if result.daily_report_interval_hours <= 0:
        raise ValueError("daily_report_interval_hours must be greater than zero")
    if result.email.security not in {"starttls", "ssl", "none"}:
        raise ValueError("email.security must be one of: starttls, ssl, none")
    return result


def iter_files(folder: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for root, _, names in os.walk(folder):
            for name in names:
                yield Path(root) / name
    else:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_file(follow_symlinks=False):
                    yield Path(entry.path)


def scan_folder(folder: Path, recursive: bool) -> FolderSnapshot:
    count = 0
    newest_ns = 0
    newest_file: str | None = None
    for path in iter_files(folder, recursive):
        try:
            stat = path.stat()
        except (FileNotFoundError, PermissionError, OSError) as exc:
            LOG.warning("Could not inspect %s: %s", path, exc)
            continue
        count += 1
        if stat.st_mtime_ns > newest_ns:
            newest_ns = stat.st_mtime_ns
            newest_file = str(path)
    return FolderSnapshot(count, newest_ns, newest_file)


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        LOG.warning("Cannot read state file %s; starting fresh: %s", path, exc)
        return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(temporary, path)


class Mailer:
    def __init__(self, config: EmailConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run

    def send(self, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.config.from_address
        message["To"] = ", ".join(self.config.to_addresses)
        message.set_content(body)

        if self.dry_run:
            LOG.info("DRY RUN email\nSubject: %s\nTo: %s\n\n%s", subject, message["To"], body)
            return

        password = self.config.password or os.environ.get(self.config.password_env, "")
        if self.config.username and not password:
            raise RuntimeError(
                "No SMTP password is configured. Set email.password in the configuration "
                f"or define the {self.config.password_env!r} environment variable."
            )

        smtp_type = smtplib.SMTP_SSL if self.config.security == "ssl" else smtplib.SMTP
        kwargs: dict[str, Any] = {"timeout": self.config.timeout_seconds}
        if self.config.security == "ssl":
            kwargs["context"] = ssl.create_default_context()
        with smtp_type(self.config.smtp_host, self.config.smtp_port, **kwargs) as smtp:
            if self.config.security == "starttls":
                smtp.starttls(context=ssl.create_default_context())
            if self.config.username:
                smtp.login(self.config.username, password)
            smtp.send_message(message)


class Watcher:
    def __init__(
        self,
        config: Config,
        mailer: Mailer,
        clock: Callable[[], datetime] = now_local,
    ):
        self.config = config
        self.mailer = mailer
        self.clock = clock
        self.state = load_state(config.state_file)

    def _send(self, subject: str, body: str) -> bool:
        try:
            self.mailer.send(subject, body)
            LOG.info("Sent email: %s", subject)
            return True
        except Exception:
            LOG.exception("Failed to send email: %s", subject)
            return False

    def _is_activity(self, snapshot: FolderSnapshot) -> bool:
        old_count = self.state.get("file_count")
        old_mtime = self.state.get("newest_mtime_ns")
        if old_count is None or old_mtime is None:
            return False
        return snapshot.file_count > int(old_count) or snapshot.newest_mtime_ns > int(old_mtime)

    def check_once(self) -> None:
        observed_at = self.clock()
        try:
            snapshot = scan_folder(self.config.watch_folder, self.config.recursive)
        except (FileNotFoundError, PermissionError, OSError) as exc:
            LOG.error("Cannot scan watched folder %s: %s", self.config.watch_folder, exc)
            snapshot = None

        initialized = "last_check_at" in self.state
        activity = snapshot is not None and self._is_activity(snapshot)
        last_activity = parse_timestamp(self.state.get("last_activity_at"))
        inactivity_due = (
            initialized
            and last_activity is not None
            and (observed_at - last_activity).total_seconds()
            >= self.config.check_interval_seconds
        )

        if snapshot is not None:
            if not initialized or activity:
                self.state["last_activity_at"] = observed_at.isoformat()
                self.state["last_activity_file"] = snapshot.newest_file

            was_stalled = bool(self.state.get("stalled", False))
            if initialized and activity and was_stalled:
                subject = f"[RECOVERED] {self.config.microscope_name}: images arriving again"
                body = (
                    f"Image acquisition for {self.config.microscope_name} has resumed.\n\n"
                    f"Folder: {self.config.watch_folder}\n"
                    f"Activity observed: {format_timestamp(observed_at)}\n"
                    f"Newest file: {snapshot.newest_file or 'unknown'}\n"
                    f"Current file count: {snapshot.file_count:,}\n"
                )
                if self._send(subject, body):
                    self.state["stalled"] = False
            elif inactivity_due and not activity:
                subject = f"[WARNING] {self.config.microscope_name}: no new images"
                body = (
                    f"No new or updated image files were detected for {self.config.microscope_name} "
                    f"during the latest check interval.\n\n"
                    f"Folder: {self.config.watch_folder}\n"
                    f"Last activity observed: {format_timestamp(last_activity)}\n"
                    f"Last active file: {self.state.get('last_activity_file') or 'unknown'}\n"
                    f"Checked at: {format_timestamp(observed_at)}\n"
                    f"Current file count: {snapshot.file_count:,}\n\n"
                    "Another warning will be sent after the next interval if acquisition does not resume."
                )
                self._send(subject, body)
                self.state["stalled"] = True

            self.state["file_count"] = snapshot.file_count
            self.state["newest_mtime_ns"] = snapshot.newest_mtime_ns
            self.state["newest_file"] = snapshot.newest_file
        elif initialized:
            subject = f"[WARNING] {self.config.microscope_name}: acquisition folder unavailable"
            body = (
                f"The acquisition folder for {self.config.microscope_name} could not be read.\n\n"
                f"Folder: {self.config.watch_folder}\n"
                f"Last activity observed: {format_timestamp(parse_timestamp(self.state.get('last_activity_at')))}\n"
                f"Checked at: {format_timestamp(observed_at)}\n"
            )
            self._send(subject, body)
            self.state["stalled"] = True

        self._maybe_send_daily_report(observed_at, snapshot)
        self.state["last_check_at"] = observed_at.isoformat()
        save_state(self.config.state_file, self.state)

    def _maybe_send_daily_report(
        self, observed_at: datetime, snapshot: FolderSnapshot | None
    ) -> None:
        last_report = parse_timestamp(self.state.get("last_report_at"))
        interval = timedelta(hours=self.config.daily_report_interval_hours)
        if last_report is not None and observed_at - last_report < interval:
            return

        try:
            usage = shutil.disk_usage(self.config.watch_folder)
            disk_text = (
                f"Free disk space: {human_bytes(usage.free)}\n"
                f"Total disk space: {human_bytes(usage.total)}\n"
                f"Disk used: {(usage.used / usage.total * 100) if usage.total else 0:.1f}%"
            )
        except OSError as exc:
            disk_text = f"Disk space: unavailable ({exc})"

        count_text = f"{snapshot.file_count:,}" if snapshot is not None else "unavailable"
        status = "STALLED" if self.state.get("stalled") else "OK"
        subject = f"[DAILY REPORT] {self.config.microscope_name}: {status}"
        body = (
            f"24-hour acquisition report for {self.config.microscope_name}\n\n"
            f"Status: {status}\n"
            f"Folder: {self.config.watch_folder}\n"
            f"Number of files: {count_text}\n"
            f"Last activity observed: {format_timestamp(parse_timestamp(self.state.get('last_activity_at')))}\n"
            f"{disk_text}\n"
            f"Report generated: {format_timestamp(observed_at)}\n"
        )
        if self._send(subject, body):
            self.state["last_report_at"] = observed_at.isoformat()


def configure_logging(log_file: Path, verbose: bool) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except OSError as exc:
        print(f"Warning: cannot open log file {log_file}: {exc}", file=sys.stderr)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(DEFAULT_CONFIG))
    parser.add_argument("--once", action="store_true", help="Perform one check and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log emails instead of sending them")
    parser.add_argument("--test-email", action="store_true", help="Send one test email and exit")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    configure_logging(config.log_file, args.verbose)
    mailer = Mailer(config.email, dry_run=args.dry_run)

    if args.test_email:
        try:
            mailer.send(
                f"[TEST] {config.microscope_name}: watcher email test",
                f"The email configuration for {config.microscope_name} is working.\n"
                f"Watched folder: {config.watch_folder}\n",
            )
            LOG.info("Test email sent successfully")
            return 0
        except Exception:
            LOG.exception("Test email failed")
            return 1

    watcher = Watcher(config, mailer)
    if args.once:
        watcher.check_once()
        return 0

    LOG.info(
        "Watching %s every %.1f seconds for %s",
        config.watch_folder,
        config.check_interval_seconds,
        config.microscope_name,
    )
    while True:
        started = time.monotonic()
        try:
            watcher.check_once()
        except Exception:
            LOG.exception("Unexpected error during check; watcher will continue")
        elapsed = time.monotonic() - started
        try:
            time.sleep(max(1.0, config.check_interval_seconds - elapsed))
        except KeyboardInterrupt:
            LOG.info("Watcher stopped")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
