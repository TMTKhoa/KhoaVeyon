<p align="center"><img src="web/assets/logo.svg" width="150" alt="KhoaVeyon"></p>

<h1 align="center">KhoaVeyon</h1>

<p align="center">
  <b>English</b> · <a href="README.vi.md">Tiếng Việt</a><br>
  A classroom control panel for <a href="https://veyon.io">Veyon</a>: lock screens, block sites/apps/AI, run exams, track attendance and violations — from one web page on the teacher's PC.
</p>

<p align="center"><img src="docs/img/control.jpg" alt="Class control page" width="860"></p>

> KhoaVeyon does not replace Veyon. It drives Veyon (and its own small agent) from a friendlier UI. The interface is in Vietnamese.

**Current version: 5.5.0** (see [kv/paths.py](kv/paths.py), the `VERSION` variable, which is the source of truth)

## Features

| | |
|---|---|
| 🎛️ **Class control** | One-click lock, kiosk mode, block internet / apps / **AI tools**, mute, close apps, clear browser history |
| 📝 **Exam mode** | Screenshot → block AI → allow-list sites → lock settings, all in one switch |
| 📡 **Status & power** | Who is online and logged in, what is restricted; wake / shut down / restart / log off |
| 📅 **Timetable automation** | Import the timetable from Excel; machines lock and unlock by period |
| 🪑 **Seating & attendance** | Seat map per class, absent students, KhoaQuiz link |
| 🚨 **Violation monitor** | Auto screenshots on forbidden pages/apps, evidence gallery, reports |
| 📋 **Excel lists** | Edit allowed apps/sites, blocked apps/AI sites in a table; synced to students |
| 🩺 **Diagnostics** | Green/red table per PC (Veyon, Agent, clock, service version, firewall) with fix buttons |
| 💾 **Backup** | One .zip with PCs, classes, timetable, seat maps and lists; move to another teacher PC in one step |
| 🙋 **Interaction** | Students raise a hand / hand in work from their PC; messages, lock screen with a note, usage stats |
| 🔌 **Agent** | Teacher PC controls students without an admin account, C$ share or remote Task Scheduler |

## How it works

```
Teacher PC ── KhoaVeyon (web UI, Python) ──┬─ veyon-cli ───────────► Veyon Service ┐
                                           └─ Agent (HTTP, port 8767) ◄─ KhoaVeyonAutoLog service ┤ Student PCs
                                                              runs KhoaVeyonServices.bat as SYSTEM / in the student session ┘
```

## Quick start

1. **Teacher PC (Windows, Veyon Master installed):** run `Chay-KhoaVeyon.bat`. The first run downloads a portable Python if none is found.
2. Open **Thiết lập ban đầu** (Setup) → **Thiết lập máy giáo viên**, then **🔎 Find student PCs**.
3. **Each student PC, once:** copy the `payload` folder, right-click `Setup-MayHocSinh.bat` → *Run as administrator*. It installs the agent, syncs the clock and prints an `[OK]/[LOI]` checklist (also saved to `C:\cmd\KhoaVeyonSetup.log`).

Done: pick machines on **Điều khiển lớp** and press a button.

## Screenshots

| Timetable & classes | Seat map |
|:--:|:--:|
| <img src="docs/img/school.jpg" width="420"> | <img src="docs/img/seats.jpg" width="420"> |
| **Exam mode** | **Machine status** |
| <img src="docs/img/exam.jpg" width="420"> | <img src="docs/img/status.jpg" width="420"> |

## Troubleshooting

| Problem | Fix |
|---|---|
| `Invalid feature name or UID` | Set **Settings → "Buttons run via"** to *Agent*; no Veyon "Programs & websites" entries needed |
| Student shows no agent | Check the student clock/time zone (> 15 min off is rejected), teacher firewall port 8767, then rerun `Setup-MayHocSinh.bat`. Reasons appear in the **Log** |
| Machine name shows as IP | Needs the agent, reverse DNS or NetBIOS; rescan after setup |
| Timetable import fails | Header row with weekdays (`THỨ HAI`, `T2`…) + times or period numbers; the error is shown on the page |

## Requirements

Teacher PC: Windows 10/11 + [Veyon](https://veyon.io) (Master). Student PCs: Windows + Veyon Service + .NET Framework 4. Python is bundled by the launcher.

## Development

```
python -m unittest discover -s tests
```

More details (Vietnamese): [docs/HUONG-DAN-CHI-TIET.vi.md](docs/HUONG-DAN-CHI-TIET.vi.md) · [README-KhoaVeyon.md](README-KhoaVeyon.md) (changelog & source layout).

> Tested with the automated suite and a simulated UI; behaviour on real student PCs depends on your Veyon and network setup.
