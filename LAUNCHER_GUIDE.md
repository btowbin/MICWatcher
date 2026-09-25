# Using the MICWatcher desktop launcher

This guide is for microscope users. MICWatcher should be started manually after the microscopy experiment has begun. Leave its terminal window open for the duration of the experiment.

## 1. Start the experiment

Start the microscopy experiment normally and confirm that it is saving files into the intended local acquisition folder.

## 2. Find the local acquisition-folder path

1. Open **Files** in Ubuntu.
2. Navigate to the folder where the active experiment is saving its files.
3. Select the **three-dot button** beside the address bar.
4. Select **Open in Terminal**.
5. In the terminal, enter:

   ```bash
   pwd
   ```

6. Select the complete path printed by `pwd`.
7. Press **Ctrl+Shift+C** to copy it.

When the MICWatcher launcher asks for the local acquisition folder, right-click in its terminal and select **Paste**. You can also paste with **Ctrl+Shift+V**.

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
8. Select the **three-dot button** beside the address bar and select **Open in Terminal**.
9. Enter:

   ```bash
   pwd
   ```

10. Select the complete path and press **Ctrl+Shift+C**.

When the launcher asks for the transfer destination, right-click and select **Paste**. There is deliberately no default destination: the user must select the correct network folder for each experiment.

## 4. Start MICWatcher

Double-click the **MICWatcher** desktop icon. If Ubuntu marks it as untrusted, right-click it and select **Allow Launching**.

The launcher asks for:

1. **Alert email address** — the address that receives warnings and daily reports.
2. **Local acquisition folder** — paste the path obtained in step 2.
3. **Check interval for missing new files, in minutes** — default: **60 minutes**.
4. **Transfer stable files to a network folder** — enter `Y` or `N`.
5. If transfer is enabled, **Transfer destination folder** — paste the path obtained in step 3. There is no default.
6. If transfer is enabled, **File-transfer check interval, in minutes** — default: **30 minutes**.

Press Enter to accept a displayed default. Review the summary, then press Enter once more to start MICWatcher.

## 5. While MICWatcher is running

- Leave the MICWatcher terminal open.
- Do not start a second MICWatcher instance. The launcher refuses to start if one is already running.
- Files already present in the acquisition folder are eligible for transfer after they remain unchanged long enough to be considered complete.
- A local file is deleted only after its network copy is completed and size-verified.
- The first two missing-file checks send warning emails. Further warnings remain silent until a recovery email reports that files are appearing again.
- A transfer failure sends one warning; a later successful transfer sends a recovery email.
- If more than 10,000 files are waiting for transfer, MICWatcher emails a safety warning, preserves the local files, and stops.
- The network location must remain connected while transfer is enabled.

## 6. Stop MICWatcher

Return to its terminal and press:

```text
Ctrl+C
```

The program stops safely. Files already copied and verified remain on the network drive; untransferred files remain local.

## Troubleshooting

### The launcher says the local folder does not exist

Repeat the `pwd` procedure inside the active acquisition folder and paste the complete path.

### The launcher says the destination is not mounted or does not exist

Reconnect through **Files → Other Locations**, open the exact destination folder, obtain its current path with `pwd`, and paste that path again. Temporary Ubuntu network-drive paths may change after logout or reboot.

### The launcher says MICWatcher is already running

Find the existing MICWatcher terminal and stop it with Ctrl+C before launching another instance.
