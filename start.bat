@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BASE=%~dp0"
set "PY=%BASE%python\python.exe"
set "PYW=%BASE%python\pythonw.exe"

echo ==============================================
echo   PortableSearXNG - privacy-first metasearch
echo ==============================================

if not exist "%BASE%searxng\" goto not_installed
if not exist "%PY%" goto not_installed
if not exist "%PYW%" goto not_installed
goto have_python

:not_installed
echo [ERROR] Not installed yet - run install.bat first.
pause
exit /b 1

:have_python

rem --- read port from config.ini via getcfg.py (default 8080 on any error) ---
set "PORT=8080"
"%PY%" "%BASE%getcfg.py" port > "%TEMP%\psx_port.tmp" 2>nul
if not errorlevel 1 set /p PORT=<"%TEMP%\psx_port.tmp"
del "%TEMP%\psx_port.tmp" >nul 2>&1

rem --- optional browser override from config.ini (empty = Windows default) ---
set "BROWSER="
"%PY%" "%BASE%getcfg.py" browser > "%TEMP%\psx_browser.tmp" 2>nul
if not errorlevel 1 set /p BROWSER=<"%TEMP%\psx_browser.tmp"
del "%TEMP%\psx_browser.tmp" >nul 2>&1

rem --- open a browser at all? (config.ini open_browser, normalized true/false) ---
set "OPENBROWSER=true"
"%PY%" "%BASE%getcfg.py" open_browser > "%TEMP%\psx_openbrowser.tmp" 2>nul
if not errorlevel 1 set /p OPENBROWSER=<"%TEMP%\psx_openbrowser.tmp"
del "%TEMP%\psx_openbrowser.tmp" >nul 2>&1

rem --- first run: replace the __SECRET__ placeholder with a real secret_key ---
findstr /c:"__SECRET__" "%BASE%settings.yml" >nul 2>&1
if errorlevel 1 goto have_secret
echo Generating a fresh secret_key ^(first run^)...
"%PY%" -c "import secrets;p=r'%BASE%settings.yml';d=open(p,'rb').read().replace(b'__SECRET__',secrets.token_hex(32).encode());open(p,'wb').write(d)"
:have_secret

rem --- refuse to double-start on the same port ---
netstat -ano -p tcp | findstr /c:":%PORT% " | findstr /c:"LISTENING" >nul 2>&1
if errorlevel 1 goto not_running
echo A server is already listening on port %PORT%.
echo If it is PortableSearXNG, you are already running.
echo For a second instance, copy the folder and set a different "port" in
echo its config.ini.
call :open_browser
ping -n 6 127.0.0.1 >nul
exit /b 0

:not_running
set "SEARXNG_SETTINGS_PATH=%BASE%settings.yml"
set "SEARXNG_PORT=%PORT%"
set "SEARXNG_BIND_ADDRESS=127.0.0.1"
set "SEARXNG_BASE_URL=http://127.0.0.1:%PORT%/"

if not exist "%BASE%data\logs" mkdir "%BASE%data\logs"

rem --- keep the log from growing forever: roll it over past ~5 MB ---
if not exist "%BASE%data\logs\searxng.log" goto no_rollover
for %%F in ("%BASE%data\logs\searxng.log") do set "LOGSIZE=%%~zF"
if %LOGSIZE% gtr 5242880 move /y "%BASE%data\logs\searxng.log" "%BASE%data\logs\searxng.old.log" >nul
:no_rollover

echo Starting PortableSearXNG in the background...
echo    URL:  http://127.0.0.1:%PORT%/
echo    Log:  data\logs\searxng.log

rem pythonw.exe = no console window; sitecustomize.py routes its output to the log
start "" "%PYW%" -m searx.webapp

rem --- wait until the server answers, then open the browser ---
set "UP="
for /L %%i in (1,1,90) do (
    if not defined UP (
        "%SystemRoot%\System32\curl.exe" -s -o NUL -m 1 "http://127.0.0.1:%PORT%/" && set "UP=1"
        if not defined UP ping -n 2 127.0.0.1 >nul
    )
)

if defined UP goto server_up

echo.
echo [ERROR] The server did not answer within 90 seconds.
echo Last log lines ^(data\logs\searxng.log^):
echo ----------------------------------------------
"%PY%" -c "print(''.join(open(r'%BASE%data\logs\searxng.log',encoding='utf-8',errors='replace').readlines()[-15:]))" 2>nul
echo ----------------------------------------------
echo You can still try opening it manually:
echo    http://127.0.0.1:%PORT%/
pause
exit /b 1

:server_up
echo Server is up. This window closes by itself.
echo Stop the server anytime with stop.bat
echo    URL: http://127.0.0.1:%PORT%/
call :open_browser
ping -n 6 127.0.0.1 >nul
exit /b 0

rem --- open http://127.0.0.1:%PORT%/ in the configured browser, or the ---
rem --- Windows default one when config.ini has no (valid) "browser" set; ---
rem --- skipped entirely when open_browser = false (startup-apps use case) ---
:open_browser
if /i "%OPENBROWSER%"=="false" goto open_skip
if not defined BROWSER goto open_default
if exist "%BROWSER%" goto open_custom
echo [WARNING] The browser set in config.ini was not found:
echo    %BROWSER%
echo Opening the Windows default browser instead.
goto open_default
:open_custom
echo Opening the browser...
start "" "%BROWSER%" "http://127.0.0.1:%PORT%/"
goto :eof
:open_default
echo Opening the browser...
start "" "http://127.0.0.1:%PORT%/"
goto :eof
:open_skip
echo Not opening a browser ^(open_browser = false in config.ini^).
goto :eof
