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

There is deliberately no default destination: the user must select the correct network folder for each experiment.

## 4. Start MICWatcher

The GUI contains:

1. **Alert email address** — the address that receives warnings and daily reports.
2. **Local acquisition folder** — type, paste, or browse to the experiment folder.
3. **Missing-file check** — default: **60 minutes**.
4. **Transfer stable files to a network folder** — enable this checkbox when required.
5. **Transfer destination** — type, paste, or browse to the mounted folder. There is no default.
6. **Transfer check** — default: **30 minutes**.

Review the settings, then click **Start monitoring**.

## 5. While MICWatcher is running

- Leave the MICWatcher window open.
- The status panel shows the latest activity, file count, transfers, and errors.
- Do not start a second MICWatcher instance. The launcher refuses to start if one is already running.
- Files already present in the acquisition folder are eligible for transfer after they remain unchanged long enough to be considered complete.
- A local file is deleted only after its network copy is completed and size-verified.
- The first two missing-file checks send warning emails. Further warnings remain silent until a recovery email reports that files are appearing again.
- A transfer failure sends one warning; a later successful transfer sends a recovery email.
- If more than 10,000 files are waiting for transfer, MICWatcher emails a safety warning, preserves the local files, and stops.
- The network location must remain connected while transfer is enabled.

## 6. Stop MICWatcher

Click **Stop**. If a scan or file copy is active, MICWatcher waits for it to finish safely. Closing the window while monitoring asks for confirmation before stopping. Files already copied and verified remain on the network drive; untransferred files remain local.

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
