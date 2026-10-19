@echo off
REM KhoaVeyon: khoa / mo khoa thu muc chua file nay (C:\cmd). Chay bang SYSTEM hoac quan tri.
REM Dung SID nen dung cho moi ngon ngu Windows: S-1-5-18 SYSTEM, S-1-5-32-544 Administrators, S-1-5-32-545 Users
set "D=%~dp0"
if "%D:~-1%"=="\" set "D=%D:~0,-1%"
if /i "%~1"=="unlock" goto UNLOCK
if not exist "%D%\log" mkdir "%D%\log"
icacls "%D%" /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "*S-1-5-32-545:(OI)(CI)RX" /T /C >nul
if errorlevel 1 exit /b 1
REM Thu muc log: hoc sinh van ghi duoc de nhat ky hoat dong chay tiep
icacls "%D%\log" /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" "*S-1-5-32-545:(OI)(CI)M" /T /C >nul
exit /b %errorlevel%
:UNLOCK
icacls "%D%" /reset /T /C >nul
exit /b %errorlevel%
