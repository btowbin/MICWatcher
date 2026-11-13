# Using the MICWatcher desktop launcher

This guide is for microscope users. MICWatcher should be started manually after the microscopy experiment has begun. Leave its graphical window open for the duration of the experiment.

## 1. Start the experiment

Start the microscopy experiment normally and confirm that it is saving files into the intended local acquisition folder.

## 2. Select the local acquisition folder

1. Double-click the **MICWatcher** desktop icon. If Ubuntu marks it as untrusted, right-click it and select **Allow Launching**.
2. Next to **Local acquisition folder**, click **Browse...**.
3. Navigate to the folder where the active experiment is saving files and select it.

If the folder is difficult to locate in the browser, obtain its path through Ubuntu Files:

1. Open the experiment folder in **Files**.
2. Select the **three-dot button** beside the address bar, then **Open in Terminal**.
3. Enter:

   ```bash
   pwd
   ```

4. Select the complete path printed by `pwd` and press **Ctrl+Shift+C**.
5. Paste it into the MICWatcher path field with **Ctrl+V** or the right-click menu.

Do not select an individual image file. Select the folder containing the experiment files.

## 3. Connect to the network destination

Do this before opening MICWatcher when file transfer is required.

1. Open **Files** in Ubuntu.
2. Select **Other Locations**.
3. At the bottom, find **Connect to Server**.
4. Enter:

   ```text
   smb://izbkingston.unibe.ch/towbin.data
   ```

5. Select **Connect** and enter the requested University credentials.
6. Navigate to the desired destination within the network drive.
7. Create a new destination folder for the experiment if needed, then open that folder.
8. In MICWatcher, select **Transfer stable files to a network folder** and click **Browse...** beside the destination field.

If the mounted network folder is not visible in the browser, obtain its current path:

1. In Ubuntu Files, open the destination folder.
2. Select the **three-dot button** and **Open in Terminal**.
3. Enter:

   ```bash
   pwd
   ```

4. Select the complete path and press **Ctrl+Shift+C**.
5. Paste it into the destination field in MICWatcher.

There is deliberately no default acquisition folder or transfer destination: the user must select the correct folders for each experiment.

## 4. Start MICWatcher

The GUI contains:

1. **Experiment / microscope name** — identify this particular run, for example `Embryo screen 42 / SQUID 2`. This name appears in all email subjects and SMS warnings.
2. **Alert email address** — the address that receives warnings, recoveries, and daily reports.
3. **Send one SMS for each new warning** — optional; SMS has a small per-message cost.
4. **SMS recipient number** — when SMS is enabled, enter the phone number in international format, for example `+41791234567`.
5. **Send warnings to the configured Telegram channel** — optional; the administrator must configure the bot and channel first.
6. **Local acquisition folder** — type, paste, or browse to the experiment folder.
7. **Missing-file check** — default: **60 minutes**.
8. **Transfer stable files to a network folder** — enable this checkbox when required.
9. **Transfer destination** — type, paste, or browse to the mounted folder. There is no default.
10. **Transfer check** — default: **30 minutes**.
11. **Mirror complete folder tree; overwrite destination; keep top-level non-image files** - use this when top-level CSV or other control files must remain locally. The mode recreates all subfolders, replaces older destination copies, deletes verified image copies from the top folder, and deletes all verified file copies from subfolders.

Review the settings, then click **Start monitoring**.

MICWatcher refuses to start if the local acquisition folder is blank or does not exist. When network transfer is selected, it also refuses to start if the transfer destination is blank, disconnected, or does not exist. A message identifies the field that must be corrected.

## 5. While MICWatcher is running

- Leave the MICWatcher window open.
- The status panel shows the latest activity, file count, transfers, and errors.
- Do not start a second MICWatcher instance. The launcher refuses to start if one is already running.
- Files already present in the acquisition folder are eligible for transfer after they remain unchanged long enough to be considered complete.
- A local file is deleted only after its network copy is completed and size-verified.
- The first two missing-file checks send warning emails. Further warnings remain silent until a recovery email reports that files are appearing again.
- If a file already exists at the destination, it remains in the local folder and the other files continue copying. MICWatcher sends only one destination-conflict email during that monitoring run, even if later checks find more conflicts. The current conflicting file names appear in the status panel and daily report.
- In folder-mirroring mode, existing destination files are replaced atomically. Top-level non-image files remain locally and are not recopied again during the same run unless they change.
- Another transfer failure sends one warning; a later successful transfer sends a recovery email.
- When SMS is enabled, only the first missing-file warning and first transfer-failure warning for an incident also send an SMS. The second email, recovery emails, daily reports, and safety-stop email do not send SMS.
- If SMS delivery fails, MICWatcher records the error in its log and continues monitoring, transferring, and sending email normally. It does not repeatedly retry that incident's SMS.
- Telegram uses the same warning policy as SMS. Telegram failures are logged and do not affect any other MICWatcher function.
- If more than 10,000 files are waiting for transfer, MICWatcher emails a safety warning, preserves the local files, and stops.
- The network location must remain connected while transfer is enabled.

## 6. Stop MICWatcher

Click **Stop**. If a scan or file copy is active, MICWatcher waits for it to finish safely. Closing the window while monitoring asks for confirmation before stopping. Files already copied and verified remain on the network drive; untransferred files remain local.

The next click of **Start monitoring** is always a fresh run, even when the same experiment name and folders are reused. Previous warning suppression, report timing, transfer stability state, pending-file tracking, and session counters are not carried over. The configured sender credentials remain saved.

## Troubleshooting

### The launcher says the local folder does not exist

Repeat the `pwd` procedure inside the active acquisition folder and paste the complete path.

### The launcher says the destination is not mounted or does not exist

Reconnect through **Files → Other Locations**, open the exact destination folder, obtain its current path with `pwd`, and paste that path again. Temporary Ubuntu network-drive paths may change after logout or reboot.

### The launcher says MICWatcher is already running

Find the existing MICWatcher window and click **Stop** before launching another instance.

### MICWatcher does not open

Check Tkinter from a terminal:

```bash
python3 -c 'import tkinter'
```

If that reports an import error, ask an administrator to run:

```bash
sudo apt install python3-tk
```
