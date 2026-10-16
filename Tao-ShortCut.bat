@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\KhoaVeyon.lnk'); $s.TargetPath='%~dp0Chay-KhoaVeyon.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0web\assets\icon.ico'; $s.WindowStyle=7; $s.Save()"
echo Da tao shortcut KhoaVeyon tren Desktop.
pause
