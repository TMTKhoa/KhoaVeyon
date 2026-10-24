@echo off
setlocal
REM ============================================================
REM  KhoaVeyonServices.bat  -  for Veyon clients (keep in C:\cmd)
REM
REM  -install      one-time setup per PC (needs admin password once)
REM                (also installs service KhoaVeyonAutoLog: activity log at every logon AND the
REM                 Agent channel: the teacher PC controls this PC through that service, no
REM                 Windows admin account / C$ share / remote Task Scheduler needed. Settings are in
REM                 %ProgramFiles%\KhoaVeyon\agent.cfg, written by Setup-MayHocSinh.bat)
REM  -uninstall    remove services, rules and app blocks
REM  -killapp      force close all open apps
REM  -blockall     block all internet (LAN stays on)
REM  -allowpage    block internet EXCEPT sites listed in AllowPage.xlsx
REM  -allowall     allow all internet again
REM  -webonly      allow ONLY the sites in AllowPage.xlsx via browser policy (covers subdomains + their API requests)
REM  -weboff       undo -webonly (restore the browser policy that was there before)
REM  -blockapp     block apps/folders listed in BlockAppList.xlsx
REM  -unblockapp   unblock those apps again
REM  -keepapp      close all apps EXCEPT those listed in KeepAppList.xlsx
REM  -lockdown     disable Task Manager and Settings for the logged-in user
REM  -unlock       enable Task Manager and Settings again
REM  -mute         mute the speakers
REM  -unmute       unmute the speakers
REM  -activitylog-start  start recording which app/window is active (no keystrokes, no passwords)
REM  -activitylog-stop   stop recording
REM  -exportlog          merge this PC's logs into one CSV file (opens in Excel)
REM  -lockapp-start      kiosk mode: continuously allow ONLY the apps listed in
REM                      KeepAppList.xlsx, closing anything else the moment it opens
REM  -lockapp-stop       turn kiosk mode off
REM  -lockrun-start      BLOCK OPENING of every app NOT listed in KeepAppList.xlsx
REM                      (Windows RestrictRun policy, per user, no admin needed)
REM  -lockrun-stop       turn that block off again
REM  -lockall-start      ONE COMMAND: block ALL apps except those in KeepAppList.xlsx
REM                      (blocks opening + closes anything else + locks Task Manager,
REM                      Settings, Registry Editor, cmd and PowerShell)
REM  -lockall-stop       undo all of the above
REM  -clearhistory       close Chrome/Firefox and clear their browsing history
REM                      (Firefox: this also clears bookmarks, see README)
REM  -blockai            BLOCK ALL AI TOOLS: AI websites (browser policy + hosts file),
REM                      AI built into the browser (Gemini in Chrome, Copilot in Edge,
REM                      Firefox AI, Brave Leo) and AI desktop apps. Needs the service
REM  -allowai            undo -blockai (puts back the settings that were there before)
REM ============================================================

REM ===== SETTINGS =====
REM Folder that holds AllowPage.xlsx and BlockAppList.xlsx (keep the last backslash)
set "LISTDIR=C:\cmd\"
REM -blockai options (1 = yes, 0 = no)
REM AI_USE_HOSTS        also block AI sites in the hosts file (covers browsers without policy support)
REM AI_CLOSE_BROWSERS   close open browsers the first time -blockai runs, so open AI tabs stop working
REM AI_BLOCK_EXTENSIONS stop installing and running ALL Chrome/Edge extensions (AI helper extensions)
set "AI_USE_HOSTS=1"
set "AI_CLOSE_BROWSERS=1"
set "AI_BLOCK_EXTENSIONS=0"
REM ====================

set "SELF=%~f0"
set "ACT=%~1"
set "MODE="

if /i "%ACT%"=="-killapp"    set "MODE=killapp"
if /i "%ACT%"=="-install"    goto INSTALL
if /i "%ACT%"=="-uninstall"  goto UNINSTALL
if /i "%ACT%"=="-blockall"   set "MODE=blockall"
if /i "%ACT%"=="-allowpage"  set "MODE=allowpage"
if /i "%ACT%"=="-allowall"   set "MODE=allowall"
if /i "%ACT%"=="-webonly"    set "MODE=webonly"
if /i "%ACT%"=="-weboff"     set "MODE=weboff"
if /i "%ACT%"=="-blockapp"   set "MODE=blockapp"
if /i "%ACT%"=="-unblockapp" set "MODE=unblockapp"
if /i "%ACT%"=="-keepapp"    set "MODE=keepapp"
if /i "%ACT%"=="-lockdown"   set "MODE=lockdown"
if /i "%ACT%"=="-unlock"     set "MODE=unlock"
if /i "%ACT%"=="-unlockdown" set "MODE=unlock"
if /i "%ACT%"=="-mute"       set "MODE=mute"
if /i "%ACT%"=="-unmute"     set "MODE=unmute"
if /i "%ACT%"=="-activitylog-start" set "MODE=activitylog-start"
if /i "%ACT%"=="-activitylog-stop"  set "MODE=activitylog-stop"
if /i "%ACT%"=="-exportlog"         set "MODE=exportlog"
if /i "%ACT%"=="-lockapp-start"     set "MODE=lockapp-start"
if /i "%ACT%"=="-lockapp-stop"      set "MODE=lockapp-stop"
if /i "%ACT%"=="-clearhistory"      set "MODE=clearhistory"
if /i "%ACT%"=="-lockrun-start"      set "MODE=lockrun-start"
if /i "%ACT%"=="-lockrun-stop"       set "MODE=lockrun-stop"
if /i "%ACT%"=="-lockall-start"      set "MODE=lockall-start"
if /i "%ACT%"=="-lockall-stop"       set "MODE=lockall-stop"
if /i "%ACT%"=="-blockai"            set "MODE=blockai"
if /i "%ACT%"=="-allowai"            set "MODE=allowai"
if not defined MODE goto HELP

REM These run in the kid's own session, so they need no admin rights and no service
for %%U in (killapp keepapp lockdown unlock mute unmute activitylog-start activitylog-stop exportlog lockapp-start lockapp-stop clearhistory lockrun-start lockrun-stop lockall-start lockall-stop) do if /i "%MODE%"=="%%U" goto RUNPS

REM Already admin / SYSTEM (for example when started by the service)? Do the work now.
fltmc >nul 2>&1
if errorlevel 1 goto VIAUSER

:RUNPS
set "KV_MODE=%MODE%"
set "KV_DIR=%~dp0"
set "KV_LIST=%LISTDIR%"
set "KV_SELF=%SELF%"
set "KV_AI_HOSTS=%AI_USE_HOSTS%"
set "KV_AI_CLOSE=%AI_CLOSE_BROWSERS%"
set "KV_AI_EXT=%AI_BLOCK_EXTENSIONS%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:KV_SELF); iex $t.Substring($t.IndexOf('#PS1'+'START'))"
exit /b 0

:VIAUSER
REM Normal (kid) account: ask the SYSTEM service to do the work
sc start KhoaVeyonService_%MODE% >nul 2>&1
if %errorlevel%==1060 echo Service not installed. Run KhoaVeyonServices.bat -install as admin.
exit /b 0

:INSTALL
fltmc >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process '%SELF%' -ArgumentList '-install' -Verb RunAs"
  exit /b
)
for %%M in (blockall allowpage allowall webonly weboff blockapp unblockapp blockai allowai) do (
  sc stop KhoaVeyonService_%%M >nul 2>&1
  sc delete KhoaVeyonService_%%M >nul 2>&1
  sc create KhoaVeyonService_%%M binPath= "cmd.exe /c %SELF% -%%M" start= demand >nul
  sc sdset KhoaVeyonService_%%M "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;LCRPRC;;;IU)" >nul
)
REM NOTE: C:\cmd is left editable by normal users (no icacls lock).
REM The SYSTEM services below execute these .bat files as SYSTEM, so anyone who can
REM edit this folder can run arbitrary code as SYSTEM. See the README security note.
if not exist "C:\cmd\log" mkdir "C:\cmd\log" >nul 2>&1

REM --- Evidence folder: students may ADD screenshots but may NOT delete/rename them (so a student
REM     cannot wipe the evidence in the few seconds before the teacher PC collects it).
REM     We deny the "delete / delete-child / change-permissions / take-ownership" rights to the
REM     INTERACTIVE group (anyone logged on AT the PC = the student). The teacher reaches the files
REM     over the network as an admin (NETWORK logon, not INTERACTIVE), so the teacher can still
REM     copy AND delete them. SIDs used so it works on any Windows language:
REM       S-1-5-18 SYSTEM, S-1-5-32-544 Administrators, S-1-5-32-545 Users, S-1-5-4 INTERACTIVE.
set "KVEVID=C:\Users\Public\KhoaVeyonEvidence"
if not exist "%KVEVID%" mkdir "%KVEVID%" >nul 2>&1
icacls "%KVEVID%" /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "*S-1-5-32-545:(OI)(CI)(RX,WD,AD,WA,WEA,REA,RA)" >nul 2>&1
icacls "%KVEVID%" /deny "*S-1-5-4:(OI)(CI)(DE,DC,WDAC,WO)" >nul 2>&1

REM Auto-start activity logging whenever any student logs on: Windows service KhoaVeyonAutoLog
REM (replaces the old scheduled task of the same name, which is removed). The service code and
REM its installer are in the KVSVC block (between the KVSVC markers) near the end of this file.
set "KV_SELF=%SELF%"
set "AUTOLOG_OK=1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:KV_SELF); $i=$t.IndexOf('#KVSVC'+'START'); $j=$t.IndexOf('#KVSVC'+'END'); iex $t.Substring($i, $j-$i)"
if errorlevel 1 set "AUTOLOG_OK=0"

if "%AUTOLOG_OK%"=="1" (
  call :LOGEVENT install "Setup completed"
) else (
  call :LOGEVENT install "Setup completed, but service KhoaVeyonAutoLog FAILED"
)
echo.
echo Install done. Services KhoaVeyonService_* created.
if "%AUTOLOG_OK%"=="1" (
  echo Activity logging will start automatically at every logon ^(service KhoaVeyonAutoLog^).
) else (
  echo WARNING: service KhoaVeyonAutoLog could not be installed, see the message above.
)
echo Log folder: C:\cmd\log
pause
if "%AUTOLOG_OK%"=="0" exit /b 2
exit /b 0

:UNINSTALL
fltmc >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process '%SELF%' -ArgumentList '-uninstall' -Verb RunAs"
  exit /b
)
call "%SELF%" -allowall
call "%SELF%" -weboff
call "%SELF%" -unblockapp
call "%SELF%" -activitylog-stop
call "%SELF%" -lockapp-stop
call "%SELF%" -lockall-stop
call "%SELF%" -allowai
for %%M in (blockall allowpage allowall webonly weboff blockapp unblockapp blockai allowai) do (
  sc stop KhoaVeyonService_%%M >nul 2>&1
  sc delete KhoaVeyonService_%%M >nul 2>&1
)
sc stop KhoaVeyonAutoLog >nul 2>&1
powershell -NoProfile -Command "try { (Get-Service KhoaVeyonAutoLog -ErrorAction Stop).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(20)) } catch {}"
sc delete KhoaVeyonAutoLog >nul 2>&1
if exist "%ProgramFiles%\KhoaVeyon\KhoaVeyonAutoLog.exe" del /f /q "%ProgramFiles%\KhoaVeyon\KhoaVeyonAutoLog.exe" >nul 2>&1
if exist "%ProgramFiles%\KhoaVeyon\agent.cfg" del /f /q "%ProgramFiles%\KhoaVeyon\agent.cfg" >nul 2>&1
rd "%ProgramFiles%\KhoaVeyon" >nul 2>&1
REM Old versions used a scheduled task with the same name: remove it too if it is still there
schtasks /delete /tn "KhoaVeyonAutoLog" /f >nul 2>&1
REM Give the evidence folder its normal (inherited) permissions back
icacls "C:\Users\Public\KhoaVeyonEvidence" /reset /T /C >nul 2>&1
call :LOGEVENT uninstall "Removed services (incl. KhoaVeyonAutoLog), rules and app blocks"
echo.
echo Uninstall done.
pause
exit /b 0

:LOGEVENT
REM %1 = mode name, %2 = message. Writes one line in the same format Log() uses in PowerShell,
REM so -exportlog and manual reading stay consistent for install/uninstall events too.
powershell -NoProfile -Command ^
 "$student = $env:USERNAME; try { $u = (Get-CimInstance Win32_ComputerSystem -ErrorAction Stop).UserName; if ($u) { $student = $u } } catch {};" ^
 "Add-Content -Path 'C:\cmd\KhoaVeyonService.log' -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  PC=' + $env:COMPUTERNAME + '  Student=' + $student + '  RunAs=' + $env:USERNAME + '  [%~1]  %~2')"
exit /b 0

:HELP
echo Usage: KhoaVeyonServices.bat [-install ^| -uninstall ^| -killapp ^| -blockall ^| -allowpage ^| -allowall ^| -webonly ^| -weboff ^| -blockapp ^| -unblockapp ^| -keepapp ^| -lockdown ^| -unlock ^| -mute ^| -unmute ^| -activitylog-start ^| -activitylog-stop ^| -exportlog ^| -lockapp-start ^| -lockapp-stop ^| -lockrun-start ^| -lockrun-stop ^| -lockall-start ^| -lockall-stop ^| -blockai ^| -allowai ^| -clearhistory]
exit /b 0

#KVSVCSTART
# ---------------------------------------------------------------------------------------------
# Installs the Windows service KhoaVeyonAutoLog (replaces the old "KhoaVeyonAutoLog" scheduled
# task). Called only from :INSTALL, already elevated. The batch code never reaches this block
# (every label above ends with exit /b), and the embedded PowerShell part below never includes it.
#
# Why a real service and not "sc create ... cmd.exe" like the others: a service runs in
# session 0 and cannot see the student's windows, but -activitylog-start must run INSIDE the
# student's session. So the service (SYSTEM) listens for logon events and starts
#     cmd.exe /c "<this .bat>" -activitylog-start
# in that session, with the student's own (limited) token, hidden. Same effect as the old task
# (group Users, at logon, RunLevel Limited), plus: it also covers a student who is already
# logged on when the service starts (right after -install, or a slow boot).
# Exit code: 0 = service installed and running, 1 = failed (reason printed).
# ---------------------------------------------------------------------------------------------
$ErrorActionPreference = 'Continue'
$svcName = 'KhoaVeyonAutoLog'
$bat     = $env:KV_SELF
$svcDir  = Join-Path $env:ProgramFiles 'KhoaVeyon'   # admin-only folder: students cannot swap the exe
$svcExe  = Join-Path $svcDir 'KhoaVeyonAutoLog.exe'
$binPath = '"{0}" "{1}"' -f $svcExe, $bat

$csSource = @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.ServiceProcess;
using System.Text;
using System.Threading;

public class KvAutoLogService : ServiceBase
{
    static string Script = @"C:\cmd\KhoaVeyonServices.bat";
    static readonly object Gate = new object();
    static readonly Dictionary<int, DateTime> LastLaunch = new Dictionary<int, DateTime>();
    // "Guard" processes to keep alive in each student session (e.g. the violation monitor). The teacher
    // PC writes one command line per guard into vcfg\kvguard.txt; this service relaunches a guard within
    // ~30s whenever it is not running (for example after a student kills it in Task Manager). Removing the
    // line (teacher turns the feature off) stops the relaunching.
    static readonly Dictionary<string, int> GuardPids = new Dictionary<string, int>();
    static System.Threading.Timer GuardTimer;

    static string GuardFile
    {
        get
        {
            string dir = Path.GetDirectoryName(Script);
            if (string.IsNullOrEmpty(dir)) dir = @"C:\cmd";
            return Path.Combine(dir, "vcfg", "kvguard.txt");
        }
    }

    public KvAutoLogService()
    {
        ServiceName = "KhoaVeyonAutoLog";
        CanStop = true;
        CanHandleSessionChangeEvent = true;
        AutoLog = false;
    }

    protected override void OnStart(string[] args)
    {
        // Students already logged on (service just installed, or it started after the logon)
        ThreadPool.QueueUserWorkItem(delegate { LaunchForActiveSessions(); });
        // Keep the guard processes (violation monitor) alive, checking every 30 seconds.
        GuardTimer = new System.Threading.Timer(delegate { try { EnsureGuards(); } catch { } }, null, 15000, 30000);
        // Agent channel: the teacher PC controls this PC through this service (no Windows admin account / C$ needed).
        try { KvAgent.Start(); } catch (Exception e) { Log("agent: cannot start (" + e.Message + ")"); }
    }

    protected override void OnStop()
    {
        KvAgent.Stop();
        if (GuardTimer != null) { GuardTimer.Dispose(); GuardTimer = null; }
    }

    protected override void OnSessionChange(SessionChangeDescription d)
    {
        if (d.Reason == SessionChangeReason.SessionLogon)
        {
            int id = d.SessionId;
            ThreadPool.QueueUserWorkItem(delegate { LaunchWithRetry(id, 5); try { EnsureGuards(); } catch { } });
        }
    }

    // ---------- Win32 ----------
    [StructLayout(LayoutKind.Sequential)]
    struct WTS_SESSION_INFO { public int SessionId; public IntPtr pWinStationName; public int State; }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct STARTUPINFO
    {
        public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize;
        public int dwXCountChars; public int dwYCountChars; public int dwFillAttribute;
        public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }

    [DllImport("wtsapi32.dll", SetLastError = true)]
    static extern bool WTSQueryUserToken(int sessionId, out IntPtr token);
    [DllImport("wtsapi32.dll", SetLastError = true)]
    static extern bool WTSEnumerateSessions(IntPtr server, int reserved, int version, out IntPtr info, out int count);
    [DllImport("wtsapi32.dll")]
    static extern void WTSFreeMemory(IntPtr p);
    [DllImport("userenv.dll", SetLastError = true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr token, bool inherit);
    [DllImport("userenv.dll", SetLastError = true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr token, string app, StringBuilder cmd, IntPtr pa, IntPtr ta,
        bool inherit, int flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr h);

    const int WTSActive = 0;
    const int STARTF_USESHOWWINDOW = 0x1;
    const short SW_HIDE = 0;
    const short SW_SHOWNORMAL = 1;
    const int CREATE_UNICODE_ENVIRONMENT = 0x400;
    const int CREATE_NO_WINDOW = 0x08000000;

    static void LaunchForActiveSessions()
    {
        IntPtr info; int count;
        if (!WTSEnumerateSessions(IntPtr.Zero, 0, 1, out info, out count)) return;
        try
        {
            int size = Marshal.SizeOf(typeof(WTS_SESSION_INFO));
            for (int i = 0; i < count; i++)
            {
                WTS_SESSION_INFO s = (WTS_SESSION_INFO)Marshal.PtrToStructure(new IntPtr(info.ToInt64() + i * size), typeof(WTS_SESSION_INFO));
                if (s.SessionId != 0 && s.State == WTSActive) LaunchWithRetry(s.SessionId, 0);
            }
        }
        finally { WTSFreeMemory(info); }
    }

    // The user token can be missing for a few seconds right after logon: wait, then retry for ~1 minute.
    static void LaunchWithRetry(int sessionId, int firstDelaySec)
    {
        if (firstDelaySec > 0) Thread.Sleep(firstDelaySec * 1000);
        lock (Gate)
        {
            DateTime last;
            if (LastLaunch.TryGetValue(sessionId, out last) && (DateTime.Now - last).TotalSeconds < 60) return;
            LastLaunch[sessionId] = DateTime.Now;
        }
        string cmdExe = Path.Combine(Environment.SystemDirectory, "cmd.exe");
        string activity = "\"" + cmdExe + "\" /c \"\"" + Script + "\" -activitylog-start\"";
        for (int attempt = 1; attempt <= 12; attempt++)
        {
            string err; int pid = Launch(sessionId, cmdExe, activity, out err);
            if (pid > 0) { Log("session " + sessionId + ": started -activitylog-start"); RunLogonList(sessionId); return; }
            if (attempt == 12) Log("session " + sessionId + ": could not start activity log (" + err + ")");
            Thread.Sleep(5000);
        }
    }

    // Student helper (hand raise / hand in work / teacher messages): KhoaVeyonStudent.ps1 next to this script, one copy per
    // student session. It touches tray-<session>.alive every 10s; relaunch it within ~30s when that heartbeat is stale.
    static readonly Dictionary<int, DateTime> TrayLaunch = new Dictionary<int, DateTime>();
    static void EnsureTray()
    {
        string dir = Path.GetDirectoryName(Script);
        if (string.IsNullOrEmpty(dir)) dir = @"C:\cmd";
        string ps1 = Path.Combine(dir, "KhoaVeyonStudent.ps1");
        string root = KvAgent.DataRoot;
        if (!File.Exists(ps1) || File.Exists(Path.Combine(root, "tray.off"))) return;
        foreach (int sid in ActiveSessions())
        {
            try
            {
                string hb = Path.Combine(root, "tray-" + sid + ".alive");
                if (File.Exists(hb) && (DateTime.Now - File.GetLastWriteTime(hb)).TotalSeconds < 40) continue;
                lock (Gate)
                {
                    DateTime t;
                    if (TrayLaunch.TryGetValue(sid, out t) && (DateTime.Now - t).TotalSeconds < 45) continue;
                    TrayLaunch[sid] = DateTime.Now;
                }
                string err; IntPtr h;
                int pid = LaunchH(sid, null, "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"" + ps1 + "\"", out err, out h, true);
                if (h != IntPtr.Zero) CloseHandle(h);
                if (pid > 0) Log("session " + sid + ": started student helper");
                else Log("session " + sid + ": student helper not started (" + err + ")");
            }
            catch { }
        }
    }

    // Keep each guard command (one per line in kvguard.txt) running in every active student session.
    static void EnsureGuards()
    {
        try { EnsureTray(); } catch { }
        string[] lines;
        try
        {
            if (!File.Exists(GuardFile)) { return; }
            lines = File.ReadAllLines(GuardFile);
        }
        catch { return; }

        var cmds = new System.Collections.Generic.List<string>();
        foreach (string raw in lines) { string l = (raw ?? "").Trim(); if (l.Length > 0) cmds.Add(l); }

        var sessions = ActiveSessions();
        lock (Gate)
        {
            // Drop tracking for commands/sessions that are no longer wanted
            var stale = new System.Collections.Generic.List<string>();
            foreach (var key in GuardPids.Keys)
            {
                int bar = key.IndexOf('|');
                int sid = int.Parse(key.Substring(0, bar));
                string cmd = key.Substring(bar + 1);
                if (!cmds.Contains(cmd) || !sessions.Contains(sid)) stale.Add(key);
            }
            foreach (var k in stale) GuardPids.Remove(k);
        }

        foreach (int sid in sessions)
        {
            foreach (string cmd in cmds)
            {
                string key = sid + "|" + cmd;
                int pid;
                lock (Gate) { if (!GuardPids.TryGetValue(key, out pid)) pid = -1; }
                // Already running? The watch script refreshes alive.txt every 10s, so a fresh heartbeat means it is
                // up (even the copy the teacher PC started directly). Otherwise fall back to the PID we launched.
                if (GuardAlive(cmd, pid)) continue;
                string err; int newPid = Launch(sid, null, cmd, out err);
                if (newPid > 0)
                {
                    lock (Gate) { GuardPids[key] = newPid; }
                    Log("session " + sid + ": (re)started guard");
                }
            }
        }
    }

    static bool ProcessAlive(int pid)
    {
        if (pid <= 0) return false;
        try { Process.GetProcessById(pid); return true; }
        catch { return false; }
    }

    // Is this guard already running? Prefer the watch heartbeat file (-Out ...\alive.txt, refreshed every 10s);
    // if the command has no -Out, fall back to the PID we last launched.
    static bool GuardAlive(string cmd, int trackedPid)
    {
        string outDir = ExtractArg(cmd, "-Out");
        if (!string.IsNullOrEmpty(outDir))
        {
            try
            {
                string alive = Path.Combine(outDir, "alive.txt");
                if (File.Exists(alive) && (DateTime.Now - File.GetLastWriteTime(alive)).TotalSeconds < 40) return true;
            }
            catch { }
            return false;   // has a heartbeat location but it is stale -> not running
        }
        return ProcessAlive(trackedPid);
    }

    // Read the value after a flag (e.g. -Out) from a command line, handling a "quoted value".
    static string ExtractArg(string cmd, string flag)
    {
        if (string.IsNullOrEmpty(cmd)) return null;
        int i = cmd.IndexOf(flag + " ", StringComparison.OrdinalIgnoreCase);
        if (i < 0) return null;
        int p = i + flag.Length;
        while (p < cmd.Length && cmd[p] == ' ') p++;
        if (p >= cmd.Length) return null;
        if (cmd[p] == '"')
        {
            int end = cmd.IndexOf('"', p + 1);
            if (end < 0) return null;
            return cmd.Substring(p + 1, end - p - 1);
        }
        int sp = cmd.IndexOf(' ', p);
        return sp < 0 ? cmd.Substring(p) : cmd.Substring(p, sp - p);
    }

    static System.Collections.Generic.List<int> ActiveSessions()
    {
        var res = new System.Collections.Generic.List<int>();
        IntPtr info; int count;
        if (!WTSEnumerateSessions(IntPtr.Zero, 0, 1, out info, out count)) return res;
        try
        {
            int size = Marshal.SizeOf(typeof(WTS_SESSION_INFO));
            for (int i = 0; i < count; i++)
            {
                WTS_SESSION_INFO s = (WTS_SESSION_INFO)Marshal.PtrToStructure(new IntPtr(info.ToInt64() + i * size), typeof(WTS_SESSION_INFO));
                if (s.SessionId != 0 && s.State == WTSActive) res.Add(s.SessionId);
            }
        }
        finally { WTSFreeMemory(info); }
        return res;
    }

    // ---------- helpers used by KvAgent ----------
    internal static string ScriptPath { get { return Script; } }
    internal static void AgentLog(string m) { Log(m); }

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern uint WaitForSingleObject(IntPtr h, uint ms);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool GetExitCodeProcess(IntPtr h, out uint code);
    [DllImport("wtsapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool WTSQuerySessionInformation(IntPtr server, int sessionId, int infoClass, out IntPtr buffer, out int bytes);

    internal static int FirstActiveSession()
    {
        var l = ActiveSessions();
        return l.Count > 0 ? l[0] : -1;
    }

    // Active student sessions and the name of the user logged on in the first one.
    internal static System.Collections.Generic.List<object> ActiveSessionsInfo(out string user)
    {
        user = "";
        var res = new System.Collections.Generic.List<object>();
        foreach (int sid in ActiveSessions())
        {
            res.Add(sid);
            if (user.Length == 0)
            {
                IntPtr buf; int n;
                if (WTSQuerySessionInformation(IntPtr.Zero, sid, 5, out buf, out n))   // WTSUserName
                {
                    try { user = Marshal.PtrToStringUni(buf) ?? ""; } finally { WTSFreeMemory(buf); }
                }
            }
        }
        return res;
    }

    // Run a command line in a student session (as that student); optionally wait for it.
    internal static bool RunInSession(int sessionId, string cmdLine, int waitMs, out int rc, out string err)
    {
        rc = 0; err = null;
        IntPtr hProc;
        int pid = LaunchH(sessionId, null, cmdLine, out err, out hProc);
        if (pid <= 0) return false;
        try
        {
            if (waitMs > 0 && hProc != IntPtr.Zero)
            {
                uint w = WaitForSingleObject(hProc, (uint)waitMs);
                if (w != 0) { rc = -1; return true; }   // still running after the timeout
                uint code; if (GetExitCodeProcess(hProc, out code)) rc = unchecked((int)code);
            }
            return true;
        }
        finally { if (hProc != IntPtr.Zero) CloseHandle(hProc); }
    }

    // vcfg\kvlogon.txt: one command line per line, started once in the student session at every logon
    // (replaces the "KhoaVeyonLogon" scheduled task).
    static void RunLogonList(int sessionId)
    {
        try
        {
            string dir = Path.GetDirectoryName(Script);
            if (string.IsNullOrEmpty(dir)) return;
            string f = Path.Combine(dir, "vcfg", "kvlogon.txt");
            if (!File.Exists(f)) return;
            foreach (string raw in File.ReadAllLines(f))
            {
                string l = (raw ?? "").Trim();
                if (l.Length == 0) continue;
                string err; int pid = Launch(sessionId, null, l, out err);
                if (pid <= 0) Log("session " + sessionId + ": logon command failed (" + err + ")");
            }
        }
        catch { }
    }

    // Launch a command line in the given session, hidden, as that student. app may be null (exe taken from cmdLine).
    // Returns the new process id (>0) on success, or -1 with err set.
    static int Launch(int sessionId, string app, string cmdLine, out string err)
    {
        IntPtr h;
        int pid = LaunchH(sessionId, app, cmdLine, out err, out h);
        if (h != IntPtr.Zero) CloseHandle(h);
        return pid;
    }

    // Same as Launch but keeps the process handle (caller must CloseHandle it) so the caller can wait for the exit code.
    static int LaunchH(int sessionId, string app, string cmdLine, out string err, out IntPtr hProc, bool visible = false)
    {
        err = null; hProc = IntPtr.Zero;
        IntPtr token, env = IntPtr.Zero;
        if (!WTSQueryUserToken(sessionId, out token)) { err = "no user token, error " + Marshal.GetLastWin32Error(); return -1; }
        try
        {
            if (!CreateEnvironmentBlock(out env, token, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = @"winsta0\default";
            si.dwFlags = STARTF_USESHOWWINDOW;
            si.wShowWindow = visible ? SW_SHOWNORMAL : SW_HIDE;   // a hidden start would also hide the first WinForms window of the process
            StringBuilder cmd = new StringBuilder(cmdLine);
            string cwd = Path.GetDirectoryName(Script);
            if (string.IsNullOrEmpty(cwd) || !Directory.Exists(cwd)) cwd = Environment.SystemDirectory;
            int flags = CREATE_NO_WINDOW | (env != IntPtr.Zero ? CREATE_UNICODE_ENVIRONMENT : 0);
            PROCESS_INFORMATION pi;
            if (!CreateProcessAsUser(token, app, cmd, IntPtr.Zero, IntPtr.Zero, false, flags, env, cwd, ref si, out pi))
            { err = "CreateProcessAsUser error " + Marshal.GetLastWin32Error(); return -1; }
            int newPid = pi.dwProcessId;
            CloseHandle(pi.hThread); hProc = pi.hProcess;
            return newPid;
        }
        finally
        {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            CloseHandle(token);
        }
    }

    // Same line format as Log() in the PowerShell part, so -exportlog picks these lines up too.
    static void Log(string m)
    {
        try
        {
            string dir = Path.GetDirectoryName(Script);
            if (string.IsNullOrEmpty(dir)) return;
            File.AppendAllText(Path.Combine(dir, "KhoaVeyonService.log"),
                DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  PC=" + Environment.MachineName +
                "  Student=-  RunAs=SYSTEM  [autolog-service]  " + m + Environment.NewLine);
        }
        catch { }
    }

    public static void Main(string[] args)
    {
        // ImagePath: "...\KhoaVeyonAutoLog.exe" "C:\cmd\KhoaVeyonServices.bat"
        if (args.Length > 0 && args[0].Length > 0) Script = args[0];
        ServiceBase.Run(new KvAutoLogService());
    }
}

// ---------------------------------------------------------------------------------------------
// KvAgent: lets the teacher PC control this PC WITHOUT a Windows admin account, the C$ share or
// remote Task Scheduler. This service calls OUT to the teacher PC (HTTP long-poll), receives jobs
// (run a command, write / read / list / delete a file) and posts the results back.
// Every message is signed with HMAC-SHA256 using the secret in %ProgramFiles%\KhoaVeyon\agent.cfg
// (admin-only folder, students cannot read it). The secret itself never goes over the network.
// ---------------------------------------------------------------------------------------------
public static class KvAgent
{
    const int Version = 1;
    static volatile bool stop;
    static Thread worker;
    static string token = "";
    static readonly List<string> urls = new List<string>();
    static readonly HashSet<string> seen = new HashSet<string>();
    static readonly object SeenGate = new object();
    static readonly DateTime Boot = DateTime.UtcNow;
    static bool lastOk = true;
    static DateTime lastLog = DateTime.MinValue;
    static DateTime lastClockTry = DateTime.MinValue;

    // Student side data folder (inbox: teacher -> student, outbox: student -> teacher, submit: handed-in work). Users may write there.
    public static string DataRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "KhoaVeyon");

    [StructLayout(LayoutKind.Sequential)]
    struct SYSTEM_POWER_STATUS { public byte ACLineStatus, BatteryFlag, BatteryLifePercent, SystemStatusFlag; public uint BatteryLifeTime, BatteryFullLifeTime; }
    [DllImport("kernel32.dll")]
    static extern bool GetSystemPowerStatus(out SYSTEM_POWER_STATUS s);

    static Dictionary<string, object> healthCache;
    static DateTime healthAt = DateTime.MinValue;
    // Small health report sent with every poll: free disk space, battery, Veyon service state (cached for a minute).
    static Dictionary<string, object> Health()
    {
        if (healthCache != null && (DateTime.UtcNow - healthAt).TotalSeconds < 60) return healthCache;
        var h = new Dictionary<string, object>();
        try { string sd = Environment.SystemDirectory; string dr = Path.GetPathRoot(string.IsNullOrEmpty(sd) ? DataRoot : sd); var di = new DriveInfo(dr); h["disk"] = (int)(100.0 * di.AvailableFreeSpace / di.TotalSize); h["diskgb"] = (int)(di.AvailableFreeSpace / 1073741824L); } catch { }
        try { SYSTEM_POWER_STATUS ps; if (GetSystemPowerStatus(out ps)) { h["ac"] = ps.ACLineStatus == 1; h["bat"] = ps.BatteryLifePercent <= 100 ? (int)ps.BatteryLifePercent : -1; } } catch { }
        try { using (var sc = new ServiceController("VeyonService")) h["veyon"] = sc.Status == ServiceControllerStatus.Running; } catch { }
        healthCache = h; healthAt = DateTime.UtcNow;
        return h;
    }

    static void EnsureDirs()
    {
        foreach (string n in new string[] { "", "inbox", "outbox", "submit" })
            Directory.CreateDirectory(string.IsNullOrEmpty(n) ? DataRoot : Path.Combine(DataRoot, n));
        try
        {
            var di = new DirectoryInfo(DataRoot);
            var sec = di.GetAccessControl();
            sec.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(WellKnownSidType.BuiltinUsersSid, null), FileSystemRights.Modify,
                InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
            di.SetAccessControl(sec);
        }
        catch { }
    }

    // Events written by the student helper (outbox\*.json: hand raise, hand-in) are posted to the teacher PC within ~2 seconds.
    static void EventLoop()
    {
        while (!stop)
        {
            try { SendEvents(); } catch { }
            Thread.Sleep(2000);
        }
    }

    static void SendEvents()
    {
        string dir = Path.Combine(DataRoot, "outbox");
        if (token.Length < 16 || !Directory.Exists(dir)) return;
        var evs = new List<object>();
        var used = new List<string>();
        foreach (string f in Directory.GetFiles(dir, "*.json"))
        {
            if (evs.Count >= 20) break;
            try
            {
                var fi = new FileInfo(f);
                if (fi.Length > 16384) { File.Delete(f); continue; }
                object o = Js().DeserializeObject(File.ReadAllText(f, Encoding.UTF8));
                if (o == null) { File.Delete(f); continue; }
                evs.Add(o); used.Add(f);
            }
            catch (IOException) { }                                   // still being written: next round
            catch { try { File.Delete(f); } catch { } }               // not valid JSON
        }
        if (evs.Count == 0) return;
        List<string> list;
        lock (urls) { list = new List<string>(urls); }
        foreach (string u in list)
        {
            try
            {
                string nonce = NewNonce();
                var body = new Dictionary<string, object>();
                body["host"] = Environment.MachineName;
                string user; KvAutoLogService.ActiveSessionsInfo(out user);
                body["user"] = user;
                body["events"] = evs;
                body["nonce"] = nonce;
                body["ts"] = Now();
                var reply = Post(u, "/agent/event", body, 10000);
                if (reply != null && Convert.ToString(reply["nonce"]) == nonce)
                {
                    foreach (string f in used) { try { File.Delete(f); } catch { } }
                    return;
                }
            }
            catch { }
        }
    }

    [StructLayout(LayoutKind.Sequential)]
    struct SYSTEMTIME { public ushort Year, Month, DayOfWeek, Day, Hour, Minute, Second, Millis; }
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool SetSystemTime(ref SYSTEMTIME st);

    // Self-heal a wrong clock (dead CMOS battery): the teacher PC rejects requests whose clock is off by more than 15 minutes,
    // so after a failed poll ask the teacher PC for its time (signed reply, echoes our nonce so it cannot be replayed) and set it.
    static void SyncClock()
    {
        if (stop || (DateTime.UtcNow - lastClockTry).TotalSeconds < 120) return;
        lastClockTry = DateTime.UtcNow;
        List<string> list;
        lock (urls) { list = new List<string>(urls); }
        foreach (string u in list)
        {
            try
            {
                string nonce = NewNonce();
                var req = (HttpWebRequest)WebRequest.Create(u + "/agent/time?n=" + nonce);
                req.Timeout = 8000; req.ReadWriteTimeout = 8000; req.Proxy = null; req.KeepAlive = false;
                byte[] buf;
                using (var resp = (HttpWebResponse)req.GetResponse())
                using (Stream rs = resp.GetResponseStream())
                using (var ms = new MemoryStream())
                {
                    rs.CopyTo(ms);
                    buf = ms.ToArray();
                    if (!SameSig(resp.Headers["X-KV-Sig"], Sign(buf))) continue;
                }
                var d = Js().DeserializeObject(Encoding.UTF8.GetString(buf)) as Dictionary<string, object>;
                if (d == null || Convert.ToString(d["nonce"]) != nonce) continue;
                double skew = Convert.ToDouble(d["ts"]) - Now();
                if (Math.Abs(skew) < 60) return;
                DateTime t = DateTime.UtcNow.AddSeconds(skew);
                var st = new SYSTEMTIME();
                st.Year = (ushort)t.Year; st.Month = (ushort)t.Month; st.Day = (ushort)t.Day; st.Hour = (ushort)t.Hour;
                st.Minute = (ushort)t.Minute; st.Second = (ushort)t.Second; st.Millis = (ushort)t.Millisecond;
                if (SetSystemTime(ref st)) { KvAutoLogService.AgentLog("agent: clock was off by " + (int)skew + "s, set from the teacher PC"); lastClockTry = DateTime.MinValue; }
                else KvAutoLogService.AgentLog("agent: cannot set the clock (error " + Marshal.GetLastWin32Error() + ")");
                return;
            }
            catch { }
        }
    }

    // %ProgramFiles%\KhoaVeyon\agent.cfg: "url=http://teacher-pc:8767" and "token=..." lines (written by Setup-MayHocSinh.bat).
    static string CfgFile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "KhoaVeyon", "agent.cfg");

    public static void Start()
    {
        stop = false;
        try { EnsureDirs(); } catch { }
        worker = new Thread(Loop);
        worker.IsBackground = true;
        worker.Start();
        var ev = new Thread(EventLoop);
        ev.IsBackground = true;
        ev.Start();
    }

    public static void Stop() { stop = true; }

    static System.Web.Script.Serialization.JavaScriptSerializer Js()
    {
        var js = new System.Web.Script.Serialization.JavaScriptSerializer();
        js.MaxJsonLength = int.MaxValue;
        return js;
    }

    static void LoadCfg()
    {
        var u = new List<string>();
        string t = "";
        try
        {
            foreach (string raw in File.ReadAllLines(CfgFile))
            {
                string l = (raw ?? "").Trim();
                int eq = l.IndexOf('=');
                if (eq <= 0) continue;
                string k = l.Substring(0, eq).Trim().ToLowerInvariant(), v = l.Substring(eq + 1).Trim();
                if (k == "url" && v.Length > 0) u.Add(v.TrimEnd('/'));
                else if (k == "token") t = v;
            }
        }
        catch { }
        lock (urls) { urls.Clear(); urls.AddRange(u); }
        token = t;
    }

    static string Hex(byte[] b)
    {
        var sb = new StringBuilder(b.Length * 2);
        foreach (byte x in b) sb.Append(x.ToString("x2"));
        return sb.ToString();
    }

    static string Sign(byte[] data)
    {
        using (var h = new System.Security.Cryptography.HMACSHA256(Encoding.ASCII.GetBytes(token)))
            return Hex(h.ComputeHash(data));
    }

    static string Sha256(byte[] data)
    {
        using (var h = System.Security.Cryptography.SHA256.Create()) return Hex(h.ComputeHash(data));
    }

    static bool SameSig(string a, string b)
    {
        if (a == null || b == null || a.Length != b.Length) return false;
        int d = 0;
        for (int i = 0; i < a.Length; i++) d |= a[i] ^ b[i];
        return d == 0;
    }

    static double Now() { return (DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds; }

    // POST a signed JSON body; returns the parsed, signature-checked reply.
    static Dictionary<string, object> Post(string baseUrl, string path, Dictionary<string, object> body, int timeoutMs)
    {
        byte[] data = Encoding.UTF8.GetBytes(Js().Serialize(body));
        var req = (HttpWebRequest)WebRequest.Create(baseUrl + path);
        req.Method = "POST";
        req.ContentType = "application/json";
        req.Timeout = timeoutMs;
        req.ReadWriteTimeout = timeoutMs;
        req.Proxy = null;
        req.KeepAlive = false;
        req.ServicePoint.Expect100Continue = false;
        req.Headers.Add("X-KV-Sig", Sign(data));
        req.ContentLength = data.Length;
        using (Stream s = req.GetRequestStream()) s.Write(data, 0, data.Length);
        using (var resp = (HttpWebResponse)req.GetResponse())
        {
            byte[] buf;
            using (Stream rs = resp.GetResponseStream())
            using (var ms = new MemoryStream())
            {
                rs.CopyTo(ms);
                buf = ms.ToArray();
            }
            if (!SameSig(resp.Headers["X-KV-Sig"], Sign(buf))) throw new Exception("bad reply signature");
            return Js().DeserializeObject(Encoding.UTF8.GetString(buf)) as Dictionary<string, object>;
        }
    }

    static string NewNonce()
    {
        var b = new byte[12];
        using (var r = System.Security.Cryptography.RandomNumberGenerator.Create()) r.GetBytes(b);
        return Hex(b);
    }

    static void Loop()
    {
        int bad = 0;
        while (!stop)
        {
            DateTime t0 = DateTime.UtcNow;
            try
            {
                LoadCfg();
                List<string> list;
                lock (urls) { list = new List<string>(urls); }
                if (token.Length < 16 || list.Count == 0) { Thread.Sleep(15000); continue; }

                Dictionary<string, object> reply = null;
                string nonce = NewNonce();
                Exception last = null;
                foreach (string u in list)
                {
                    try
                    {
                        var body = PollBody(nonce);
                        reply = Post(u, "/agent/poll", body, 40000);
                        if (reply != null) break;
                    }
                    catch (Exception e) { last = e; nonce = NewNonce(); }
                }
                if (reply == null) throw (last ?? new Exception("no reply"));
                if (Convert.ToString(reply["nonce"]) != nonce) throw new Exception("nonce mismatch");
                double ts = Convert.ToDouble(reply["ts"]);
                if (Math.Abs(Now() - ts) > 900) throw new Exception("clock skew");
                if (Math.Abs(Now() - ts) > 120) { try { SyncClock(); } catch { } }
                bad = 0;
                if (!lastOk) { KvAutoLogService.AgentLog("agent: connected again"); lastOk = true; }
                object[] jobs = AsArray(reply.ContainsKey("jobs") ? reply["jobs"] : null);
                foreach (object o in jobs)
                {
                    var job = o as Dictionary<string, object>;
                    if (job == null) continue;
                    string id = Convert.ToString(job["id"]);
                    lock (SeenGate)
                    {
                        if (seen.Contains(id)) continue;   // replayed job: ignore
                        if (seen.Count > 2000) seen.Clear();
                        seen.Add(id);
                    }
                    var j = job;
                    ThreadPool.QueueUserWorkItem(delegate { Handle(j); });
                }
            }
            catch (Exception e)
            {
                bad++;
                if (lastOk || (DateTime.Now - lastLog).TotalMinutes > 30)
                {
                    KvAutoLogService.AgentLog("agent: cannot reach the teacher PC (" + e.Message + ")");
                    lastLog = DateTime.Now;
                }
                lastOk = false;
                if (!stop) { try { SyncClock(); } catch { } }
                Thread.Sleep(Math.Min(30000, 3000 + bad * 2000));
                continue;
            }
            if ((DateTime.UtcNow - t0).TotalMilliseconds < 800) Thread.Sleep(800);
        }
    }

    static object[] AsArray(object o)
    {
        if (o == null) return new object[0];
        var arr = o as object[];
        if (arr != null) return arr;
        var al = o as System.Collections.ArrayList;
        if (al != null) return al.ToArray();
        return new object[0];
    }

    static Dictionary<string, object> PollBody(string nonce)
    {
        var d = new Dictionary<string, object>();
        d["host"] = Environment.MachineName;
        string user; var sessions = KvAutoLogService.ActiveSessionsInfo(out user);
        d["user"] = user;
        d["sessions"] = sessions;
        d["ver"] = Version;
        d["boot"] = (Boot - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
        try { d["health"] = Health(); } catch { }
        d["nonce"] = nonce;
        d["ts"] = Now();
        return d;
    }

    static void Reply(string id, Dictionary<string, object> res)
    {
        res["id"] = id;
        res["nonce"] = NewNonce();
        res["ts"] = Now();
        List<string> list;
        lock (urls) { list = new List<string>(urls); }
        foreach (string u in list)
        {
            try { Post(u, "/agent/result", res, 60000); return; }
            catch { }
        }
    }

    static string Tail(string s, int max)
    {
        if (s == null) return "";
        return s.Length <= max ? s : s.Substring(s.Length - max);
    }

    static string Str(Dictionary<string, object> j, string k)
    {
        object v;
        return j.TryGetValue(k, out v) && v != null ? Convert.ToString(v) : "";
    }

    static bool Flag(Dictionary<string, object> j, string k)
    {
        object v;
        if (!j.TryGetValue(k, out v) || v == null) return false;
        if (v is bool) return (bool)v;
        return Convert.ToString(v).ToLowerInvariant() == "true";
    }

    static double Epoch(DateTime utc) { return (utc - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds; }

    static void Handle(Dictionary<string, object> job)
    {
        string id = Str(job, "id");
        var res = new Dictionary<string, object>();
        try
        {
            string op = Str(job, "op");
            string path = Str(job, "path");
            if (op != "exec")
            {
                if (path.Length < 3 || path.Length > 400 || !Path.IsPathRooted(path) || path.StartsWith(@"\\")) throw new Exception("invalid path");
            }
            switch (op)
            {
                case "exec": DoExec(job, res); break;
                case "put":
                    {
                        byte[] data = Convert.FromBase64String(Str(job, "b64"));
                        string want = Str(job, "sha");
                        if (want.Length > 0 && Sha256(data) != want.ToLowerInvariant()) throw new Exception("hash mismatch");
                        string dir = Path.GetDirectoryName(path);
                        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                        string tmp = path + ".kvtmp";
                        File.WriteAllBytes(tmp, data);
                        if (File.Exists(path)) File.Delete(path);
                        File.Move(tmp, path);
                        res["ok"] = true;
                        break;
                    }
                case "get":
                    {
                        if (!File.Exists(path)) { res["ok"] = true; res["exists"] = false; break; }
                        var fi = new FileInfo(path);
                        if (fi.Length > 25 * 1024 * 1024) throw new Exception("file too large");
                        byte[] data;
                        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                        using (var ms = new MemoryStream()) { fs.CopyTo(ms); data = ms.ToArray(); }
                        res["ok"] = true; res["exists"] = true;
                        res["b64"] = Convert.ToBase64String(data);
                        res["sha"] = Sha256(data);
                        break;
                    }
                case "ls":
                    {
                        if (!Directory.Exists(path)) { res["ok"] = true; res["exists"] = false; break; }
                        var entries = new List<object>();
                        var di = new DirectoryInfo(path);
                        foreach (var d in di.GetDirectories())
                        {
                            var e = new Dictionary<string, object>();
                            e["n"] = d.Name; e["s"] = 0; e["m"] = Epoch(d.LastWriteTimeUtc); e["d"] = true;
                            entries.Add(e);
                        }
                        foreach (var f in di.GetFiles())
                        {
                            var e = new Dictionary<string, object>();
                            e["n"] = f.Name; e["s"] = f.Length; e["m"] = Epoch(f.LastWriteTimeUtc); e["d"] = false;
                            entries.Add(e);
                            if (entries.Count >= 5000) break;
                        }
                        res["ok"] = true; res["exists"] = true; res["entries"] = entries;
                        break;
                    }
                case "stat":
                    {
                        res["ok"] = true;
                        if (File.Exists(path))
                        {
                            var fi = new FileInfo(path);
                            res["exists"] = true; res["size"] = fi.Length; res["mtime"] = Epoch(fi.LastWriteTimeUtc);
                            if (Flag(job, "sha"))
                            {
                                using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                                using (var h = System.Security.Cryptography.SHA256.Create()) res["sha"] = Hex(h.ComputeHash(fs));
                            }
                        }
                        else if (Directory.Exists(path)) { res["exists"] = true; res["size"] = 0; res["mtime"] = Epoch(Directory.GetLastWriteTimeUtc(path)); }
                        else res["exists"] = false;
                        break;
                    }
                case "rm":
                    {
                        if (File.Exists(path)) { File.SetAttributes(path, FileAttributes.Normal); File.Delete(path); res["ok"] = true; }
                        else if (Directory.Exists(path)) { Directory.Delete(path, true); res["ok"] = true; }
                        else { res["ok"] = true; res["exists"] = false; }
                        break;
                    }
                default: throw new Exception("unknown op " + op);
            }
        }
        catch (Exception e)
        {
            res["ok"] = false;
            res["out"] = e.Message;
        }
        Reply(id, res);
    }

    static void DoExec(Dictionary<string, object> job, Dictionary<string, object> res)
    {
        string cmd = Str(job, "cmd");
        if (cmd.Length == 0 || cmd.Length > 8000) throw new Exception("invalid command");
        bool wait = Flag(job, "wait");
        int timeout = 60;
        try { timeout = Math.Max(1, Math.Min(900, Convert.ToInt32(job["timeout"]))); } catch { }
        string cwd = Path.GetDirectoryName(KvAutoLogService.ScriptPath);
        if (string.IsNullOrEmpty(cwd) || !Directory.Exists(cwd)) cwd = Environment.SystemDirectory;

        if (Str(job, "session") == "user")
        {
            int sid = KvAutoLogService.FirstActiveSession();
            if (sid < 0) throw new Exception("Chưa có ai đăng nhập Windows trên máy này");
            int rc; string err;
            if (!KvAutoLogService.RunInSession(sid, cmd, wait ? timeout * 1000 : 0, out rc, out err)) throw new Exception(err);
            res["ok"] = true; res["rc"] = rc;
            return;
        }

        var psi = new ProcessStartInfo();
        psi.FileName = Path.Combine(Environment.SystemDirectory, "cmd.exe");
        psi.Arguments = "/s /c \"" + cmd + "\"";
        psi.UseShellExecute = false;
        psi.CreateNoWindow = true;
        psi.WorkingDirectory = cwd;
        if (!wait)
        {
            Process.Start(psi);
            res["ok"] = true; res["rc"] = 0;
            return;
        }
        psi.RedirectStandardOutput = true;
        psi.RedirectStandardError = true;
        psi.RedirectStandardInput = true;
        var sb = new StringBuilder();
        using (var p = new Process())
        {
            p.StartInfo = psi;
            DataReceivedEventHandler h = delegate (object s, DataReceivedEventArgs a)
            {
                if (a.Data != null) lock (sb) { if (sb.Length < 20000) sb.AppendLine(a.Data); }
            };
            p.OutputDataReceived += h;
            p.ErrorDataReceived += h;
            p.Start();
            p.StandardInput.Close();   // like "<nul": scripts that call pause do not hang
            p.BeginOutputReadLine();
            p.BeginErrorReadLine();
            if (!p.WaitForExit(timeout * 1000))
            {
                try { p.Kill(); } catch { }
                res["ok"] = true; res["rc"] = -1; res["out"] = "timeout";
                return;
            }
            p.WaitForExit();
            res["ok"] = true; res["rc"] = p.ExitCode;
            lock (sb) { res["out"] = Tail(sb.ToString(), 1500); }
        }
    }
}
'@

# 1. Remove the scheduled task left by older versions, so logging is not started twice.
try { Unregister-ScheduledTask -TaskName $svcName -Confirm:$false -ErrorAction Stop } catch {}

# 2. Stop the service if it already exists (re-install), so its exe can be replaced.
$existing = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if ($existing -and $existing.Status -ne 'Stopped') {
    Stop-Service -Name $svcName -Force -ErrorAction SilentlyContinue
    try { $existing.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(20)) } catch {}
}

# 3. Compile the service with the C# compiler that ships with .NET Framework 4 (Windows 8/10/11).
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $csc)) { $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path -LiteralPath $csc)) { Write-Host 'AutoLog service: csc.exe (.NET Framework 4) not found'; exit 1 }
if (-not (Test-Path -LiteralPath $svcDir)) { New-Item -ItemType Directory -Path $svcDir -Force | Out-Null }
$csFile = Join-Path $env:TEMP 'KhoaVeyonAutoLog.cs'
$newExe = Join-Path $env:TEMP 'KhoaVeyonAutoLog.new.exe'
Set-Content -LiteralPath $csFile -Value $csSource -Encoding UTF8
Remove-Item -LiteralPath $newExe -Force -ErrorAction SilentlyContinue
$cscOut = & $csc /nologo /target:winexe /optimize+ /r:System.ServiceProcess.dll /r:System.Web.Extensions.dll "/out:$newExe" $csFile 2>&1
Remove-Item -LiteralPath $csFile -Force -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $newExe)) {
    Write-Host 'AutoLog service: compile failed'; $cscOut | ForEach-Object { Write-Host "  $_" }
    if (-not (Test-Path -LiteralPath $svcExe)) { exit 1 }
    Write-Host 'AutoLog service: keeping the exe from the previous install'
} else {
    # Make sure the old service process is really gone, then delete the old exe so the new one is always put in place
    # (the compile above succeeded, so the old exe is no longer needed as a fallback).
    Get-Process -Name 'KhoaVeyonAutoLog' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Remove-Item -LiteralPath $svcExe -Force -ErrorAction SilentlyContinue
    try { Move-Item -LiteralPath $newExe -Destination $svcExe -Force -ErrorAction Stop }
    catch { Write-Host "AutoLog service: cannot replace $svcExe ($_)"; if (-not (Test-Path -LiteralPath $svcExe)) { exit 1 } }
}

# 4. Create the service, or point the existing one at the new exe / script path.
if ($existing) {
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$svcName" -Name ImagePath -Value $binPath
    Set-Service -Name $svcName -StartupType Automatic
} else {
    try {
        New-Service -Name $svcName -BinaryPathName $binPath -StartupType Automatic `
            -DisplayName 'KhoaVeyon AutoLog' -ErrorAction Stop | Out-Null
    } catch { Write-Host "AutoLog service: create failed ($_)"; exit 1 }
}
& sc.exe description $svcName 'KhoaVeyon: starts the activity log (-activitylog-start) in every student session at logon.' | Out-Null
# Students may only see the service, not stop or change it (same idea as KhoaVeyonService_*).
& sc.exe sdset $svcName 'D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)' | Out-Null
# If it ever crashes, Windows restarts it after 1 minute.
& sc.exe failure $svcName reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null

# 5. Start it now (it also starts the log for a student who is already logged on).
Start-Service -Name $svcName -ErrorAction SilentlyContinue
$s = Get-Service -Name $svcName -ErrorAction SilentlyContinue
try { $s.WaitForStatus('Running', [TimeSpan]::FromSeconds(15)) } catch {}
$s.Refresh()
if ($s.Status -ne 'Running') { Write-Host "AutoLog service: installed but not running (status $($s.Status))"; exit 1 }
Write-Host "AutoLog service: $svcName is running ($svcExe)"
exit 0
#KVSVCEND

#PS1START
$ErrorActionPreference = 'Continue'
$mode = $env:KV_MODE
$dir  = $env:KV_DIR
$list = $env:KV_LIST
$log  = Join-Path $dir 'KhoaVeyonService.log'
if (@('killapp','keepapp','lockdown','unlock','mute','unmute','activitylog-start','activitylog-stop','exportlog','lockapp-start','lockapp-stop','clearhistory','lockrun-start','lockrun-stop','lockall-start','lockall-stop') -contains $mode) { $log = Join-Path $env:TEMP 'KhoaVeyonService.log' }
$sid  = '*S-1-5-32-545'
$pcname   = $env:COMPUTERNAME
$logdir   = 'C:\cmd\log'
$stopFlag = Join-Path $logdir ("activity_{0}.stop" -f $pcname)
$pidFile  = Join-Path $logdir ("activity_{0}.pid" -f $pcname)
$lockStopFlag = Join-Path $logdir ("lockapp_{0}.stop" -f $pcname)
$lockPidFile  = Join-Path $logdir ("lockapp_{0}.pid" -f $pcname)
if (-not (Test-Path $logdir)) { New-Item -ItemType Directory -Path $logdir -Force -ErrorAction SilentlyContinue | Out-Null }
function TodayCsv { Join-Path $logdir ("activity_{0}_{1}.csv" -f $pcname, (Get-Date -Format 'yyyy-MM-dd')) }
$actCsv = TodayCsv

# Who is actually sitting at this PC right now (the student), even when this code is
# running as SYSTEM/admin on their behalf. Falls back to the process account if nobody
# is logged on (for example right after -install, before any student has logged in).
function CurrentStudent {
    try {
        $u = (Get-CimInstance Win32_ComputerSystem -ErrorAction Stop).UserName
        if ($u) { return $u }
    } catch {}
    return $env:USERNAME
}
$kvStudent = CurrentStudent
$kvRunAs   = $env:USERNAME   # the account this PowerShell process itself is running as

function Log($m) {
    try {
        Add-Content -Path $log -Value ("{0}  PC={1}  Student={2}  RunAs={3}  [{4}]  {5}" -f `
            (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $pcname, $kvStudent, $kvRunAs, $mode, $m)
    } catch {}
}

# Explorer only reads the RestrictRun policy when it starts, so restart it (Windows relaunches it by itself)
function Restart-UserShell {
    $sess = (Get-Process -Id $PID).SessionId
    Get-Process -Name explorer -ErrorAction SilentlyContinue | Where-Object { $_.SessionId -eq $sess } | Stop-Process -Force -ErrorAction SilentlyContinue
}

# ---------- read column A of the first sheet of an .xlsx (Excel not needed) ----------
function Read-ColumnA($file) {
    $out = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path -LiteralPath $file)) { Log "File not found: $file"; return @() }
    Add-Type -AssemblyName System.IO.Compression
    $fs  = [IO.File]::Open($file, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $zip = New-Object IO.Compression.ZipArchive($fs, [IO.Compression.ZipArchiveMode]::Read)
    try {
        $shared = @()
        $e = $zip.GetEntry('xl/sharedStrings.xml')
        if ($e) {
            $r = New-Object IO.StreamReader($e.Open())
            $x = New-Object Xml.XmlDocument
            $x.LoadXml($r.ReadToEnd()); $r.Close()
            foreach ($si in $x.SelectNodes('//*[local-name()="si"]')) {
                $shared += (($si.SelectNodes('.//*[local-name()="t"]') | ForEach-Object { $_.InnerText }) -join '')
            }
        }
        $e = $zip.GetEntry('xl/worksheets/sheet1.xml')
        if (-not $e) {
            $e = $zip.Entries | Where-Object { $_.FullName -like 'xl/worksheets/sheet*.xml' } | Sort-Object FullName | Select-Object -First 1
        }
        if (-not $e) { Log "No worksheet found in $file"; return @() }
        $r = New-Object IO.StreamReader($e.Open())
        $x = New-Object Xml.XmlDocument
        $x.LoadXml($r.ReadToEnd()); $r.Close()
        foreach ($c in $x.SelectNodes('//*[local-name()="c"]')) {
            if ($c.GetAttribute('r') -notmatch '^A\d+$') { continue }
            $t = $c.GetAttribute('t'); $val = $null
            if ($t -eq 's') {
                $v = $c.SelectSingleNode('*[local-name()="v"]')
                if ($v) { $val = $shared[[int]$v.InnerText] }
            } elseif ($t -eq 'inlineStr') {
                $val = ($c.SelectNodes('.//*[local-name()="t"]') | ForEach-Object { $_.InnerText }) -join ''
            } else {
                $v = $c.SelectSingleNode('*[local-name()="v"]')
                if ($v) { $val = $v.InnerText }
            }
            if ($val) { $out.Add($val.Trim()) }
        }
    } finally { $zip.Dispose(); $fs.Dispose() }
    return $out.ToArray()
}

# ---------- IP helpers ----------
function ToLong($ip) {
    $b = [Net.IPAddress]::Parse($ip).GetAddressBytes()
    return ([long]$b[0] * 16777216) + ([long]$b[1] * 65536) + ([long]$b[2] * 256) + [long]$b[3]
}
function ToIp([long]$n) {
    return '{0}.{1}.{2}.{3}' -f (($n -shr 24) -band 255), (($n -shr 16) -band 255), (($n -shr 8) -band 255), ($n -band 255)
}

# ---------- firewall ----------
function Remove-Rules {
    Get-NetFirewallRule -DisplayName 'KhoaVeyonBlock*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
}

function Apply-Block($extra) {
    Remove-Rules
    $allow = New-Object System.Collections.Generic.List[object]
    $lan = @(
        @('10.0.0.0','10.255.255.255'),
        @('127.0.0.0','127.255.255.255'),
        @('169.254.0.0','169.254.255.255'),
        @('172.16.0.0','172.31.255.255'),
        @('192.168.0.0','192.168.255.255'),
        @('224.0.0.0','239.255.255.255'),
        @('255.255.255.255','255.255.255.255')
    )
    foreach ($p in $lan) { $allow.Add(@((ToLong $p[0]), (ToLong $p[1]))) }
    foreach ($ip in $extra) { $n = ToLong $ip; $allow.Add(@($n, $n)) }

    # block everything that is NOT inside an allowed range
    $sorted = @($allow | Sort-Object { $_[0] })
    $ranges = New-Object System.Collections.Generic.List[string]
    $next = [long]0
    foreach ($a in $sorted) {
        if ($a[0] -gt $next) { $ranges.Add((ToIp $next) + '-' + (ToIp ($a[0] - 1))) }
        if (($a[1] + 1) -gt $next) { $next = $a[1] + 1 }
    }
    if ($next -le 4294967295) { $ranges.Add((ToIp $next) + '-' + (ToIp 4294967295)) }

    New-NetFirewallRule -DisplayName 'KhoaVeyonBlock'  -Direction Outbound -Action Block -Profile Any -RemoteAddress $ranges.ToArray() | Out-Null
    New-NetFirewallRule -DisplayName 'KhoaVeyonBlock6' -Direction Outbound -Action Block -Profile Any -RemoteAddress '2000::/3' | Out-Null
}


# ---------- AI blocking helpers (-blockai / -allowai) ----------
# Backup of the settings that were there before -blockai. It lives in a folder only SYSTEM and
# Administrators can write (NOT C:\cmd\log, which students can write), because -allowai replays it as SYSTEM.
$aiDir    = Join-Path $env:ProgramData 'KhoaVeyon'
$aiBackup = Join-Path $aiDir 'ai_backup.json'
$aiHostsBegin = '# KhoaVeyon-AI-BEGIN'
$aiHostsEnd   = '# KhoaVeyon-AI-END'
$aiHostsFile  = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
# Used when BlockAIList.xlsx is missing; the Excel list is the real, editable list
$aiBuiltIn = @('chatgpt.com','openai.com','gemini.google.com','claude.ai','copilot.microsoft.com','perplexity.ai','deepseek.com','grok.com')
# Never block these as a whole (a typo in the list must not cut off the whole internet). A path such as bing.com/chat is fine.
$aiTooBroad = @('google.com','microsoft.com','bing.com','live.com','office.com','windows.com','windowsupdate.com','github.com','youtube.com','wikipedia.org','x.com','apple.com','amazon.com','facebook.com')
$global:AiRec = New-Object System.Collections.Generic.List[object]

function Get-AiTargets {
    $items = @($aiBuiltIn) + @(Read-ColumnA (Join-Path $list 'BlockAIList.xlsx'))
    $res = New-Object System.Collections.Generic.List[object]
    $seen = @{}
    foreach ($i in $items) {
        if (-not $i) { continue }
        $s = ([string]$i).ToLower().Trim()
        $s = $s -replace '^[a-z]+://', ''
        $s = $s -replace '[?#].*$', ''
        $s = $s.TrimEnd('/')
        $s = $s -replace '^www\.', ''
        if ($s -notmatch '^[a-z0-9-]+(\.[a-z0-9-]+)+(/[A-Za-z0-9._~%/-]*)?$') { continue }
        $hasPath = $s.Contains('/')
        $hostName = ($s -split '/')[0]
        if (-not $hasPath -and ($aiTooBroad -contains $hostName)) { Log "SKIPPED (too broad, would block normal sites): $s"; continue }
        if ($seen.ContainsKey($s)) { continue }
        $seen[$s] = $true
        $res.Add([pscustomobject]@{ Url = $s; HostName = $hostName; HasPath = $hasPath })
    }
    return $res.ToArray()
}

function Ai-Remember-Value($path, $name) {
    $ex = $false; $val = $null; $kind = 'DWord'
    try {
        $k = Get-Item -LiteralPath $path -ErrorAction Stop
        if ($k.GetValueNames() -contains $name) { $ex = $true; $val = $k.GetValue($name); $kind = [string]$k.GetValueKind($name) }
    } catch {}
    $global:AiRec.Add([pscustomobject]@{ T = 'v'; Path = $path; Name = $name; Existed = $ex; Value = $val; Kind = $kind })
}

function Ai-Set-Dword($path, $name, $value) {
    try {
        if (-not (Test-Path -LiteralPath $path)) { New-Item -Path $path -Force | Out-Null }
        Ai-Remember-Value $path $name
        New-ItemProperty -LiteralPath $path -Name $name -Value ([int]$value) -PropertyType DWord -Force | Out-Null
    } catch { Log ("Policy not set {0}\{1}: {2}" -f $path, $name, $_.Exception.Message) }
}

function Ai-Set-String($path, $name, $value) {
    try {
        if (-not (Test-Path -LiteralPath $path)) { New-Item -Path $path -Force | Out-Null }
        Ai-Remember-Value $path $name
        New-ItemProperty -LiteralPath $path -Name $name -Value ([string]$value) -PropertyType String -Force | Out-Null
    } catch { Log ("Policy not set {0}\{1}: {2}" -f $path, $name, $_.Exception.Message) }
}

# List policies (URLBlocklist ...) are values named 1, 2, 3 ... Keep what the school already has and add ours.
function Ai-Set-List($path, $newItems) {
    try {
        $keyExisted = Test-Path -LiteralPath $path
        $existing = @()
        if ($keyExisted) {
            $k = Get-Item -LiteralPath $path
            $existing = @($k.GetValueNames() | Where-Object { $_ -match '^\d+$' } | Sort-Object { [int]$_ } | ForEach-Object { [string]$k.GetValue($_) })
        } else { New-Item -Path $path -Force | Out-Null }
        $global:AiRec.Add([pscustomobject]@{ T = 'l'; Path = $path; KeyExisted = $keyExisted; Items = @($existing) })
        $all = New-Object System.Collections.Generic.List[string]
        foreach ($e in $existing) { $all.Add($e) }
        foreach ($n in $newItems) { if ($all -notcontains $n) { $all.Add($n) } }
        foreach ($nm in @((Get-Item -LiteralPath $path).GetValueNames() | Where-Object { $_ -match '^\d+$' })) {
            Remove-ItemProperty -LiteralPath $path -Name $nm -ErrorAction SilentlyContinue
        }
        $n = 1
        foreach ($v in $all) { New-ItemProperty -LiteralPath $path -Name ([string]$n) -Value $v -PropertyType String -Force | Out-Null; $n++ }
    } catch { Log ("List policy not set {0}: {1}" -f $path, $_.Exception.Message) }
}

function Ai-Restore {
    if (-not (Test-Path -LiteralPath $aiBackup)) { return $false }
    $bk = $null
    try { $bk = Get-Content -LiteralPath $aiBackup -Raw | ConvertFrom-Json } catch { Log "AI backup unreadable: $($_.Exception.Message)"; return $false }
    foreach ($r in @($bk)) {
        try {
            # Only ever touch the policy area, even if the backup file was edited
            if (-not ([string]$r.Path).StartsWith('HKLM:\SOFTWARE\Policies\', [StringComparison]::OrdinalIgnoreCase)) { Log "Restore skipped (path not allowed): $($r.Path)"; continue }
            if ($r.T -eq 'v') {
                if ($r.Existed) {
                    if (-not (Test-Path -LiteralPath $r.Path)) { New-Item -Path $r.Path -Force | Out-Null }
                    $kind = if ($r.Kind) { [string]$r.Kind } else { 'DWord' }
                    $val = $r.Value
                    if ($kind -eq 'DWord') { $val = [int]$val }
                    New-ItemProperty -LiteralPath $r.Path -Name $r.Name -Value $val -PropertyType $kind -Force | Out-Null
                } else {
                    Remove-ItemProperty -LiteralPath $r.Path -Name $r.Name -ErrorAction SilentlyContinue
                }
            } elseif ($r.T -eq 'l') {
                if (Test-Path -LiteralPath $r.Path) {
                    foreach ($nm in @((Get-Item -LiteralPath $r.Path).GetValueNames() | Where-Object { $_ -match '^\d+$' })) {
                        Remove-ItemProperty -LiteralPath $r.Path -Name $nm -ErrorAction SilentlyContinue
                    }
                    $n = 1
                    foreach ($v in @($r.Items)) { if ($v) { New-ItemProperty -LiteralPath $r.Path -Name ([string]$n) -Value ([string]$v) -PropertyType String -Force | Out-Null; $n++ } }
                }
            }
        } catch { Log ("Restore error {0}: {1}" -f $r.Path, $_.Exception.Message) }
    }
    # remove policy keys we created and that are now empty
    foreach ($path in @($bk | ForEach-Object { $_.Path } | Sort-Object -Unique -Descending)) {
        try {
            if (-not ([string]$path).StartsWith('HKLM:\SOFTWARE\Policies\', [StringComparison]::OrdinalIgnoreCase)) { continue }
            if (Test-Path -LiteralPath $path) {
                $k = Get-Item -LiteralPath $path
                if ($k.ValueCount -eq 0 -and $k.SubKeyCount -eq 0) { Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue }
            }
        } catch {}
    }
    return $true
}

function Ai-Hosts-Remove {
    try {
        if (-not (Test-Path -LiteralPath $aiHostsFile)) { return }
        $lines = @([IO.File]::ReadAllLines($aiHostsFile))
        $out = New-Object System.Collections.Generic.List[string]
        $skip = $false; $found = $false
        foreach ($l in $lines) {
            if ($l.Trim() -eq $aiHostsBegin) { $skip = $true; $found = $true; continue }
            if ($l.Trim() -eq $aiHostsEnd) { $skip = $false; continue }
            if (-not $skip) { $out.Add($l) }
        }
        if ($skip) { Log 'hosts: BEGIN marker without END, hosts file left unchanged'; return }
        if ($found) { [IO.File]::WriteAllLines($aiHostsFile, $out.ToArray(), (New-Object Text.UTF8Encoding($false))) }
    } catch { Log "hosts remove failed: $($_.Exception.Message)" }
}

function Ai-Hosts-Add($names) {
    try {
        Ai-Hosts-Remove
        $add = New-Object System.Collections.Generic.List[string]
        $add.Add($aiHostsBegin)
        foreach ($h in $names) {
            foreach ($n in @($h, ('www.' + $h))) { $add.Add('0.0.0.0 ' + $n); $add.Add(':: ' + $n) }
        }
        $add.Add($aiHostsEnd)
        $lines = @([IO.File]::ReadAllLines($aiHostsFile))
        [IO.File]::WriteAllLines($aiHostsFile, ($lines + $add.ToArray()), (New-Object Text.UTF8Encoding($false)))
        return $true
    } catch { Log "hosts write failed: $($_.Exception.Message)"; return $false }
}

function Ai-Lock-Folder($dirPath) {
    if (-not (Test-Path -LiteralPath $dirPath)) { New-Item -ItemType Directory -Path $dirPath -Force | Out-Null }
    # S-1-5-18 SYSTEM, S-1-5-32-544 Administrators: nobody else can read or write
    icacls $dirPath /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
}

# ---------- "only allowed pages" via browser policy (-webonly / -weboff) ----------
# Blocks EVERY page except the domains in AllowPage.xlsx, at the BROWSER level (Chrome/Edge/Brave/Coc Coc/Chromium).
# Unlike the firewall -allowpage, a listed domain also covers ALL its subdomains, and the allowed pages may still
# send requests (XHR/fetch) to the listed domains (Firebase, Google Fonts, MongoDB, other APIs). No IP pinning,
# so it does not break when a cloud service answers from a different IP. Runs as SYSTEM (HKLM policy).
$pageDir    = Join-Path $env:ProgramData 'KhoaVeyon'
$pageBackup = Join-Path $pageDir 'pageonly_backup.json'
$pageRoots  = @('HKLM:\SOFTWARE\Policies\Google\Chrome', 'HKLM:\SOFTWARE\Policies\Microsoft\Edge',
                'HKLM:\SOFTWARE\Policies\BraveSoftware\Brave', 'HKLM:\SOFTWARE\Policies\CocCoc\CocCoc',
                'HKLM:\SOFTWARE\Policies\Chromium')

function Page-AllowFromList {
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($i in @(Read-ColumnA (Join-Path $list 'AllowPage.xlsx'))) {
        $d = ((([string]$i).ToLower().Trim()) -replace '^[a-z]+://', '') -replace '[/?#:].*$', ''
        $d = $d -replace '^www\.', ''
        if ($d -match '^\d{1,3}(\.\d{1,3}){3}$' -or $d -match '^[a-z0-9-]+(\.[a-z0-9-]+)+$') { if ($out -notcontains $d) { $out.Add($d) } }
    }
    return $out.ToArray()
}
function Page-ListVals($root, $name) {
    $k = Join-Path $root $name
    if (-not (Test-Path -LiteralPath $k)) { return @() }
    $item = Get-Item -LiteralPath $k
    return @($item.GetValueNames() | Where-Object { $_ -match '^\d+$' } | Sort-Object { [int]$_ } | ForEach-Object { [string]$item.GetValue($_) })
}
function Page-SetListVals($root, $name, $vals) {
    $k = Join-Path $root $name
    $vals = @($vals | Where-Object { $_ -ne $null -and $_ -ne '' })
    if ($vals.Count -eq 0) {
        if (Test-Path -LiteralPath $k) {
            foreach ($nm in @((Get-Item -LiteralPath $k).GetValueNames() | Where-Object { $_ -match '^\d+$' })) { Remove-ItemProperty -LiteralPath $k -Name $nm -ErrorAction SilentlyContinue }
            $kk = Get-Item -LiteralPath $k; if ($kk.ValueCount -eq 0 -and $kk.SubKeyCount -eq 0) { Remove-Item -LiteralPath $k -Force -ErrorAction SilentlyContinue }
        }
        return
    }
    if (-not (Test-Path -LiteralPath $k)) { New-Item -Path $k -Force | Out-Null }
    foreach ($nm in @((Get-Item -LiteralPath $k).GetValueNames() | Where-Object { $_ -match '^\d+$' })) { Remove-ItemProperty -LiteralPath $k -Name $nm -ErrorAction SilentlyContinue }
    $n = 1; foreach ($v in $vals) { New-ItemProperty -LiteralPath $k -Name ([string]$n) -Value ([string]$v) -PropertyType String -Force | Out-Null; $n++ }
}
function Page-Start {
    $allow = Page-AllowFromList
    if ($allow.Count -eq 0) { Log 'WEBONLY refused: AllowPage.xlsx is empty (would block the whole web).'; return }
    if (-not (Test-Path -LiteralPath $pageDir)) { New-Item -ItemType Directory -Path $pageDir -Force | Out-Null }
    # Dang o che do webonly roi (bam khoa lan hai, hoac thi + bam tay): GIU ban sao luu GOC. Neu ghi de bang trang thai da khoa thi -weboff chi khoi phuc lai
    # chinh trang thai khoa va khong the mo lai duoc.
    $orig = $null
    if (Test-Path -LiteralPath $pageBackup) { try { $orig = @(Get-Content -LiteralPath $pageBackup -Raw | ConvertFrom-Json) } catch { $orig = $null } }
    $rec = New-Object System.Collections.Generic.List[object]
    foreach ($root in $pageRoots) {
        $o = $null
        if ($orig) { $o = @($orig | Where-Object { [string]$_.Root -eq $root })[0] }
        if ($o) {
            $rootExisted = [bool]$o.RootExisted
            $prevBlock = @($o.Block | Where-Object { $_ })
            $prevAllow = @($o.Allow | Where-Object { $_ })
            $starWas = [bool]$o.StarWasThere
        } else {
            $rootExisted = Test-Path -LiteralPath $root
            $prevBlock = @(Page-ListVals $root 'URLBlocklist')
            $prevAllow = @(Page-ListVals $root 'URLAllowlist')
            $starWas = ($prevBlock -contains '*')
        }
        $rec.Add([pscustomobject]@{ Root = $root; RootExisted = $rootExisted; Block = $prevBlock; Allow = $prevAllow; StarWasThere = $starWas })
        $nb = New-Object System.Collections.Generic.List[string]; foreach ($e in $prevBlock) { $nb.Add($e) }; if ($nb -notcontains '*') { $nb.Add('*') }
        Page-SetListVals $root 'URLBlocklist' $nb.ToArray()
        $na = New-Object System.Collections.Generic.List[string]; foreach ($e in $prevAllow) { $na.Add($e) }; foreach ($d in $allow) { if ($na -notcontains $d) { $na.Add($d) } }
        Page-SetListVals $root 'URLAllowlist' $na.ToArray()
    }
    [IO.File]::WriteAllText($pageBackup, ($rec | ConvertTo-Json -Depth 5))
    # Close Chromium browsers so the next launch reads the new policy
    Get-Process -Name chrome, msedge, brave, browser, chromium -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Log ("WEBONLY ON: {0} allowed domain(s) + their subdomains in browser policy: {1}" -f $allow.Count, ($allow -join ', '))
}
function Page-Stop {
    if (Test-Path -LiteralPath $pageBackup) {
        $bk = $null
        try { $bk = Get-Content -LiteralPath $pageBackup -Raw | ConvertFrom-Json } catch { Log 'WEBONLY backup unreadable, doing best-effort cleanup'; $bk = $null }
        if ($bk) {
            foreach ($r in @($bk)) {
                if (-not ([string]$r.Root).StartsWith('HKLM:\SOFTWARE\Policies\', [StringComparison]::OrdinalIgnoreCase)) { continue }
                # '*' la do KhoaVeyon them. Ban sao luu cu (tu phien ban truoc) co the da bi ghi de bang trang thai da khoa nen luon bo '*', tru khi truoc do da co san (StarWasThere).
                $blk = @($r.Block | Where-Object { $_ })
                if (-not $r.StarWasThere) { $blk = @($blk | Where-Object { $_ -ne '*' }) }
                Page-SetListVals $r.Root 'URLBlocklist' $blk
                Page-SetListVals $r.Root 'URLAllowlist' @($r.Allow | Where-Object { $_ })
                if (-not $r.RootExisted -and (Test-Path -LiteralPath $r.Root)) {
                    $k = Get-Item -LiteralPath $r.Root; if ($k.ValueCount -eq 0 -and $k.SubKeyCount -eq 0) { Remove-Item -LiteralPath $r.Root -Force -ErrorAction SilentlyContinue }
                }
            }
            Remove-Item -LiteralPath $pageBackup -Force -ErrorAction SilentlyContinue
            Log 'WEBONLY OFF: browser policy restored.'
            return
        }
    }
    # No readable backup: just take the "*" we added back out of every blocklist
    foreach ($root in $pageRoots) { Page-SetListVals $root 'URLBlocklist' @(Page-ListVals $root 'URLBlocklist' | Where-Object { $_ -ne '*' }) }
    Log 'WEBONLY OFF: removed the block-all rule (no backup to restore from).'
}

# ---------- modes ----------
switch ($mode) {

    'killapp' {
        $protect = @('explorer','cmd','conhost','powershell','pwsh','veyon-server','veyon-worker','veyon-service','veyon-master',
                     'applicationframehost','shellexperiencehost','startmenuexperiencehost','searchhost','textinputhost',
                     'systemsettings','sihost','ctfmon','dwm')
        $session = (Get-Process -Id $PID).SessionId
        $closed = @()
        foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
            if ($p.SessionId -ne $session -or $p.MainWindowHandle -eq 0) { continue }
            $n = $p.ProcessName.ToLower()
            if ($protect -contains $n) { continue }
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            $closed += $n
        }
        Log ("Closed {0} app(s): {1}" -f $closed.Count, ($closed -join ', '))
    }

    'blockall' {
        Apply-Block @()
        Log 'Internet BLOCKED (LAN allowed)'
    }

    'webonly' { Page-Start }
    'weboff'  { Page-Stop }

    'allowall' {
        Remove-Rules
        # -webonly khoa bang chinh sach trinh duyet chu khong phai tuong lua, nen "Cho phep internet" cung phai go no (chi khi chinh KhoaVeyon da bat: co file sao luu)
        if (Test-Path -LiteralPath $pageBackup) { Page-Stop }
        Log 'Internet ALLOWED'
    }

    'allowpage' {
        Remove-Rules   # so DNS works while we look the sites up
        $items = @(Read-ColumnA (Join-Path $list 'AllowPage.xlsx'))
        $names = @()
        foreach ($i in $items) {
            $d = ($i.ToLower() -replace '^[a-z]+://', '') -replace '[/?#:].*$', ''
            if ($d -match '^\d{1,3}(\.\d{1,3}){3}$' -or $d -match '^[a-z0-9-]+(\.[a-z0-9-]+)+$') { $names += $d }
        }
        $names = @($names | Select-Object -Unique)

        $ips = New-Object System.Collections.Generic.HashSet[string]
        foreach ($d in $names) {
            if ($d -match '^\d{1,3}(\.\d{1,3}){3}$') { [void]$ips.Add($d); continue }
            $try = @($d)
            if ($d -notlike 'www.*') { $try += "www.$d" }
            foreach ($h in $try) {
                $res = Resolve-DnsName $h -Type A -DnsOnly -ErrorAction SilentlyContinue | Where-Object { $_.Type -eq 'A' }
                foreach ($r in $res) { [void]$ips.Add($r.IPAddress) }
            }
        }
        # keep the DNS servers reachable, otherwise names cannot be resolved
        Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            ForEach-Object { $_.ServerAddresses } | Where-Object { $_ } | ForEach-Object { [void]$ips.Add($_) }

        Apply-Block @($ips)
        Log ("Internet BLOCKED except {0} sites ({1} IPs): {2}" -f $names.Count, $ips.Count, ($names -join ', '))
    }

    'blockapp' {
        $blockedFile = Join-Path $dir 'blocked.txt'
        $done = @()
        if (Test-Path -LiteralPath $blockedFile) { $done = @(Get-Content -LiteralPath $blockedFile) }
        $skip = @($env:windir, (Join-Path $env:ProgramFiles 'Veyon'), $dir.TrimEnd('\'))
        $items = @(Read-ColumnA (Join-Path $list 'BlockAppList.xlsx')) | Where-Object { $_ -match '^[A-Za-z]:\\' -or $_ -match '^\\\\' }

        foreach ($raw in $items) {
            $p = [Environment]::ExpandEnvironmentVariables($raw).Trim('"')
            $targets = @()
            if ($p -match '[\*\?]') {
                $targets = @(Get-ChildItem -Path $p -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
            } elseif (Test-Path -LiteralPath $p) {
                $targets = @($p)
            } else {
                Log "Not found: $p"
            }
            foreach ($t in $targets) {
                $bad = ($t.Length -le 3)
                foreach ($s in $skip) { if ($t -like "$s*") { $bad = $true } }
                if ($bad) { Log "SKIPPED (protected): $t"; continue }

                if (Test-Path -LiteralPath $t -PathType Container) {
                    icacls $t /deny "${sid}:(OI)(CI)(X)" | Out-Null
                    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path -like "$t\*" } | Stop-Process -Force -ErrorAction SilentlyContinue
                } else {
                    icacls $t /deny "${sid}:(X)" | Out-Null
                    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path -eq $t } | Stop-Process -Force -ErrorAction SilentlyContinue
                }
                if ($done -notcontains $t) { $done += $t }
                Log "Blocked: $t"
            }
        }
        if ($done.Count -gt 0) { Set-Content -LiteralPath $blockedFile -Value $done }
    }

    'unblockapp' {
        $blockedFile = Join-Path $dir 'blocked.txt'
        if (Test-Path -LiteralPath $blockedFile) {
            foreach ($t in @(Get-Content -LiteralPath $blockedFile)) {
                if ($t -and (Test-Path -LiteralPath $t)) {
                    icacls $t /remove:d $sid | Out-Null
                    Log "Unblocked: $t"
                }
            }
            Remove-Item -LiteralPath $blockedFile -Force -ErrorAction SilentlyContinue
        } else {
            Log 'Nothing to unblock'
        }
    }

    # ---------- the modes below run as the logged-in user (no admin needed) ----------

    'keepapp' {
        $keepNames = @(); $keepPaths = @()
        foreach ($k in @(Read-ColumnA (Join-Path $list 'KeepAppList.xlsx'))) {
            $k = [Environment]::ExpandEnvironmentVariables($k).Trim('"')
            if ($k -match '\\') { $keepPaths += $k.TrimEnd('\') }
            elseif ($k) { $keepNames += ($k -replace '\.exe$', '').ToLower() }
        }
        $protect = @('explorer','cmd','conhost','powershell','pwsh','veyon-server','veyon-worker','veyon-service','veyon-master',
                     'applicationframehost','shellexperiencehost','startmenuexperiencehost','searchhost','textinputhost',
                     'systemsettings','sihost','ctfmon','dwm')
        $session = (Get-Process -Id $PID).SessionId
        foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
            if ($p.SessionId -ne $session -or $p.MainWindowHandle -eq 0) { continue }
            $n = $p.ProcessName.ToLower()
            if ($protect -contains $n -or $keepNames -contains $n) { continue }
            $path = $null
            try { $path = $p.Path } catch {}
            if ($path) {
                $kept = $false
                foreach ($kp in $keepPaths) { if ($path -like "$kp*") { $kept = $true } }
                if ($kept) { continue }
            }
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            Log "Closed: $n"
        }
        Log ("Kept names: {0}; kept paths: {1}" -f ($keepNames -join ', '), ($keepPaths -join ', '))
    }

    'lockapp-start' {
        # Kiosk mode: continuously allow ONLY the apps in KeepAppList.xlsx. Anything else
        # with a visible window is closed within a few seconds of opening.
        $already = $false
        if (Test-Path $lockPidFile) {
            $oldPid = (Get-Content $lockPidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
            if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) { $already = $true }
        }
        if ($already) {
            Log 'Kiosk mode (lockapp) already running'
        } else {
            Remove-Item -LiteralPath $lockStopFlag -ErrorAction SilentlyContinue
            $keepNames = @(); $keepPaths = @()
            foreach ($k in @(Read-ColumnA (Join-Path $list 'KeepAppList.xlsx'))) {
                $k = [Environment]::ExpandEnvironmentVariables($k).Trim('"')
                if ($k -match '\\') { $keepPaths += $k.TrimEnd('\') }
                elseif ($k) { $keepNames += ($k -replace '\.exe$', '').ToLower() }
            }
            # Pass the resolved whitelist (a snapshot of KeepAppList.xlsx at this moment)
            # into the background worker. Run -lockapp-stop then -lockapp-start again to
            # pick up changes made to the Excel file afterward.
            $namesLit = ($keepNames | ForEach-Object { "'" + ($_ -replace "'", "''") + "'" }) -join ','
            $pathsLit = ($keepPaths | ForEach-Object { "'" + ($_ -replace "'", "''") + "'" }) -join ','
            # KV_STRICT=1 (set by -lockall-start): cmd, PowerShell, Settings are NOT exempt from closing
            $prot = @('explorer','veyon-server','veyon-worker','veyon-service','veyon-master','applicationframehost','shellexperiencehost','startmenuexperiencehost','searchhost','textinputhost','sihost','ctfmon','dwm')
            if ($env:KV_STRICT -ne '1') { $prot += @('cmd','conhost','powershell','pwsh','systemsettings') }
            $protLit = ($prot | ForEach-Object { "'" + $_ + "'" }) -join ','
            $strictLit = if ($env:KV_STRICT -eq '1') { '$true' } else { '$false' }
            $psCmd = @"
`$stop  = '$lockStopFlag'
`$log   = '$log'
`$mode  = 'lockapp-start'
`$keepNames = @($namesLit)
`$keepPaths = @($pathsLit)
`$protect = @($protLit)
`$strict = $strictLit
function Log(`$m) { try { Add-Content -Path `$log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  [lockapp]  ' + `$m) } catch {} }
`$session = (Get-Process -Id `$PID).SessionId
while (-not (Test-Path `$stop)) {
    try {
        foreach (`$p in @(Get-Process -ErrorAction SilentlyContinue)) {
            if (`$p.SessionId -ne `$session) { continue }
            if (`$p.MainWindowHandle -eq 0) {
                if (-not `$strict) { continue }
                `$pp = `$null
                try { `$pp = `$p.Path } catch {}
                if (-not `$pp -or `$pp -notlike '*\WindowsApps\*') { continue }
            }
            `$n = `$p.ProcessName.ToLower()
            if (`$protect -contains `$n -or `$keepNames -contains `$n) { continue }
            `$path = `$null
            try { `$path = `$p.Path } catch {}
            if (`$path) {
                `$kept = `$false
                foreach (`$kp in `$keepPaths) { if (`$path -like "`$kp*") { `$kept = `$true } }
                if (`$kept) { continue }
            }
            Stop-Process -Id `$p.Id -Force -ErrorAction SilentlyContinue
            Log "Closed (not in KeepAppList): `$n"
        }
    } catch {}
    Start-Sleep -Seconds 3
}
"@
            $tmp = Join-Path $logdir ("lockapp_{0}_worker.ps1" -f $pcname)
            Set-Content -LiteralPath $tmp -Value $psCmd -Encoding UTF8
            $p = Start-Process powershell -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',$tmp) -WindowStyle Hidden -PassThru
            Set-Content -LiteralPath $lockPidFile -Value $p.Id
            Log ("Kiosk mode STARTED (pid $($p.Id)). Allowed: {0} {1}" -f ($keepNames -join ', '), ($keepPaths -join ', '))
        }
    }

    'lockapp-stop' {
        New-Item -ItemType File -Path $lockStopFlag -Force -ErrorAction SilentlyContinue | Out-Null
        Start-Sleep -Seconds 1
        if (Test-Path $lockPidFile) {
            $oldPid = Get-Content $lockPidFile -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($oldPid) { Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue }
            Remove-Item -LiteralPath $lockPidFile -ErrorAction SilentlyContinue
        }
        Log 'Kiosk mode (lockapp) STOPPED'
    }

    'clearhistory' {
        # Browsers must be closed first: the history file is locked while they run.
        Get-Process -Name 'chrome','firefox' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        $cleared = @()

        # Chrome / Chromium-based: delete only the History file(s). Bookmarks live in a
        # separate "Bookmarks" file and are not touched.
        $chromeRoot = Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data'
        if (Test-Path -LiteralPath $chromeRoot) {
            Get-ChildItem -LiteralPath $chromeRoot -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -eq 'Default' -or $_.Name -like 'Profile *' } |
                ForEach-Object {
                    foreach ($f in @('History','History-journal')) {
                        $p = Join-Path $_.FullName $f
                        if (Test-Path -LiteralPath $p) {
                            Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
                            $cleared += "Chrome:$($_.Name)"
                        }
                    }
                }
        }

        # Firefox: history and bookmarks share one file (places.sqlite). There is no
        # built-in SQLite tool here to remove just the history rows, so the whole file
        # is deleted, which also clears bookmarks. See README for details.
        $ffRoot = Join-Path $env:APPDATA 'Mozilla\Firefox\Profiles'
        if (Test-Path -LiteralPath $ffRoot) {
            Get-ChildItem -LiteralPath $ffRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
                foreach ($f in @('places.sqlite','places.sqlite-wal','places.sqlite-shm')) {
                    $p = Join-Path $_.FullName $f
                    if (Test-Path -LiteralPath $p) {
                        Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
                        $cleared += "Firefox:$($_.Name)"
                    }
                }
            }
        }

        Log ("Cleared browsing history: {0}" -f (($cleared | Select-Object -Unique) -join ', '))
    }

    'lockrun-start' {
        # Stops apps from OPENING at all (Windows "RestrictRun" policy). Only the apps in
        # KeepAppList.xlsx (plus a few system/Veyon ones) can be launched from Explorer,
        # Start menu, desktop icons, etc. Others show "This operation has been cancelled".
        # Entries: process name (chrome / chrome.exe) or a folder path (every .exe inside it).
        try {
            $ErrorActionPreference = 'Stop'
            $names = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
            $kl = @(Read-ColumnA (Join-Path $list 'KeepAppList.xlsx'))
            if ($kl.Count -eq 0) { Log 'WARNING: KeepAppList.xlsx is empty or not found, only system apps will be allowed' }
            foreach ($k in $kl) {
                $k = [Environment]::ExpandEnvironmentVariables($k).Trim('"')
                if ($k -match '\\') {
                    $root = $k.TrimEnd('\')
                    if (Test-Path -LiteralPath $root -PathType Container) {
                        Get-ChildItem -LiteralPath $root -Filter *.exe -Recurse -ErrorAction SilentlyContinue | ForEach-Object { [void]$names.Add($_.Name) }
                    } elseif (Test-Path -LiteralPath $root -PathType Leaf) {
                        [void]$names.Add([IO.Path]::GetFileName($root))
                    } else { Log "Not found: $root" }
                } elseif ($k) {
                    if ($k -notmatch '\.exe$') { $k = $k + '.exe' }
                    [void]$names.Add($k)
                }
            }
            foreach ($n in @('explorer.exe','ctfmon.exe','veyon-server.exe','veyon-worker.exe','veyon-service.exe','veyon-master.exe','veyon-configurator.exe')) { [void]$names.Add($n) }

            $pol = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer'
            $rr  = $pol + '\RestrictRun'
            if (-not (Test-Path $pol)) { New-Item -Path $pol -Force | Out-Null }
            if (Test-Path $rr) { Remove-Item -Path $rr -Recurse -Force }
            New-Item -Path $rr -Force | Out-Null
            $i = 1
            foreach ($n in @($names | Sort-Object)) {
                New-ItemProperty -Path $rr -Name ([string]$i) -Value $n -PropertyType String -Force | Out-Null
                $i++
            }
            New-ItemProperty -Path $pol -Name RestrictRun -Value 1 -PropertyType DWord -Force | Out-Null
            $ErrorActionPreference = 'Continue'
            Restart-UserShell
            Log ("Open-block ON (RestrictRun). {0} exe(s) allowed: {1}" -f $names.Count, (@($names | Sort-Object) -join ', '))
        } catch {
            Log ("ERROR in lockrun-start: " + $_.Exception.Message)
        }
    }

    'lockrun-stop' {
        $pol = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer'
        Remove-ItemProperty -Path $pol -Name RestrictRun -ErrorAction SilentlyContinue
        Remove-Item -Path ($pol + '\RestrictRun') -Recurse -Force -ErrorAction SilentlyContinue
        Restart-UserShell
        Log 'Open-block OFF (RestrictRun removed)'
    }

    'blockai' {
        # Block ALL AI: (1) AI websites in Chrome/Edge/Brave/Firefox (URL blocklist), (2) AI built into those browsers,
        # (3) hosts file for any other browser, (4) AI desktop apps are closed. Runs as SYSTEM through the service.
        try {
            $already = Test-Path -LiteralPath $aiBackup
            if ($already) { [void](Ai-Restore) }          # start again from the original settings, so entries removed from the list do not stay behind
            $global:AiRec = New-Object System.Collections.Generic.List[object]
            Ai-Lock-Folder $aiDir

            # Options: defaults come from the KV_AI_* env (set at the top of this .bat); an optional
            # ai_opts.txt in the list folder (written by KhoaVeyon) overrides them. KEY=1/0 per line.
            $optExt = ($env:KV_AI_EXT -eq '1'); $optDoh = $true; $optOverview = $true
            $optFile = Join-Path $list 'ai_opts.txt'
            if (Test-Path -LiteralPath $optFile) {
                foreach ($ln in @(Get-Content -LiteralPath $optFile -ErrorAction SilentlyContinue)) {
                    if ($ln -match '^\s*([A-Za-z]+)\s*=\s*([01])\s*$') {
                        switch ($matches[1].ToUpper()) {
                            'EXT'      { $optExt = ($matches[2] -eq '1') }
                            'DOH'      { $optDoh = ($matches[2] -eq '1') }
                            'OVERVIEW' { $optOverview = ($matches[2] -eq '1') }
                        }
                    }
                }
            }

            $targets = @(Get-AiTargets)
            $urls    = @($targets | ForEach-Object { $_.Url })
            $hostNames = @($targets | Where-Object { -not $_.HasPath } | ForEach-Object { $_.HostName } | Select-Object -Unique)
            $ffPatterns = @($targets | ForEach-Object {
                if ($_.HasPath) { '*://*.' + $_.HostName + '/' + (($_.Url -split '/', 2)[1]) + '*' } else { '*://*.' + $_.HostName + '/*' }
            })

            # --- Chrome ---
            $cr = 'HKLM:\SOFTWARE\Policies\Google\Chrome'
            $chromeDw = [ordered]@{
                GenAiDefaultSettings = 2; GeminiSettings = 1; AIModeSettings = 1; SearchContentSharingSettings = 1
                LensOverlaySettings = 1; GenAILocalFoundationalModelSettings = 1; HelpMeWriteSettings = 2; HelpMeReadSettings = 2
                TabOrganizerSettings = 2; CreateThemesSettings = 2; HistorySearchSettings = 2; TabCompareSettings = 2; DevToolsGenAiSettings = 2
            }
            foreach ($k in $chromeDw.Keys) { Ai-Set-Dword $cr $k $chromeDw[$k] }
            Ai-Set-List ($cr + '\URLBlocklist') $urls

            # --- Edge ---
            $ed = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge'
            $edgeDw = [ordered]@{
                HubsSidebarEnabled = 0; Microsoft365CopilotChatIconEnabled = 0; CopilotPageContext = 0; EdgeEntraCopilotPageContext = 0
                EdgeCopilotEnabled = 0; ComposeInlineEnabled = 0; GenAILocalFoundationalModelSettings = 1
            }
            foreach ($k in $edgeDw.Keys) { Ai-Set-Dword $ed $k $edgeDw[$k] }
            Ai-Set-List ($ed + '\URLBlocklist') $urls

            # --- Brave (Leo) ---
            $bv = 'HKLM:\SOFTWARE\Policies\BraveSoftware\Brave'
            Ai-Set-Dword $bv 'BraveAIChatEnabled' 0
            Ai-Set-List ($bv + '\URLBlocklist') $urls

            # --- Firefox (AI controls + website filter) ---
            $ff = 'HKLM:\SOFTWARE\Policies\Mozilla\Firefox'
            foreach ($k in @('Enabled', 'Chatbot', 'LinkPreviews', 'TabGroups')) { Ai-Set-Dword ($ff + '\GenerativeAI') $k 0 }
            Ai-Set-Dword ($ff + '\GenerativeAI') 'Locked' 1
            Ai-Set-List ($ff + '\WebsiteFilter\Block') $ffPatterns
            foreach ($k in @('Default', 'Translations', 'PDFAltText', 'SmartTabGroups', 'LinkPreviewKeyPoints', 'SidebarChatbot', 'SmartWindow')) {
                $kp = $ff + '\AIControls\' + $k
                try {
                    if (-not (Test-Path -LiteralPath $kp)) { New-Item -Path $kp -Force | Out-Null }
                    Ai-Remember-Value $kp 'Value'
                    New-ItemProperty -LiteralPath $kp -Name 'Value' -Value 'blocked' -PropertyType String -Force | Out-Null
                    Ai-Set-Dword $kp 'Locked' 1
                } catch { Log ("Firefox AIControls {0}: {1}" -f $k, $_.Exception.Message) }
            }

            # --- AI Overviews in Google Search: force the default search to the "Web" filter (udm=14), which
            #     shows classic links with NO AI Overview / AI Mode. Covers omnibox (address-bar) searches on
            #     Chrome and Edge. NOTE: a manual search typed on google.com itself can still show an overview;
            #     only an allow-list (chỉ trang cho phép) removes it entirely. ---
            if ($optOverview) {
                $udm = 'https://www.google.com/search?q={searchTerms}&udm=14'
                foreach ($br in @($cr, $ed)) {
                    Ai-Set-Dword  $br 'DefaultSearchProviderEnabled' 1
                    Ai-Set-String $br 'DefaultSearchProviderName' 'Google (khong AI Overview)'
                    Ai-Set-String $br 'DefaultSearchProviderKeyword' 'google.com'
                    Ai-Set-String $br 'DefaultSearchProviderSearchURL' $udm
                }
                # Chrome: also turn off the Search Generative Experience / AI Mode entry points in the omnibox
                Ai-Set-Dword $cr 'GenAiDefaultSettings' 2
            }

            # --- DNS-over-HTTPS off, so the hosts-file block for AI sites cannot be bypassed by encrypted DNS ---
            if ($optDoh) {
                foreach ($br in @($cr, $ed, $bv)) { Ai-Set-String $br 'DnsOverHttpsMode' 'off' }
                Ai-Set-Dword ($ff + '\DNSOverHTTPS') 'Enabled' 0
                Ai-Set-Dword ($ff + '\DNSOverHTTPS') 'Locked' 1
            }

            # --- Optional: no browser extensions at all (AI helper extensions). Turns OFF every extension,
            #     not just AI ones, so it is opt-in (KhoaVeyon toggle writes EXT=1 in ai_opts.txt). ---
            if ($optExt) {
                foreach ($br in @($cr, $ed, $bv)) { Ai-Set-List ($br + '\ExtensionInstallBlocklist') @('*') }
            }

            # --- Windows (older Copilot policy, Recall) ---
            Ai-Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot' 'TurnOffWindowsCopilot' 1
            Ai-Set-Dword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI' 'DisableAIDataAnalysis' 1

            # --- Save the backup of what was there before (SYSTEM/Administrators only) ---
            ConvertTo-Json -InputObject @($global:AiRec.ToArray()) -Depth 5 | Set-Content -LiteralPath $aiBackup -Encoding UTF8

            # --- hosts file ---
            $hostsOk = $false
            if ($env:KV_AI_HOSTS -eq '1') { $hostsOk = [bool](Ai-Hosts-Add $hostNames) } else { Ai-Hosts-Remove }
            & ipconfig /flushdns | Out-Null

            # --- AI desktop apps: close them now (add their install folder to BlockAppList.xlsx to keep them blocked) ---
            $appNames = @('chatgpt', 'claude', 'copilot', 'perplexity', 'deepseek')
            $closedApps = @()
            foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
                if ($appNames -contains $p.ProcessName.ToLower()) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; $closedApps += $p.ProcessName }
            }

            # --- Close open browsers the first time, so an AI tab that is already open stops working ---
            $closedBrowsers = 0
            if ($env:KV_AI_CLOSE -eq '1' -and -not $already) {
                $bn = @('chrome', 'msedge', 'firefox', 'brave', 'opera', 'vivaldi')
                foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
                    $n = $p.ProcessName.ToLower()
                    $hit = ($bn -contains $n)
                    if (-not $hit -and $n -eq 'browser') { try { if ($p.Path -like '*CocCoc*') { $hit = $true } } catch {} }
                    if ($hit) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; $closedBrowsers++ }
                }
            }

            $chk = (Get-ItemProperty -Path $cr -Name GenAiDefaultSettings -ErrorAction SilentlyContinue).GenAiDefaultSettings
            Log ("AI BLOCKED. {0} entries ({1} hosts, hosts file written={2}); Chrome GenAiDefaultSettings={3}; closed {4} browser process(es), apps: {5}; overview(udm14)={6}, doh_off={7}, block_extensions={8}" -f $urls.Count, $hostNames.Count, $hostsOk, $chk, $closedBrowsers, ($closedApps -join ','), $optOverview, $optDoh, $optExt)
        } catch {
            Log ("ERROR in blockai: " + $_.Exception.Message)
        }
    }

    'allowai' {
        try {
            $restored = Ai-Restore
            Ai-Hosts-Remove
            & ipconfig /flushdns | Out-Null
            if (Test-Path -LiteralPath $aiBackup) { Remove-Item -LiteralPath $aiBackup -Force -ErrorAction SilentlyContinue }
            Log ("AI ALLOWED again. Settings restored from backup: {0}" -f $restored)
        } catch {
            Log ("ERROR in allowai: " + $_.Exception.Message)
        }
    }

    'lockall-start' {
        # ONE command = block all apps except KeepAppList.xlsx:
        #  1) lockdown: Task Manager + Settings off     2) Registry Editor off (so the rules cannot be removed)
        #  3) lockrun : apps cannot be OPENED           4) kiosk (strict): anything else that appears is closed in ~3 s
        $self = $env:KV_SELF
        & $self '-lockapp-stop'
        & $self '-lockdown'
        $sys = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\System'
        if (-not (Test-Path $sys)) { New-Item -Path $sys -Force | Out-Null }
        New-ItemProperty -Path $sys -Name DisableRegistryTools -Value 1 -PropertyType DWord -Force | Out-Null
        & $self '-lockrun-start'
        $env:KV_STRICT = '1'
        & $self '-lockapp-start'
        $env:KV_STRICT = $null
        Start-Sleep -Seconds 1
        $chk = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer' -Name RestrictRun -ErrorAction SilentlyContinue).RestrictRun
        $kp = $null
        if (Test-Path $lockPidFile) { $kp = Get-Content $lockPidFile -ErrorAction SilentlyContinue | Select-Object -First 1 }
        $alive = [bool]($kp -and (Get-Process -Id $kp -ErrorAction SilentlyContinue))
        Log ("LOCKALL ON. CHECK: RestrictRun={0}, kiosk worker running={1}" -f $chk, $alive)
    }

    'lockall-stop' {
        $self = $env:KV_SELF
        Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\System' -Name DisableRegistryTools -ErrorAction SilentlyContinue
        & $self '-lockrun-stop'
        & $self '-lockapp-stop'
        & $self '-unlock'
        Log 'LOCKALL OFF'
    }

    'lockdown' {
        $sys = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\System'
        $exp = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer'
        foreach ($k in @($sys, $exp)) { if (-not (Test-Path $k)) { New-Item -Path $k -Force | Out-Null } }
        New-ItemProperty -Path $sys -Name DisableTaskMgr  -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $exp -Name NoControlPanel  -Value 1 -PropertyType DWord -Force | Out-Null
        Stop-Process -Name Taskmgr, SystemSettings -Force -ErrorAction SilentlyContinue
        Log 'Lockdown ON (Task Manager and Settings disabled)'
    }

    'unlock' {
        Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\System'   -Name DisableTaskMgr -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer' -Name NoControlPanel -ErrorAction SilentlyContinue
        Log 'Lockdown OFF (Task Manager and Settings enabled)'
    }

    { $_ -eq 'mute' -or $_ -eq 'unmute' } {
        $src = @"
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, ref Guid pguidEventContext);
    int GetMute(out bool pbMute);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {
    int Activate(ref Guid id, int clsCtx, IntPtr activationParams, out IAudioEndpointVolume aev);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject { }

public class KvAudio {
    static IAudioEndpointVolume Vol() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));
        IAudioEndpointVolume epv = null;
        var epvid = typeof(IAudioEndpointVolume).GUID;
        Marshal.ThrowExceptionForHR(dev.Activate(ref epvid, 23, IntPtr.Zero, out epv));
        return epv;
    }
    public static void SetMute(bool m) { Guid ctx = Guid.Empty; Marshal.ThrowExceptionForHR(Vol().SetMute(m, ref ctx)); }
}
"@
        try {
            Add-Type -TypeDefinition $src
            [KvAudio]::SetMute(($mode -eq 'mute'))
            Log ("Speakers " + $(if ($mode -eq 'mute') { 'MUTED' } else { 'UNMUTED' }))
        } catch {
            Log "Mute failed: $_"
        }
    }

    'activitylog-start' {
        # Records which window/app is in front, with date, time and PC name.
        # Does NOT record keystrokes, typed text, or passwords.
        $already = $false
        if (Test-Path $pidFile) {
            $oldPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
            if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) { $already = $true }
        }
        if ($already) {
            Log 'Activity log already running'
        } else {
            Remove-Item -LiteralPath $stopFlag -ErrorAction SilentlyContinue
            $worker = @'
using System;
using System.Runtime.InteropServices;
public class KvWin {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@
            # One CSV per day (C:\cmd\log\activity_<PC>_<yyyy-MM-dd>.csv), appended all day long.
            # - a row is added the moment the active window changes (near real time)
            # - a row is also added every 3 minutes even with no change, so the file is
            #   never more than 3 minutes out of date ("auto save")
            # - at midnight the worker switches to the next day's file by itself
            $psCmd = @"
Add-Type -TypeDefinition @'
$worker
'@
`$logdir  = '$logdir'
`$stop    = '$stopFlag'
`$user    = '$env:USERNAME'
`$pc      = '$pcname'
`$actionLogs = @('$((Join-Path $dir 'KhoaVeyonService.log') -replace "'","''")', '$((Join-Path $env:TEMP 'KhoaVeyonService.log') -replace "'","''")')
`$last   = ''
`$lastFlush = Get-Date
function CsvFor(`$d) { Join-Path `$logdir ("activity_{0}_{1}.csv" -f `$pc, `$d.ToString('yyyy-MM-dd')) }
function EnsureHeader(`$f) { if (-not (Test-Path -LiteralPath `$f)) { Set-Content -LiteralPath `$f -Value 'Date,Time,PCName,User,Window,Process,Event' } }
function MergeActions(`$csv) {
    foreach (`$f in `$actionLogs) {
        if (-not (Test-Path -LiteralPath `$f)) { continue }
        `$marker = Join-Path `$logdir ("export_{0}_{1}.pos" -f `$pc, ([IO.Path]::GetFileName(`$f) -replace '[\\/:]', '_'))
        `$lastPos = 0
        if (Test-Path -LiteralPath `$marker) { `$lastPos = [int](Get-Content -LiteralPath `$marker -ErrorAction SilentlyContinue | Select-Object -First 1) }
        `$lines = @(Get-Content -LiteralPath `$f)
        `$s = [Math]::Min(`$lastPos, `$lines.Count)
        for (`$i = `$s; `$i -lt `$lines.Count; `$i++) {
            if (`$lines[`$i] -match '^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\s+(.*)`$') {
                `$d2 = `$matches[3] -replace '"','""'
                Add-Content -LiteralPath `$csv -Value ('"{0}","{1}","{2}","{3}","","","action: {4}"' -f `$matches[1], `$matches[2], `$pc, `$user, `$d2)
            }
        }
        Set-Content -LiteralPath `$marker -Value `$lines.Count
    }
}
while (-not (Test-Path `$stop)) {
    try {
        `$now = Get-Date
        `$csv = CsvFor `$now
        EnsureHeader `$csv
        `$h = [KvWin]::GetForegroundWindow()
        `$sb = New-Object System.Text.StringBuilder 256
        [void][KvWin]::GetWindowText(`$h, `$sb, 256)
        `$title = `$sb.ToString()
        `$procId = 0
        [void][KvWin]::GetWindowThreadProcessId(`$h, [ref]`$procId)
        `$procName = ''
        try { `$procName = (Get-Process -Id `$procId -ErrorAction Stop).ProcessName } catch {}
        `$cur = "`$title|`$procName"
        `$changed = (`$title -and `$cur -ne `$last)
        `$due3min = ((`$now - `$lastFlush).TotalSeconds -ge 180)
        if (`$changed -or `$due3min) {
            `$t = `$title -replace '"','""'
            `$evt = if (`$changed) { 'change' } else { 'autosave' }
            Add-Content -LiteralPath `$csv -Value ('"{0}","{1}","{2}","{3}","{4}","{5}","{6}"' -f `$now.ToString('yyyy-MM-dd'), `$now.ToString('HH:mm:ss'), `$pc, `$user, `$t, `$procName, `$evt)
            `$last = `$cur
            if (`$due3min) { MergeActions `$csv; `$lastFlush = `$now }
        }
    } catch {}
    Start-Sleep -Seconds 3
}
"@
            $tmp = Join-Path $logdir ("activity_{0}_worker.ps1" -f $pcname)
            Set-Content -LiteralPath $tmp -Value $psCmd -Encoding UTF8
            $p = Start-Process powershell -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',$tmp) -WindowStyle Hidden -PassThru
            Set-Content -LiteralPath $pidFile -Value $p.Id
            Log ("Activity log STARTED (pid $($p.Id)) -> $actCsv")
        }
    }

    'activitylog-stop' {
        New-Item -ItemType File -Path $stopFlag -Force -ErrorAction SilentlyContinue | Out-Null
        Start-Sleep -Seconds 1
        if (Test-Path $pidFile) {
            $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($oldPid) { Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue }
            Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
        }
        Log 'Activity log STOPPED'
    }

    'exportlog' {
        # Merges today's action-log lines (block/allow/app-block/etc.) into today's single
        # daily CSV, as extra rows with Event = "action". Keeps everything in one file per day.
        $csv = TodayCsv
        if (-not (Test-Path -LiteralPath $csv)) {
            Set-Content -LiteralPath $csv -Value 'Date,Time,PCName,User,Window,Process,Event'
        }
        $added = 0
        foreach ($f in @((Join-Path $dir 'KhoaVeyonService.log'), (Join-Path $env:TEMP 'KhoaVeyonService.log'))) {
            if (-not (Test-Path -LiteralPath $f)) { continue }
            $markerFile = Join-Path $logdir ("export_{0}_{1}.pos" -f $pcname, ([IO.Path]::GetFileName($f) -replace '[\\/:]', '_'))
            $lastPos = 0
            if (Test-Path -LiteralPath $markerFile) { $lastPos = [int](Get-Content -LiteralPath $markerFile -ErrorAction SilentlyContinue | Select-Object -First 1) }
            $lines = @(Get-Content -LiteralPath $f)
            $start = [Math]::Min($lastPos, $lines.Count)
            for ($i = $start; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\s+(.*)$') {
                    $d2 = $matches[3] -replace '"','""'
                    Add-Content -LiteralPath $csv -Value ('"{0}","{1}","{2}","{3}","","","action: {4}"' -f $matches[1], $matches[2], $pcname, $env:USERNAME, $d2)
                    $added++
                }
            }
            Set-Content -LiteralPath $markerFile -Value $lines.Count
        }
        Log ("Export merged $added action row(s) into $csv")
    }
}