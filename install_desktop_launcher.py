"""Install the per-account Ubuntu graphical launcher for MICWatcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LAUNCHER_SCRIPT = ROOT / "micwatcher_gui.py"


def desktop_directory() -> Path:
    try:
        result = subprocess.run(
            ["xdg-user-dir", "DESKTOP"],
            check=True,
            capture_output=True,
            text=True,
        )
        value = result.stdout.strip()
        if value:
            return Path(value)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return Path.home() / "Desktop"


def launcher_contents() -> str:
    python = Path(sys.executable).resolve()
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=MICWatcher\n"
        "Comment=Configure and start microscope monitoring\n"
        f'Exec="{python}" "{LAUNCHER_SCRIPT}"\n'
        f"Path={ROOT}\n"
        "Terminal=false\n"
        "Icon=utilities-system-monitor\n"
        "Categories=Utility;Science;\n"
        "StartupNotify=true\n"
    )


def install_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


def main() -> int:
    tkinter_check = subprocess.run(
        [sys.executable, "-c", "import tkinter"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if tkinter_check.returncode != 0:
        print("MICWatcher needs Ubuntu's Python Tk package for its graphical interface.")
        print("Ask an administrator to run: sudo apt install python3-tk")
        return 2
    if not LAUNCHER_SCRIPT.is_file():
        print(f"GUI launcher script not found: {LAUNCHER_SCRIPT}")
        return 2

    contents = launcher_contents()
    application = Path.home() / ".local/share/applications/micwatcher.desktop"
    install_file(application, contents)

    desktop = desktop_directory()
    desktop_launcher = desktop / "MICWatcher.desktop"
    if desktop.is_dir():
        install_file(desktop_launcher, contents)
        try:
            subprocess.run(
                ["gio", "set", str(desktop_launcher), "metadata::trusted", "true"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        print(f"Desktop launcher installed: {desktop_launcher}")
    else:
        print("Desktop folder was not found; use the MICWatcher entry in Applications.")

    print(f"Applications launcher installed: {application}")
    print("If Ubuntu shows an untrusted-launcher warning, right-click the icon and select Allow Launching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
