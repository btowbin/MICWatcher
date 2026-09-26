# Microscope acquisition watcher

A dependency-free Python program for monitoring long-running microscope acquisitions. It checks whether new or updated files appear, emails a warning after each inactive interval, sends a recovery notice when acquisition resumes, and sends a disk/file-count report every 24 hours.

Each microscope runs its own copy with its own name, acquisition folder, interval, recipients, and persistent state.

## Requirements

- Ubuntu Linux
- Python 3.10 or newer
- Python Tk support (`python3-tk`) for the graphical launcher
- A Gmail account with 2-Step Verification and a generated app password

No third-party Python packages are required. Ubuntu may not install Tk support by default; if it is missing, an administrator must run `sudo apt install python3-tk` once. Normal installation and operation do not require administrator rights.

## Download and configure

Once this repository is published, run on the microscope computer:

```bash
git clone https://github.com/btowbin/MICWatcher.git
cd MICWatcher
cp watcher_config.example.json watcher_config.json
nano watcher_config.json
```

Configure:

- `microscope_name`: a unique, recognizable microscope name.
- `watch_folder`: the Linux acquisition path, for example `/data/acquisition/images`.
- `check_interval_seconds`: longer than the normal maximum gap between images.
- `username` and `from_address`: the watcher Gmail address.
- `password`: the generated Google app password.
- `to_addresses`: one or more alert recipients.
- `transfer.enabled`: set to `true` to move stable new files to network storage.
- `transfer.destination_folder`: the mounted network-drive destination for this microscope.
- `transfer.check_interval_seconds`: how often transfer candidates are checked, independently of acquisition alarms.
- `transfer.stable_for_seconds`: how long a file must remain unchanged before copying.
- `transfer.max_files_per_check`: optional per-check limit; `null` means no limit.
- `transfer.max_untransferred_files`: backlog safety limit; the default is 10,000.

Keep the Gmail SMTP settings as supplied in the example. Protect the local configuration containing the app password:

```bash
chmod 600 watcher_config.json
```

`watcher_config.json` is excluded from Git, so local credentials and microscope-specific settings are never committed or overwritten by updates.

## Verify the configuration

Print emails without sending them:

```bash
python3 microscope_watcher.py --once --dry-run
```

Send a real test email:

```bash
python3 microscope_watcher.py --test-email
```

The first real check establishes a baseline and does not send an inactivity warning. It does send the initial daily report. A file counts as activity when the folder's file count increases or the newest file's modification time advances; this also recognizes acquisition formats that continually append to one file.

## Optional network transfer

Mount the network drive through Ubuntu first, then enable transfer in `watcher_config.json`:

```json
"transfer": {
  "enabled": true,
  "destination_folder": "/mnt/network-drive/microscope-1",
  "check_interval_seconds": 300,
  "stable_for_seconds": 60,
  "max_files_per_check": null,
  "max_untransferred_files": 10000
}
```

Files already present when MICWatcher starts are included, as are files created later. A candidate must be unchanged across checks for at least `stable_for_seconds`. The watcher preserves its path relative to the acquisition folder, copies its contents through a bounded buffer to a `.micwatcher-part` file, confirms that the source did not change and that sizes match, finalizes the destination, and only then deletes the local source. It does not attempt to copy Unix metadata, which keeps it compatible with GVFS/FUSE network mounts.

If copying or local deletion fails, the source is retained and one warning email is sent. Repeated failures remain silent. A single recovery email is sent after a later file transfers successfully. The daily report includes transfer status, pending count, total transferred count, last success, and any active error.

Use a destination unique to each microscope. The destination must not be inside the watched folder. By default there is no per-check transfer count limit, so every stable candidate is processed. A numeric `max_files_per_check` can still be configured when deliberate throttling is needed.

If the number of untransferred local files exceeds `max_untransferred_files` (10,000 by default), MICWatcher sends a `[SAFETY STOP]` email, saves its state, retains every local file, and exits. Resolve the network or backlog problem before restarting it.

## Install the graphical desktop launcher

Install it once for the current Ubuntu account; administrator rights are not required:

```bash
cd ~/MICWatcher
python3 install_desktop_launcher.py
```

Double-click **MICWatcher** on the desktop, or open it from the Applications menu. A graphical window lets operators:

- Enter the alert recipient.
- Type a folder path or select it with **Browse...**.
- Set the missing-file and transfer intervals.
- Enable or disable network transfer.
- Start and stop monitoring.
- See acquisition, file-count, transfer, and error status.

Keep the GUI open while the experiment is running. Closing it while monitoring asks for confirmation and stops safely after the current check or file copy finishes. Existing Gmail credentials and microscope identity remain unchanged.

The missing-file check defaults to 60 minutes, the transfer check defaults to 30 minutes, and the transfer destination has no default. See [LAUNCHER_GUIDE.md](LAUNCHER_GUIDE.md) for the complete operator workflow, including browsing or copying local and network paths from Ubuntu Files.

The installer verifies that Tkinter is available and prints the required `python3-tk` installation command if it is missing. Run the installer again after moving the repository to another path. If Ubuntu marks the desktop icon untrusted, right-click it and select **Allow Launching**.

## Start and stop manually

Start the watcher when an experiment begins:

```bash
cd ~/microscope-watcher
python3 microscope_watcher.py
```

Keep the terminal open. Stop it with Ctrl+C.

To let it continue after closing the terminal:

```bash
cd ~/microscope-watcher
nohup python3 microscope_watcher.py > watcher-console.log 2>&1 &
echo $! > watcher.pid
```

Stop that background process with:

```bash
kill "$(cat ~/microscope-watcher/watcher.pid)"
```

## Operations

- `microscope_watcher.log` records activity and email failures.
- `watcher_state.json` preserves activity, alert, and report state across restarts.
- At most two inactivity warnings are sent for one interruption. Further checks remain silent until a recovery email reports that files are appearing again.
- A separate warning is sent when the acquisition folder cannot be read.
- Failed email delivery is retried on a later check.
- The daily report gives file count and free/total disk space.
- When enabled, network-transfer health and progress are included in the daily report.
- Temporarily lower `daily_report_interval_hours` to test daily reporting.

## Update an installed copy

Local configuration is preserved during updates:

```bash
cd ~/MICWatcher
git pull
python3 install_desktop_launcher.py
```

Rerunning the installer refreshes the desktop/Application launcher and does not overwrite `watcher_config.json`.

## Run automated tests

```bash
python3 -m unittest discover -s tests -v
```
