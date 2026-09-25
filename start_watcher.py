"""Interactive operator launcher for MICWatcher."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from microscope_watcher import load_config, main as watcher_main


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "watcher_config.json"
EXAMPLE_CONFIG_PATH = ROOT / "watcher_config.example.json"


def prompt_text(label: str, default: str) -> str:
    while True:
        value = input(f"{label} [{default}]: ").strip() or default
        if value:
            return value
        print("Please enter a value.")


def prompt_minutes(label: str, default_seconds: float) -> float:
    default_minutes = default_seconds / 60
    default_text = f"{default_minutes:g}"
    while True:
        value = input(f"{label}, in minutes [{default_text}]: ").strip() or default_text
        try:
            minutes = float(value)
            if minutes > 0:
                return minutes * 60
        except ValueError:
            pass
        print("Enter a number greater than zero, for example 5 or 60.")


def prompt_yes_no(label: str, default: bool) -> bool:
    marker = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} [{marker}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Enter Y or N.")


def expanded_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def running_watcher() -> str | None:
    try:
        result = subprocess.run(
            ["pgrep", "-af", "microscope_watcher.py"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return "\n".join(lines) if lines else None


def load_editable_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        shutil.copyfile(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict[str, Any]) -> None:
    temporary = CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, CONFIG_PATH)
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass


def configure() -> bool:
    config = load_editable_config()
    original_watch_folder = expanded_path(str(config.get("watch_folder", "/data")))
    email = config.setdefault("email", {})
    recipients = email.get("to_addresses") or [""]
    current_recipient = recipients[0] if isinstance(recipients, list) else str(recipients)
    transfer = config.setdefault("transfer", {})

    print("\nMICWatcher experiment setup")
    print("Press Enter to keep the value shown in brackets.\n")
    recipient = prompt_text("Alert email address", current_recipient)
    while "@" not in recipient:
        print("Enter a valid email address.")
        recipient = prompt_text("Alert email address", current_recipient)

    watch_folder = expanded_path(
        prompt_text("Local acquisition folder", str(config.get("watch_folder", "/data")))
    )
    if not watch_folder.is_dir():
        print(f"\nCannot start: local folder does not exist: {watch_folder}")
        return False
    if not os.access(watch_folder, os.R_OK):
        print(f"\nCannot start: local folder is not readable: {watch_folder}")
        return False

    acquisition_interval = prompt_minutes(
        "Check interval for missing new files",
        float(config.get("check_interval_seconds", 3600)),
    )
    transfer_enabled = prompt_yes_no(
        "Transfer stable files to a network folder",
        bool(transfer.get("enabled", False)),
    )

    destination: Path | None = None
    transfer_interval = float(
        transfer.get("check_interval_seconds", config.get("check_interval_seconds", 300))
    )
    if transfer_enabled:
        destination = expanded_path(
            prompt_text(
                "Transfer destination folder",
                str(transfer.get("destination_folder", "/mnt/network-drive/microscope-1")),
            )
        )
        if not destination.is_dir():
            print(f"\nCannot start: transfer destination is not mounted or does not exist: {destination}")
            return False
        if not os.access(destination, os.W_OK):
            print(f"\nCannot start: transfer destination is not writable: {destination}")
            return False
        transfer_interval = prompt_minutes(
            "File-transfer check interval",
            transfer_interval,
        )

    email["to_addresses"] = [recipient]
    config["watch_folder"] = str(watch_folder)
    config["check_interval_seconds"] = acquisition_interval
    transfer["enabled"] = transfer_enabled
    transfer["check_interval_seconds"] = transfer_interval
    if destination is not None:
        transfer["destination_folder"] = str(destination)
    transfer.setdefault("stable_for_seconds", 60)
    transfer.setdefault("max_files_per_check", 10)
    save_config(config)

    if watch_folder != original_watch_folder:
        state_value = Path(str(config.get("state_file", "watcher_state.json")))
        state_path = state_value if state_value.is_absolute() else ROOT / state_value
        if state_path.exists():
            previous_state = state_path.with_suffix(state_path.suffix + ".previous")
            os.replace(state_path, previous_state)
            print(f"Previous experiment state archived as {previous_state.name}.")

    try:
        load_config(CONFIG_PATH)
    except ValueError as exc:
        print(f"\nConfiguration error: {exc}")
        return False

    print("\nConfiguration saved.")
    print(f"  Alert recipient: {recipient}")
    print(f"  Local folder: {watch_folder}")
    print(f"  Missing-file check: every {acquisition_interval / 60:g} minutes")
    print(f"  Transfer enabled: {'yes' if transfer_enabled else 'no'}")
    if transfer_enabled:
        print(f"  Destination: {destination}")
        print(f"  Transfer check: every {transfer_interval / 60:g} minutes")
        print("  Existing stable files will also be transferred.")
    return True


def main() -> int:
    existing = running_watcher()
    if existing:
        print("MICWatcher is already running. Stop it before starting another copy:\n")
        print(existing)
        input("\nPress Enter to close this window.")
        return 1
    try:
        if not configure():
            input("\nPress Enter to close this window.")
            return 2
        input("\nPress Enter to start MICWatcher. Leave this terminal open; use Ctrl+C to stop.")
        return watcher_main(["--config", str(CONFIG_PATH)])
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 130
    except (OSError, json.JSONDecodeError) as exc:
        print(f"\nSetup failed: {exc}")
        input("Press Enter to close this window.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
