@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BASE=%~dp0"
set "PY=%BASE%python\python.exe"

rem --- read port from config.ini via getcfg.py (default 8080 on any error) ---
set "PORT=8080"
"%PY%" "%BASE%getcfg.py" port > "%TEMP%\psx_port.tmp" 2>nul
if not errorlevel 1 set /p PORT=<"%TEMP%\psx_port.tmp"
del "%TEMP%\psx_port.tmp" >nul 2>&1

set "PID="
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr /c:":%PORT% " ^| findstr /c:"LISTENING"') do set "PID=%%a"

if not defined PID (
    echo PortableSearXNG is not running on port %PORT% - nothing to stop.
    pause
    exit /b 0
)

rem --- only kill it if it is actually a python process (ours) ---
tasklist /fi "PID eq %PID%" | findstr /i "python" >nul
if errorlevel 1 (
    echo The process listening on port %PORT% - PID %PID% - is not python.exe,
    echo so it is probably not PortableSearXNG. It will NOT be stopped.
    pause
    exit /b 1
)

taskkill /PID %PID% /F >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Could not stop PID %PID%. Try running stop.bat again.
    pause
    exit /b 1
)

echo PortableSearXNG stopped - PID %PID% released port %PORT%.
pause
exit /b 0
