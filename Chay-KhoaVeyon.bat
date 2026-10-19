@echo off
setlocal
cd /d "%~dp0"
set "RT=%~dp0runtime"

REM 1) Python portable da nam trong thu muc runtime (tu tai o lan chay dau)
if exist "%RT%\tools\pythonw.exe" goto :portable

REM 2) May da co Python: dung luon, tu cai openpyxl neu thieu
where python >nul 2>&1
if errorlevel 1 goto :download
python -c "import openpyxl" >nul 2>&1
if errorlevel 1 python -m pip install --user openpyxl
python -c "import openpyxl" >nul 2>&1
if errorlevel 1 goto :download
where pythonw >nul 2>&1
if errorlevel 1 goto :download
start "" pythonw KhoaVeyon.py %*
exit /b 0

:download
echo Lan chay dau tien: dang tai Python portable (khoang 30 MB), can ket noi Internet...
echo Khong cai gi vao Windows, moi thu nam trong thu muc "runtime" ben canh chuong trinh.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest 'https://www.nuget.org/api/v2/package/python/3.11.9' -OutFile 'python-portable.zip'; Expand-Archive -Path 'python-portable.zip' -DestinationPath 'runtime' -Force; Remove-Item 'python-portable.zip'"
if not exist "%RT%\tools\python.exe" (
  echo Tai Python that bai. Kiem tra Internet hoac cai Python tai https://www.python.org/downloads/ ^(tick Add Python to PATH^).
  pause
  exit /b 1
)
"%RT%\tools\python.exe" -m ensurepip --upgrade >nul 2>&1
"%RT%\tools\python.exe" -m pip install openpyxl
"%RT%\tools\python.exe" -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
  echo Khong cai duoc openpyxl. Hay cai Python tai https://www.python.org/downloads/ roi chay lai.
  pause
  exit /b 1
)

:portable
start "" "%RT%\tools\pythonw.exe" KhoaVeyon.py %*
exit /b 0
