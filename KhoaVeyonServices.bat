@echo off
setlocal
REM ============================================================
REM  KhoaVeyonService.bat  -  for Veyon clients (keep in C:\cmd)
REM
REM  -install      one-time setup per PC (needs admin password once)
REM  -uninstall    remove services, rules and app blocks
REM  -killapp      force close all open apps
REM  -blockall     block all internet (LAN stays on)
REM  -allowpage    block internet EXCEPT sites listed in AllowPage.xlsx
REM  -allowall     allow all internet again
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
REM  -clearhistory       close Chrome/Firefox and clear their browsing history
REM                      (Firefox: this also clears bookmarks, see README)
REM ============================================================

REM ===== SETTINGS =====
REM Folder that holds AllowPage.xlsx and BlockAppList.xlsx (keep the last backslash)
set "LISTDIR=C:\cmd\"
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
if not defined MODE goto HELP

REM These run in the kid's own session, so they need no admin rights and no service
for %%U in (killapp keepapp lockdown unlock mute unmute activitylog-start activitylog-stop exportlog lockapp-start lockapp-stop clearhistory) do if /i "%MODE%"=="%%U" goto RUNPS

REM Already admin / SYSTEM (for example when started by the service)? Do the work now.
fltmc >nul 2>&1
if errorlevel 1 goto VIAUSER

:RUNPS
set "KV_MODE=%MODE%"
set "KV_DIR=%~dp0"
set "KV_LIST=%LISTDIR%"
set "KV_SELF=%SELF%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:KV_SELF); iex $t.Substring($t.IndexOf('#PS1'+'START'))"
exit /b 0

:VIAUSER
REM Normal (kid) account: ask the SYSTEM service to do the work
sc start KhoaVeyonService_%MODE% >nul 2>&1
if %errorlevel%==1060 echo Service not installed. Run KhoaVeyonService.bat -install as admin.
exit /b 0

:INSTALL
fltmc >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process '%SELF%' -ArgumentList '-install' -Verb RunAs"
  exit /b
)
for %%M in (blockall allowpage allowall blockapp unblockapp) do (
  sc stop KhoaVeyonService_%%M >nul 2>&1
  sc delete KhoaVeyonService_%%M >nul 2>&1
  sc create KhoaVeyonService_%%M binPath= "cmd.exe /c %SELF% -%%M" start= demand >nul
  sc sdset KhoaVeyonService_%%M "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;LCRPRC;;;IU)" >nul
)
REM NOTE: C:\cmd is left editable by normal users (no icacls lock).
REM The SYSTEM services below execute these .bat files as SYSTEM, so anyone who can
REM edit this folder can run arbitrary code as SYSTEM. See the README security note.
if not exist "C:\cmd\log" mkdir "C:\cmd\log" >nul 2>&1

REM Auto-start activity logging whenever any student logs on (registered once, fires for every logon)
powershell -NoProfile -Command ^
 "$a = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c \"%SELF%\" -activitylog-start';" ^
 "$t = New-ScheduledTaskTrigger -AtLogOn;" ^
 "$p = New-ScheduledTaskPrincipal -GroupId 'BUILTIN\Users' -RunLevel Limited;" ^
 "$s = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;" ^
 "Register-ScheduledTask -TaskName 'KhoaVeyonAutoLog' -Action $a -Trigger $t -Principal $p -Settings $s -Force | Out-Null"

call :LOGEVENT install "Setup completed"
echo.
echo Install done. Services KhoaVeyonService_* created.
echo Activity logging will start automatically at every logon.
echo Log folder: C:\cmd\log
pause
exit /b 0

:UNINSTALL
fltmc >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process '%SELF%' -ArgumentList '-uninstall' -Verb RunAs"
  exit /b
)
call "%SELF%" -allowall
call "%SELF%" -unblockapp
call "%SELF%" -activitylog-stop
call "%SELF%" -lockapp-stop
for %%M in (blockall allowpage allowall blockapp unblockapp) do (
  sc stop KhoaVeyonService_%%M >nul 2>&1
  sc delete KhoaVeyonService_%%M >nul 2>&1
)
schtasks /delete /tn "KhoaVeyonAutoLog" /f >nul 2>&1
call :LOGEVENT uninstall "Removed services, rules and scheduled tasks"
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
echo Usage: KhoaVeyonService.bat [-install ^| -uninstall ^| -killapp ^| -blockall ^| -allowpage ^| -allowall ^| -blockapp ^| -unblockapp ^| -keepapp ^| -lockdown ^| -unlock ^| -mute ^| -unmute ^| -activitylog-start ^| -activitylog-stop ^| -exportlog ^| -lockapp-start ^| -lockapp-stop ^| -clearhistory]
exit /b 0

#PS1START
$ErrorActionPreference = 'Continue'
$mode = $env:KV_MODE
$dir  = $env:KV_DIR
$list = $env:KV_LIST
$log  = Join-Path $dir 'KhoaVeyonService.log'
if (@('killapp','keepapp','lockdown','unlock','mute','unmute','activitylog-start','activitylog-stop','exportlog','lockapp-start','lockapp-stop','clearhistory') -contains $mode) { $log = Join-Path $env:TEMP 'KhoaVeyonService.log' }
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

    'allowall' {
        Remove-Rules
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
            $psCmd = @"
`$stop  = '$lockStopFlag'
`$log   = '$log'
`$mode  = 'lockapp-start'
`$keepNames = @($namesLit)
`$keepPaths = @($pathsLit)
`$protect = @('explorer','cmd','conhost','powershell','pwsh','veyon-server','veyon-worker','veyon-service','veyon-master',
             'applicationframehost','shellexperiencehost','startmenuexperiencehost','searchhost','textinputhost',
             'systemsettings','sihost','ctfmon','dwm')
function Log(`$m) { try { Add-Content -Path `$log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  [lockapp]  ' + `$m) } catch {} }
`$session = (Get-Process -Id `$PID).SessionId
while (-not (Test-Path `$stop)) {
    try {
        foreach (`$p in @(Get-Process -ErrorAction SilentlyContinue)) {
            if (`$p.SessionId -ne `$session -or `$p.MainWindowHandle -eq 0) { continue }
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