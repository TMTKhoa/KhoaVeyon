@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
REM KhoaVeyon - thiet lap may hoc sinh tron goi. Bam doi 2 lan (tu xin quyen quan tri), chay 1 lan tren moi may.
REM Neu canh file nay co: veyon-*setup*.exe (bo cai Veyon) va *_public.pem (khoa xac thuc) thi tu cai va nhap luon.
net session >nul 2>&1
if errorlevel 1 (
  echo Dang xin quyen quan tri...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs" >nul 2>&1
  if errorlevel 1 (
    echo Khong xin duoc quyen quan tri. Hay chuot phai file nay - Run as administrator.
    pause
  )
  exit /b
)
set "HERE=%~dp0"
set "VCLI=%ProgramFiles%\Veyon\veyon-cli.exe"
set "FAIL="

echo [1/6] Thu muc C:\cmd
if not exist "C:\cmd" mkdir "C:\cmd"

echo [2/6] Mo chia se file va Task Scheduler tu xa
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes >nul 2>&1
netsh advfirewall firewall set rule group="@FirewallAPI.dll,-28502" new enable=Yes >nul 2>&1
netsh advfirewall firewall set rule group="Remote Scheduled Tasks Management" new enable=Yes >nul 2>&1
netsh advfirewall firewall set rule group="@FirewallAPI.dll,-33502" new enable=Yes >nul 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f >nul
netsh advfirewall firewall add rule name="Veyon Server" dir=in action=allow protocol=TCP localport=11100 profile=any >nul 2>&1

echo [3/6] Veyon Service
if exist "%VCLI%" (
  echo     Da co Veyon.
) else (
  set "VSET="
  for %%F in ("%HERE%veyon*setup*.exe") do set "VSET=%%~fF"
  if defined VSET (
    echo     Dang cai Veyon tu !VSET! ...
    "!VSET!" /S /NoMaster
    timeout /t 5 /nobreak >nul
  ) else (
    echo     CHUA CO Veyon va khong thay bo cai veyon*setup*.exe canh file nay.
    set "FAIL=1"
  )
)

echo [4/6] Khoa xac thuc
set "KEYDONE="
for %%F in ("%HERE%*_public.pem") do (
  if exist "%VCLI%" (
    set "KN=%%~nF"
    set "KN=!KN:_public=!"
    "%VCLI%" authkeys import "!KN!/public" "%%~fF" >nul 2>&1 && (echo     Da nhap khoa !KN! & set "KEYDONE=1")
  )
)
if not defined KEYDONE echo     Khong nhap khoa (khong co file *_public.pem hoac chua co Veyon). Neu da nhap tay thi bo qua.

echo [5/6] Bat Veyon Service
sc config VeyonService start= auto >nul 2>&1
sc start VeyonService >nul 2>&1

echo [6/6] Agent va dich vu KhoaVeyon
set "KVAG=%ProgramFiles%\KhoaVeyon"
if exist "%HERE%KhoaVeyonAgent.cfg" (
  if not exist "!KVAG!" mkdir "!KVAG!"
  copy /y "%HERE%KhoaVeyonAgent.cfg" "!KVAG!\agent.cfg" >nul
  icacls "!KVAG!\agent.cfg" /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" >nul 2>&1
  echo     Da cai khoa Agent: may giao vien dieu khien may nay khong can tai khoan quan tri.
  echo "%HERE%" | find /i "\KhoaVeyonSetup\" >nul && del /q "%HERE%KhoaVeyonAgent.cfg" >nul 2>&1
) else (
  echo     Khong thay KhoaVeyonAgent.cfg canh file nay: may giao vien se dung chia se C$ nhu cu.
)
if not exist "C:\cmd\KhoaVeyonServices.bat" if not exist "%HERE%KhoaVeyonServices.bat" if exist "!KVAG!\agent.cfg" (
  echo     Dang tai KhoaVeyonServices.bat tu may giao vien...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=@{};Get-Content -LiteralPath ($env:ProgramFiles+'\KhoaVeyon\agent.cfg') | ForEach-Object { $p=$_.Split('=',2); if($p.Length -eq 2){ $c[$p[0].Trim()]=$p[1].Trim() } }; if(-not $c['url'] -or -not $c['sha']){ exit 3 }; $f='C:\cmd\KhoaVeyonServices.bat'; (New-Object Net.WebClient).DownloadFile($c['url']+'/agent/boot/KhoaVeyonServices.bat',$f); $h=(Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLower(); if($h -ne $c['sha']){ Remove-Item -LiteralPath $f -Force; exit 4 }" >nul 2>&1
  if errorlevel 1 echo     KHONG tai duoc KhoaVeyonServices.bat: kiem tra may giao vien dang chay KhoaVeyon, tuong lua cho phep cong Agent, hoac chep file nay vao C:\cmd bang tay.
)
if exist "%HERE%KhoaVeyonServices.bat" (
  copy /y "%HERE%KhoaVeyonServices.bat" "C:\cmd\" >nul
)
if exist "C:\cmd\KhoaVeyonServices.bat" (
  call "C:\cmd\KhoaVeyonServices.bat" -install <nul
) else (
  echo     Chua co KhoaVeyonServices.bat tren may nay: bo qua, may giao vien se gui sau.
)

echo.
if defined FAIL (
  echo CON THIEU: Veyon chua duoc cai. Chep bo cai Veyon vao cung thu muc voi file nay roi chay lai.
) else (
  echo Xong. May hoc sinh san sang nhan file va lenh tu KhoaVeyon.
)
pause
