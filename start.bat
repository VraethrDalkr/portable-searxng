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
rem temp files live in this folder, not %TEMP%: keeps "nothing outside this
rem folder" honest and stops two instances racing on a shared filename
set "PORT=8080"
"%PY%" "%BASE%getcfg.py" port > "%BASE%psx_port.tmp" 2>nul
if not errorlevel 1 set /p PORT=<"%BASE%psx_port.tmp"
del "%BASE%psx_port.tmp" >nul 2>&1

rem --- optional browser override from config.ini (empty = Windows default) ---
set "BROWSER="
"%PY%" "%BASE%getcfg.py" browser > "%BASE%psx_browser.tmp" 2>nul
if not errorlevel 1 set /p BROWSER=<"%BASE%psx_browser.tmp"
del "%BASE%psx_browser.tmp" >nul 2>&1

rem --- open a browser at all? (config.ini open_browser, normalized true/false) ---
set "OPENBROWSER=true"
"%PY%" "%BASE%getcfg.py" open_browser > "%BASE%psx_openbrowser.tmp" 2>nul
if not errorlevel 1 set /p OPENBROWSER=<"%BASE%psx_openbrowser.tmp"
del "%BASE%psx_openbrowser.tmp" >nul 2>&1

rem --- log server output to data\logs\searxng.log? (config.ini logging) ---
rem the actual redirection happens in sitecustomize.py, which reads the same
rem key itself; start.bat only needs it for its messages
set "LOGGING=false"
"%PY%" "%BASE%getcfg.py" logging > "%BASE%psx_logging.tmp" 2>nul
if not errorlevel 1 set /p LOGGING=<"%BASE%psx_logging.tmp"
del "%BASE%psx_logging.tmp" >nul 2>&1

rem --- per-instance secret: lives in data\secret_key and reaches SearXNG ---
rem --- through the SEARXNG_SECRET environment variable, which overrides ---
rem --- settings.yml's secret_key (same mechanism as SEARXNG_PORT below); ---
rem --- settings.yml itself is never modified. An empty file (crashed    ---
rem --- first run) is regenerated. The path goes in via sys.argv, never  ---
rem --- interpolated into the Python source: a quote character in the    ---
rem --- folder path must not be able to break the code.                  ---
set "SECRETSIZE=0"
if exist "%BASE%data\secret_key" for %%F in ("%BASE%data\secret_key") do set "SECRETSIZE=%%~zF"
if %SECRETSIZE% gtr 0 goto have_secret
echo Generating a fresh secret_key ^(first run^)...
"%PY%" -c "import sys,os,secrets;p=sys.argv[1];os.makedirs(os.path.dirname(p),exist_ok=True);open(p,'w',encoding='ascii').write(secrets.token_hex(32))" "%BASE%data\secret_key"
if not errorlevel 1 goto have_secret
echo [ERROR] Could not create data\secret_key.
echo The server cannot start without it. Check that this folder is
echo writable, then run start.bat again.
pause
exit /b 1
:have_secret
set /p SEARXNG_SECRET=<"%BASE%data\secret_key"

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
if /i "%LOGGING%"=="true" goto log_msg_on
echo    Log:  off - set "logging = true" in config.ini to enable
goto log_msg_done
:log_msg_on
echo    Log:  data\logs\searxng.log
:log_msg_done

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
if /i "%LOGGING%"=="true" goto fail_show_log
echo Logging is off, so there are no details to show. Set
echo    logging = true
echo in config.ini and run start.bat again to capture the error in
echo data\logs\searxng.log.
goto fail_log_done
:fail_show_log
echo Last log lines ^(data\logs\searxng.log^):
echo ----------------------------------------------
"%PY%" -c "import sys;print(''.join(open(sys.argv[1],encoding='utf-8',errors='replace').readlines()[-15:]))" "%BASE%data\logs\searxng.log" 2>nul
echo ----------------------------------------------
:fail_log_done
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
