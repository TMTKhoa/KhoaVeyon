# KhoaVeyonServices

**English** | [Tiếng Việt](README.vi.md)

A single Windows batch file that adds classroom-control actions to [Veyon](https://veyon.io): force close apps, block the internet (LAN stays on), allow only chosen sites, block chosen apps, allow only a few apps to open (full lockdown mode), lock down Task Manager and Settings, and mute the speakers.

Each action is a command-line switch, so every one can be run on its own from Veyon's **Run program** feature.

```
C:\cmd\KhoaVeyonServices.bat -blockall
```

> This is an independent script. It is not made by or affiliated with Veyon. It is **not** the paid *Internet Access Control* add-on from veyon.io; it is a free alternative built from Windows Firewall rules.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Switches](#switches)
- [Blocking app launch and full lockdown](#blocking-app-launch-and-full-lockdown)
- [Excel list files](#excel-list-files)
- [Adding the actions to Veyon](#adding-the-actions-to-veyon)
- [How it works](#how-it-works)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Uninstall](#uninstall)
- [Security notes](#security-notes)

---

## Features

| Feature | Switch |
|---|---|
| Force close all open apps | `-killapp` |
| Force close all apps except a list you choose | `-keepapp` |
| Block all internet, keep LAN and Veyon working | `-blockall` |
| Block the internet except sites listed in an Excel file | `-allowpage` |
| Allow all internet again | `-allowall` |
| Block apps or folders listed in an Excel file | `-blockapp` |
| Unblock those apps again | `-unblockapp` |
| Disable Task Manager and Settings/Control Panel | `-lockdown` |
| Enable them again | `-unlock` |
| Mute / unmute the speakers | `-mute`, `-unmute` |
| **Allow only the apps in a list and block everything else from opening (one command)** | `-lockall-start`, `-lockall-stop` |
| Only block apps outside the list from opening | `-lockrun-start`, `-lockrun-stop` |
| Kiosk mode: automatically close apps outside the list | `-lockapp-start`, `-lockapp-stop` |
| Record student activity, export the log | `-activitylog-start`, `-activitylog-stop`, `-exportlog` |
| Clear Chrome/Firefox browsing history | `-clearhistory` |

Other points:

- One file, no compiled code, no third-party tools.
- Excel is **not** required on the PCs. The `.xlsx` lists are read directly.
- No admin password is stored anywhere in the script.
- Designed for a classroom of standard (non-admin) student accounts.

## Requirements

- Windows 10 or 11 on the student PCs (Windows PowerShell 5.1, built in).
- Veyon installed on the teacher PC and the clients. The actions are started with Veyon's **Run program** feature.
- **Windows Defender Firewall switched on**, with its service (`mpssvc`) running. The internet blocking works by adding firewall rules, so it does nothing if the firewall is off.
- Student accounts without administrator rights.
- The script must be installed in `C:\cmd` on every client.
- Port 11100 open on every client (run `Firewall-setup.bat` on each client first).
- One-time admin approval on each PC (see [Installation](#installation)).

## Installation

**Order matters: set up the firewall on each client first.** Veyon Master can only reach a student PC once port 11100 is open on it. After that, the rest is done from the server (the teacher PC where Veyon Master runs).

Files in this project:

| File | Purpose |
|---|---|
| `Firewall-setup.bat` | Turns the firewall on and opens Veyon's port 11100. Run on every client **first**. |
| `KhoaVeyonServices.bat` | The main script with all the actions. |
| `AllowPage.xlsx`, `BlockAppList.xlsx`, `KeepAppList.xlsx` | Optional lists, with sample files you can edit (see [Excel list files](#excel-list-files)). |

### Step 1: Firewall on each client (first)

Copy `Firewall-setup.bat` to the student PC (USB drive or a shared folder) and run it. Windows asks for the PC's admin name and password (UAC). It runs only these two commands:

```
netsh advfirewall set allprofiles state on
netsh advfirewall firewall add rule name="Veyon Server" dir=in action=allow protocol=TCP localport=11100 profile=any
```

This needs admin rights, so Veyon cannot do it for you. Do it once per PC. After it, check that the PC shows up in Veyon Master.

On the **teacher PC**, also allow port `11400` for Veyon's Demo feature. These are Veyon's default ports; use your own numbers if you changed them. No port forwarding is needed.

### Step 2: Distribute the files from the server

On the teacher PC, open Veyon Master, select the student PCs and use Veyon's file distribution (the **File transfer** feature) to send these files:

- `KhoaVeyonServices.bat`
- the Excel list files you need

Veyon saves the files in the destination folder set for file transfer, which may not be `C:\cmd`. If your Veyon version has a destination folder setting, set it to `C:\cmd`. Otherwise send the files, look at one client to see where they landed, and move them into `C:\cmd`. The script must end up in `C:\cmd`.

### Step 3: Install on each client (once)

Run this on each client with admin rights:

```
C:\cmd\KhoaVeyonServices.bat -install
```

Windows asks for the admin name and password (UAC). You should see `Install done`. Veyon cannot do this step either, because its programs run as the student, who has no admin rights.

`-install` does two things:

- It creates one small Windows service per admin-level action (`KhoaVeyonService_blockall`, `_allowpage`, `_allowall`, `_blockapp`, `_unblockapp`). Standard users may **start** these services but not edit them.
- `C:\cmd` is **not** locked down: normal (student) users can read, run, and also edit everything in it, including `KhoaVeyonServices.bat` itself. See [Security notes](#security-notes) for what this means.
- It registers a logon task (`KhoaVeyonAutoLog`) that starts activity logging automatically for whichever student logs in (see [Activity log and export](#activity-log-and-export)).

### Step 4: Start applications from the server

From now on everything is done from Veyon Master on the server. Add an entry per action in Veyon (see [Adding the actions to Veyon](#adding-the-actions-to-veyon)), select the student PCs, and use **Run program** (called **Start application** in some versions) to start `C:\cmd\KhoaVeyonServices.bat` with a switch such as `-blockall`.

To update the script or the lists later, repeat Step 2 from the server.

## Switches

| Switch | Needs install? | What it does |
|---|---|---|
| `-install` | - | One-time setup (needs admin). |
| `-uninstall` | - | Removes the services, firewall rules and app blocks. |
| `-killapp` | No | Force closes all apps in the logged-in user's session. Windows shell, Veyon, cmd and PowerShell are never closed. |
| `-keepapp` | No | Same as `-killapp`, but keeps the apps listed in `KeepAppList.xlsx`. |
| `-blockall` | Yes | Blocks all internet. LAN, localhost and Veyon keep working. Blocks IPv6 internet too. |
| `-allowpage` | Yes | Blocks the internet except the sites in `AllowPage.xlsx` (and the PC's DNS server). |
| `-allowall` | Yes | Removes the internet block. |
| `-blockapp` | Yes | Blocks the files or folders in `BlockAppList.xlsx` from running and closes copies that are already open. |
| `-unblockapp` | Yes | Removes those blocks. |
| `-lockdown` | No | Disables Task Manager and Settings/Control Panel for the logged-in user. |
| `-unlock` | No | Undoes `-lockdown`. `-unlockdown` also works. |
| `-mute` | No | Mutes the default speakers. |
| `-unmute` | No | Unmutes them. |
| `-activitylog-start` | No | Starts recording the active window title, process name, date, time, user and PC name to a CSV file. **Does not record keystrokes, typed text, or passwords.** |
| `-activitylog-stop` | No | Stops recording. |
| `-exportlog` | No | Merges this PC's activity log and action log into one CSV file, ready to collect and open in Excel. |
| `-lockapp-start` | No | **Kiosk mode.** Continuously allows only the apps listed in `KeepAppList.xlsx`; anything else is closed within a few seconds of opening. |
| `-lockapp-stop` | No | Turns kiosk mode off. |
| `-lockrun-start` | No | **Blocks opening** every app not listed in `KeepAppList.xlsx` (Windows `RestrictRun` policy): apps outside the list cannot start. Restarts Explorer automatically. |
| `-lockrun-stop` | No | Removes the app-launch block. |
| `-lockall-start` | No | **Full lockdown in one command:** disables Task Manager, Settings and Registry Editor, blocks apps outside the list from opening, and closes anything that slips through (including cmd, PowerShell and Microsoft Store apps). |
| `-lockall-stop` | No | Undoes everything `-lockall-start` did. |
| `-clearhistory` | No | Closes Chrome and Firefox, then clears their browsing history. **For Firefox this also clears bookmarks** (see below). |

> **About `-activitylog-start`:** this is intentionally limited to *which window/app was active and when*, not what was typed. Recording keystrokes on children's computers is a serious privacy risk and this project does not include that capability. Tell students and parents that activity is recorded, in line with your school's policy.

Run with no switch (or an unknown one) to print the usage line.

The internet block stays in place after a reboot until you run `-allowall`.

## Full logging coverage

Every switch now writes a log line, from student-triggered actions (`-killapp`, `-keepapp`, `-lockdown`, `-mute`...) through to admin-level actions (`-blockall`, `-blockapp`...) and `-install` / `-uninstall` themselves. Nothing runs silently.

Each line records:

```
<date> <time>  PC=<computer name>  Student=<logged-in student>  RunAs=<account the code executed as>  [<switch>]  <message>
```

- **`Student`** is always the person actually sitting at the keyboard, resolved from the active console session — even when the action itself runs as SYSTEM (the admin-level switches) or as a different admin account (`-install` / `-uninstall`).
- **`RunAs`** is the account the code executed under (the student account for user-session switches, `SYSTEM` for admin-level switches run through the service, or the admin account used for `-install`/`-uninstall`).

This means a single log line always tells you *which PC*, *which student was there*, *what ran it*, and *what happened* — the full chain from student input to the admin-level action it triggered.

## Kiosk mode (`-lockapp-start` / `-lockapp-stop`)

`-keepapp` (covered above) closes everything except the listed apps **once**, at the moment you run it. `-lockapp-start` does the same thing, but **continuously**: it runs in the background and closes anything that is not in `KeepAppList.xlsx` the moment it appears, for as long as it keeps running. It shares the exclusion list (Explorer, Veyon, cmd, PowerShell...) and the same `KeepAppList.xlsx` format described above.

- Add it to Veyon: `C:\cmd\KhoaVeyonServices.bat -lockapp-start` and `C:\cmd\KhoaVeyonServices.bat -lockapp-stop`.
- Needs no admin rights and no `-install`, same as `-activitylog-start`.
- **The whitelist is read once, when you start kiosk mode**, not re-read on every check. If you edit `KeepAppList.xlsx` while kiosk mode is already running, run `-lockapp-stop` then `-lockapp-start` again to pick up the change.
- Runs independently from the activity log; starting or stopping one does not affect the other.
- A student opening something not on the list will see it flash open and close within a few seconds, rather than being blocked from opening at all. To block opening from the start, use `-lockrun-start` or `-lockall-start` (see [Blocking app launch and full lockdown](#blocking-app-launch-and-full-lockdown)), or `-blockapp` for specific apps.
- Every closed app is written to the log, so it also shows up in the daily CSV (see below).

## Blocking app launch and full lockdown

These modes let students use only the apps in `KeepAppList.xlsx` and stop everything else. Both run in the student's session: **no admin rights and no `-install` needed**.

### `-lockrun-start` / `-lockrun-stop` (block opening)

Turns on the Windows `RestrictRun` policy for the current user. When a student opens an app from the Start menu, a desktop icon, the Run box or by double-clicking a file, only listed apps open. Anything else shows *This operation has been cancelled due to restrictions in effect on this computer* and **never starts**.

- The allow list is `KeepAppList.xlsx`. Each row is a program name (`chrome` or `chrome.exe`) or a folder path. For a folder, every `.exe` inside it (including subfolders) is allowed to open.
- Explorer, ctfmon and the Veyon components are always allowed.
- Explorer only reads this policy when it starts, so the script **restarts Explorer**: the taskbar flashes once and any open File Explorer windows close.
- The policy only blocks apps opened through Explorer. Apps started from cmd, PowerShell or another app are not blocked by it, so use it together with `-lockall-start`.
- After editing `KeepAppList.xlsx`, run `-lockrun-start` again.
- If something goes wrong, the log gets a line starting with `ERROR in lockrun-start`.

### `-lockall-start` / `-lockall-stop` (full lockdown, one command)

`-lockall-start` runs these steps in order:

1. `-lockdown`: disables Task Manager and Settings/Control Panel.
2. Disables Registry Editor (`DisableRegistryTools`) so students cannot delete the rules below.
3. `-lockrun-start`: blocks apps outside the list from opening.
4. **Strict** kiosk mode: scans every 3 seconds and closes any app outside the list. Unlike the normal `-lockapp-start`, cmd, conhost, PowerShell and Settings are **not** exempt in this mode, and Microsoft Store apps (Calculator, Photos...) are closed too. Explorer and Veyon are always kept.

The last step writes a check line to the log, for example:

```
LOCKALL ON. CHECK: RestrictRun=1, kiosk worker running=True
```

`RestrictRun=1` and `running=True` mean the lock is on. `-lockall-stop` undoes all of the steps above.

> **Warning, read before use:** while a PC is locked, the student (and you, if you sit at it) cannot double-click a `.bat` file or open cmd. **Always start and stop this mode with Veyon's Run program**, which does not go through Explorer and so is not blocked. Try it on one PC before using it on the whole class. If you locked a PC and cannot use Veyon, see [Troubleshooting](#troubleshooting).

## Clear browsing history (`-clearhistory`)

```
C:\cmd\KhoaVeyonServices.bat -clearhistory
```

- **Closes Chrome and Firefox first**, because the history file is locked while a browser is running. Any open tabs or unsaved work in the browser are lost — treat this the same as `-killapp` for those two apps.
- **Chrome:** deletes only the `History` file (and its journal) in every profile folder (`Default`, `Profile 1`, `Profile 2`...). Bookmarks live in a separate `Bookmarks` file and are **not** touched.
- **Firefox:** history and bookmarks are both stored in one file, `places.sqlite`, and there is no SQLite tool built into Windows/PowerShell that can remove just the history rows. So this switch deletes `places.sqlite` entirely, which **also clears Firefox bookmarks**. If your students rely on saved Firefox bookmarks, either back them up first (Firefox menu → Bookmarks → Manage Bookmarks → Export) or avoid running this switch on Firefox profiles that have bookmarks worth keeping.
- Passwords saved in the browser, cookies and site data are **not** touched by this switch; it only removes history (and, for Firefox, bookmarks).
- Runs in the student's session, no admin rights needed.

## Activity log and export

Everything lives in `C:\cmd\log` on each client, one CSV file **per PC per day**:

```
C:\cmd\log\activity_<PCNAME>_<yyyy-MM-dd>.csv
```

Columns: `Date, Time, PCName, User, Window, Process, Event`. `Event` is one of:

- `change` — the active window/app changed.
- `autosave` — an automatic row written every 3 minutes, so the file is never more than 3 minutes out of date, even with no change.
- `action` — a block/allow/app-block/etc. event merged in from the action log, in the `Window` → left blank and the detail placed under `Event` (e.g. `action: Internet BLOCKED`).

Rows are only ever **appended**, never overwritten, so the file accumulates through the whole day. At midnight the worker switches to the next day's file by itself, with no restart needed.

### Starts automatically when the PC turns on

`-install` registers a scheduled task (`KhoaVeyonAutoLog`) that fires at every logon, for any student account, and runs `-activitylog-start`. You do not need to add anything to Veyon for this to work; it runs on its own from the moment a student logs in. `-activitylog-start` does nothing if it is already running on that PC, so a double logon or a manual run afterwards is harmless.

### `-exportlog` (optional, manual)

The 3-minute `autosave` rows already keep today's file current on their own. `-exportlog` is only useful if you want the latest block/allow/app-block events merged in **right now**, without waiting up to 3 minutes. It is safe to run repeatedly; it only adds the lines it has not merged yet.

### Collecting the files

Use Veyon's file transfer (download direction, if your version supports it) or copy `C:\cmd\log\activity_*.csv` from each client. Every file opens directly in Excel; no `.xlsx` conversion is needed.

## Excel list files

The project includes 3 sample files: `AllowPage.xlsx`, `BlockAppList.xlsx` and `KeepAppList.xlsx`. Open them in Excel, edit column A to suit your class, and copy them to `C:\cmd`.

General rules:

- The script **reads only column A of the first sheet**, one entry per row. Other columns (B, C, D...) are free for notes and are ignored. The sample files use column B for notes and column D for instructions.
- The samples have no header row. If you add a header in column A: `AllowPage.xlsx` and `BlockAppList.xlsx` ignore rows that do not look like a site or path, but `KeepAppList.xlsx` treats a header as the name of an allowed app, so do not add one.
- Only `.xlsx` files are read. Excel is not needed on the student PCs.

| File | Used by | Each row in column A |
|---|---|---|
| `AllowPage.xlsx` | `-allowpage` | A domain name or web address |
| `BlockAppList.xlsx` | `-blockapp` | The full path of a file or folder; `*` and `?` work |
| `KeepAppList.xlsx` | `-keepapp`, `-lockapp-start`, `-lockrun-start`, `-lockall-start` | A program name or a folder path |

### `AllowPage.xlsx`

Sites to allow when you use `-allowpage`. The sample:

```
wikipedia.org
vietjack.vn
olm.vn
khanacademy.org
```

`https://`, paths and `www.` are handled for you. After editing the list, run `-allowpage` again.

### `BlockAppList.xlsx`

Full paths (starting with a drive letter) of programs or folders to block with `-blockapp`. Wildcards work. The sample:

```
C:\Program Files (x86)\Steam
C:\Program Files\Epic Games
C:\Users\*\AppData\Local\Roblox
C:\Games\*.exe
C:\Users\Public\Games
C:\Program Files\Mozilla Firefox\firefox.exe
```

- `-blockapp` runs as SYSTEM, so environment variables such as `%LOCALAPPDATA%` or `%USERPROFILE%` point to SYSTEM's profile, not the student's. For folders inside a student profile, use a wildcard such as `C:\Users\*\AppData\Local\Roblox`.
- Anything inside `C:\Windows`, the Veyon folder, `C:\cmd` and drive roots is skipped on purpose, so a typo cannot break the PC.

### `KeepAppList.xlsx`

Apps that are allowed to run, shared by `-keepapp`, `-lockapp-start`, `-lockrun-start` and `-lockall-start`. The sample allows only Chrome, ONLYOFFICE and Paint:

```
chrome
C:\Program Files\Google\Chrome\Application\
C:\Program Files (x86)\Google\Chrome\Application\
%LOCALAPPDATA%\Google\Chrome\Application\
DesktopEditors
C:\Program Files\ONLYOFFICE\DesktopEditors\
mspaint
```

- A **program name** (with or without `.exe`) is the process name. Find it in Task Manager, *Details* tab.
- A **folder path**: every app running from that folder is kept, and with `-lockrun-start` every `.exe` inside the folder may be opened. That is why you should list an app's install folder too. If an app is installed somewhere else on your PCs, fix the path.
- These modes run in the student's session, so environment variables such as `%LOCALAPPDATA%` work.
- The list is read when the mode starts. After editing the file, run `-lockall-start` (or `-lockapp-start`, `-lockrun-start`) again.

### Changing the list folder

By default the lists are read from `C:\cmd\`. To use one shared copy for every PC, change `LISTDIR` near the top of the script to a network path (keep the trailing backslash). The share must be readable by the computer accounts (for the admin-level actions) and by the student accounts (for the user-level actions).

Since `C:\cmd` is not locked down, you can update the lists as any user who can reach the folder, but so can students, so treat the lists as editable by them too.

## Adding the actions to Veyon

1. Open **Veyon Configurator** and go to **Programs & websites** (the name varies by version; in older versions it is under **Master**).
2. Add one entry per action. The command is the script path plus the switch:

| Name | Command |
|---|---|
| Close all apps | `C:\cmd\KhoaVeyonServices.bat -killapp` |
| Close all except list | `C:\cmd\KhoaVeyonServices.bat -keepapp` |
| Block internet | `C:\cmd\KhoaVeyonServices.bat -blockall` |
| Allow listed sites only | `C:\cmd\KhoaVeyonServices.bat -allowpage` |
| Allow internet | `C:\cmd\KhoaVeyonServices.bat -allowall` |
| Block apps | `C:\cmd\KhoaVeyonServices.bat -blockapp` |
| Unblock apps | `C:\cmd\KhoaVeyonServices.bat -unblockapp` |
| Lockdown | `C:\cmd\KhoaVeyonServices.bat -lockdown` |
| Unlock | `C:\cmd\KhoaVeyonServices.bat -unlock` |
| Mute | `C:\cmd\KhoaVeyonServices.bat -mute` |
| Unmute | `C:\cmd\KhoaVeyonServices.bat -unmute` |
| Full lockdown (listed apps only) | `C:\cmd\KhoaVeyonServices.bat -lockall-start` |
| Undo full lockdown | `C:\cmd\KhoaVeyonServices.bat -lockall-stop` |
| Block only app opening | `C:\cmd\KhoaVeyonServices.bat -lockrun-start` |
| Unblock app opening | `C:\cmd\KhoaVeyonServices.bat -lockrun-stop` |
| Kiosk mode on | `C:\cmd\KhoaVeyonServices.bat -lockapp-start` |
| Kiosk mode off | `C:\cmd\KhoaVeyonServices.bat -lockapp-stop` |

3. Click **Apply**.
4. In **Veyon Master**, select the student PCs, click **Run program** (called **Start application** in some versions), and choose an entry.

Use backslashes (`\`) in the path, not forward slashes. If Veyon cannot run the `.bat` file directly, start the command with `cmd.exe /c`, for example `cmd.exe /c C:\cmd\KhoaVeyonServices.bat -lockall-start`.

## How it works

Veyon's **Run program** starts a command as the logged-in student, who has no admin rights. Changing the firewall needs admin rights, so the script uses two paths:

- **Admin-level actions** (`-blockall`, `-allowpage`, `-allowall`, `-blockapp`, `-unblockapp`): when started by a student, the script asks the matching SYSTEM service to run. The service starts the same script, which now has admin rights and does the work with PowerShell.
- **User-level actions** (`-killapp`, `-keepapp`, `-lockdown`, `-unlock`, `-mute`, `-unmute`, `-lockapp-*`, `-lockrun-*`, `-lockall-*`): these run directly in the student's session and need no admin rights or service.

Details:

- **Internet blocking** adds two outbound firewall rules, `KhoaVeyonBlock` and `KhoaVeyonBlock6`. They block every address except private LAN ranges (`10.x`, `172.16-31.x`, `192.168.x`), localhost, link-local, multicast and broadcast.
- **`-allowpage`** looks up the IP addresses of each listed site and removes them from the blocked ranges. The PC's DNS servers are allowed as well.
- **`-blockapp`** adds a *deny Execute* permission for the Users group on each listed file or folder, and records the paths in `blocked.txt` so `-unblockapp` can undo it.
- **`-lockdown`** sets the `DisableTaskMgr` and `NoControlPanel` policies for the current user.
- **`-lockrun-start`** sets the `RestrictRun` policy (plus a `RestrictRun` list of the allowed `.exe` names) under `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer` for the current user, then restarts Explorer. `-lockrun-stop` removes those values.
- **`-lockall-start`** runs `-lockapp-stop`, `-lockdown`, sets `DisableRegistryTools`, runs `-lockrun-start`, then runs `-lockapp-start` with a strict flag (the environment variable `KV_STRICT=1`).
- **`-mute`** uses the Windows Core Audio API to mute the default output device.

The PowerShell code lives at the end of the `.bat` file, after the `#PS1START` marker. Do not put that text anywhere else in the file.

## Limitations

- **`-allowpage` works by IP address, not by domain.** Large sites that use many domains or CDNs (for example YouTube or Google) may load only partly, and IP addresses change over time. Run `-allowpage` again to refresh them. For reliable site filtering, use a DNS filter at your router.
- **A proxy server on your LAN defeats the block.** If the PCs reach the internet through a proxy with a LAN address, that traffic looks like LAN traffic and is allowed. Check with `netsh winhttp show proxy`.
- **Third-party firewalls and antivirus products** that manage the Windows firewall can override the rules.
- **Existing connections** may survive for a moment. Closing and reopening the browser makes the block visible immediately.
- **`-blockapp`** also affects administrators until you run `-unblockapp`. It does not block Microsoft Store (UWP) apps. A student can still copy a blocked program to another location.
- **`-lockdown` and `-mute`** apply only to the logged-in account. Students can still unmute with the keyboard volume keys.
- **Windows may log "service did not respond" (error 1053)** for the services. This is expected: the services are not real service programs, but the commands still run.
- Domain names and paths are processed from the first sheet only.
- **`-lockrun-start` only blocks apps opened through Explorer** (Start menu, icons, the Run box, double-click). Apps started from cmd, PowerShell or another app are not blocked by this policy, so it needs the kiosk mode alongside it (`-lockall-start` includes both).
- **Kiosk mode has a delay of up to about 3 seconds.** An app outside the list may flash on screen before it is closed. Background processes without a window are not closed (except Microsoft Store apps in strict mode).
- **The rules of `-lockrun-*` and `-lockall-*` live in the student account's own registry.** They are classroom management, not a hard security barrier. A student who knows Windows well can still find a way around them.
- Turning `-lockrun-*` or `-lockall-*` off restarts Explorer once more.

## Troubleshooting

**Nothing happens.**
Check the log. Admin-level actions write to `C:\cmd\KhoaVeyonService.log`; user-level actions write to `%TEMP%\KhoaVeyonService.log` of the logged-in student. The log records each action, missing list files and skipped paths.

**`Service not installed`.**
Run `-install` as the PC's administrator.

**The internet is still reachable after `-blockall`.**
Check, in this order:
1. The firewall is on: `netsh advfirewall show allprofiles state`
2. The rule exists: `netsh advfirewall firewall show rule name="KhoaVeyonBlock"`
3. There is no proxy: `netsh winhttp show proxy`
4. `ping 8.8.8.8` fails after the block, while `ping <teacher PC IP>` still works.

**A PC disappears from Veyon Master after the firewall was turned on.**
Add the incoming rule for port 11100 (see [Step 1](#step-1-firewall-on-each-client-first)).

**`-mute` does nothing.**
Make sure the PC has an active output device. Check the log for the error text.

**`-lockall-start` has no effect.**
Check, in this order:
1. The command is written correctly, with backslashes and the **s** in the file name: `C:\cmd\KhoaVeyonServices.bat -lockall-start`.
2. Open `%TEMP%\KhoaVeyonService.log` on the student PC. A line `LOCKALL ON. CHECK: RestrictRun=1, kiosk worker running=True` means the command ran; an `ERROR` line gives the exact problem.
3. `C:\cmd\KeepAppList.xlsx` exists and the app names are in column A. If not, the log says `WARNING: KeepAppList.xlsx is empty or not found`.
4. An allowed app that still will not open usually has a process name or install folder different from the Excel file. The log lists `Closed (not in KeepAppList)` lines so you can see what to add.

**A PC is locked and cmd or `.bat` files will not open.**
This is expected while `-lockrun-start` or `-lockall-start` is on. From Veyon Master, use **Run program** to run `C:\cmd\KhoaVeyonServices.bat -lockall-stop`; it does not go through Explorer, so it is not blocked. Wait a few seconds for Explorer to restart.

If you cannot use Veyon, sign the student out, sign in with an admin account (the locks are in the student's account, so the admin is not affected), and run this in an administrator cmd (replace `<name>` with the student account name):

```
reg load HKU\kid C:\Users\<name>\NTUSER.DAT
reg delete "HKU\kid\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\RestrictRun" /f
reg delete "HKU\kid\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v RestrictRun /f
reg delete "HKU\kid\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoControlPanel /f
reg delete "HKU\kid\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v DisableTaskMgr /f
reg delete "HKU\kid\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v DisableRegistryTools /f
reg unload HKU\kid
```

The kiosk process does not survive the student signing out, so nothing else needs stopping.

## Uninstall

Run as administrator on each PC:

```
C:\cmd\KhoaVeyonServices.bat -uninstall
```

This removes the internet block, the app blocks and the services. You can then delete `C:\cmd`. `-lockdown`, `-mute`, `-lockrun-*` and `-lockall-*` are per-user settings, so `-uninstall` (run as an admin) cannot remove the settings stored in a student account. If they are still active, run `-lockall-stop` and `-unmute` through Veyon (as the student) before uninstalling.

## Security notes

- The script contains **no passwords**. Admin rights are provided once, at install, through the Windows UAC prompt.
- **`C:\cmd` is writable by normal users, and the admin-level services run `KhoaVeyonServices.bat` as SYSTEM.** This means anyone who can edit a file in `C:\cmd` — including a student — can make the SYSTEM services run arbitrary code the next time they are started, which is a genuine privilege-escalation path. This project used to lock the folder read-only for this exact reason; the lock was removed on request. If you need that protection back, re-add it on each PC:
  ```
  icacls "C:\cmd" /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" "Users:(OI)(CI)RX" /T
  ```
  (run as administrator; this also removes any write access students currently have, including to `C:\cmd\log`, so re-add a writable exception for that folder if you still want the activity log: `icacls "C:\cmd\log" /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" "Users:(OI)(CI)M"`).
- `-lockall-start` disables Registry Editor and uses policies stored in the student account to make the rules hard to remove, but that is only classroom management. Because `C:\cmd` is writable by students, a student can also edit `KeepAppList.xlsx` or the script itself (see the note above).
- Tell your students and their parents that the classroom tools can restrict the PC, in line with your school's policy.

## License

Add a license of your choice (for example MIT) before publishing.