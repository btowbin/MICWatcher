# Microscope acquisition watcher

A dependency-free Python program for monitoring long-running microscope acquisitions. It checks whether new or updated files appear, emails a warning after each inactive interval, sends a recovery notice when acquisition resumes, and sends a disk/file-count report every 24 hours.

Each microscope runs its own copy with its own name, acquisition folder, interval, recipients, and persistent state.

## Requirements

- Ubuntu Linux
- Python 3.10 or newer
- A Gmail account with 2-Step Verification and a generated app password

No third-party Python packages or administrator rights are required when Python is installed and the current user can read the acquisition folder.

## Download and configure

Once this repository is published, run on the microscope computer:

```bash
git clone REPOSITORY_URL microscope-watcher
cd microscope-watcher
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
- `transfer.max_files_per_check`: a load-control limit on copies per interval.

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
  "max_files_per_check": 10
}
```

Files already present when MICWatcher starts are included, as are files created later. A candidate must be unchanged across checks for at least `stable_for_seconds`. The watcher preserves its path relative to the acquisition folder, copies its contents through a bounded buffer to a `.micwatcher-part` file, confirms that the source did not change and that sizes match, finalizes the destination, and only then deletes the local source. It does not attempt to copy Unix metadata, which keeps it compatible with GVFS/FUSE network mounts.

If copying or local deletion fails, the source is retained and one warning email is sent. Repeated failures remain silent. A single recovery email is sent after a later file transfers successfully. The daily report includes transfer status, pending count, total transferred count, last success, and any active error.

Use a destination unique to each microscope. The destination must not be inside the watched folder. Start with a low `max_files_per_check` and increase it only if transfers fall behind.

## Install the desktop launcher

Install it once for the current Ubuntu account; administrator rights are not required:

```bash
cd ~/MICWatcher
python3 install_desktop_launcher.py
```

Double-click **MICWatcher** on the desktop, or open it from the Applications menu. A terminal asks for the alert email, local acquisition folder, missing-file check interval, whether transfer is enabled, and—when enabled—the mounted destination and transfer-check interval. Existing Gmail credentials and microscope identity remain unchanged. Press Enter to start, leave the terminal open, and use Ctrl+C to stop.

Run the installer again after moving the repository to another path. If Ubuntu marks the desktop icon untrusted, right-click it and select **Allow Launching**.

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
- Warnings repeat every check interval while no activity is detected.
- A separate warning is sent when the acquisition folder cannot be read.
- Failed email delivery is retried on a later check.
- The daily report gives file count and free/total disk space.
- When enabled, network-transfer health and progress are included in the daily report.
- Temporarily lower `daily_report_interval_hours` to test daily reporting.

## Update an installed copy

Local configuration is preserved during updates:

```bash
cd ~/microscope-watcher
git pull
```

## Run automated tests

```bash
python3 -m unittest discover -s tests -v
```
