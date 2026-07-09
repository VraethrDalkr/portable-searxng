@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "BASE=%~dp0"

echo ==============================================
echo   PortableSearXNG installer
echo   Fetches Python + SearXNG into this folder
echo ==============================================

rem --- pins ---
set "PYVER=3.13.14"
set "PYZIP_URL=https://www.python.org/ftp/python/3.13.14/python-3.13.14-embed-amd64.zip"
set "PYZIP_SHA256=90B4E5B9898B72D744650524BFF92377C367F44BD5FBD09E3148656C080AD907"
set "PIPWHL_URL=https://files.pythonhosted.org/packages/5d/95/6b5cb3461ea5673ba0995989746db58eb18b91b54dbf331e72f569540946/pip-26.1.2-py3-none-any.whl"
set "PIPWHL_SHA256=382ff9f685ee3bc25864f820aa50505825f10f5458ffff07e30a6d96e5715cab"
rem pip refuses wheels whose filename is not {name}-{version}-...-.whl - keep the real name
set "PIPWHL_NAME=pip-26.1.2-py3-none-any.whl"

rem --- warn (not abort) about very long install paths (possible MAX_PATH issues) ---
call :strlen BASE PATHLEN
if %PATHLEN% gtr 120 goto path_warn
goto path_ok
:path_warn
echo [WARNING] This folder's path is %PATHLEN% characters long:
echo    %BASE%
echo Very long paths can hit Windows MAX_PATH limits during install or later
echo updates. If you hit odd file errors, try a shorter path instead
echo ^(e.g. C:\PortableSearXNG^).
:path_ok

rem --- required tools: curl.exe and tar.exe must exist (Windows 10 1803+) ---
set "CURL=%SystemRoot%\System32\curl.exe"
set "TAR=%SystemRoot%\System32\tar.exe"
if not exist "%CURL%" set "STAGE=tool check - requires Windows 10 1803+ with curl.exe/tar.exe (curl.exe missing)" & goto fail
if not exist "%TAR%" set "STAGE=tool check - requires Windows 10 1803+ with curl.exe/tar.exe (tar.exe missing)" & goto fail

echo.
echo [1/4] Portable Python...

rem --- gate: python already extracted with our ._pth already in place? ---
if not exist "%BASE%python\python.exe" goto need_python
findstr /c:"..\searxng" "%BASE%python\python313._pth" >nul 2>&1
if errorlevel 1 goto need_python
echo    already present - skipping.
goto have_python

:need_python
echo    downloading Python %PYVER% embeddable package...
if not exist "%BASE%dl" mkdir "%BASE%dl"
if not exist "%BASE%python" mkdir "%BASE%python"

"%CURL%" -fsSL --connect-timeout 30 --retry 3 --retry-delay 2 -o "%BASE%dl\python-embed.zip" "%PYZIP_URL%"
if errorlevel 1 set "STAGE=Python download" & goto fail

echo    verifying checksum...
certutil -hashfile "%BASE%dl\python-embed.zip" SHA256 | findstr /i "%PYZIP_SHA256%" >nul
if errorlevel 1 goto python_checksum_fail
goto python_checksum_ok

:python_checksum_fail
del /f /q "%BASE%dl\python-embed.zip" >nul 2>&1
set "STAGE=Python checksum verification (downloaded file did not match the expected SHA256 - possible corrupt/incomplete download or tampering)"
goto fail

:python_checksum_ok
echo    extracting...
"%TAR%" -xf "%BASE%dl\python-embed.zip" -C "%BASE%python"
if errorlevel 1 set "STAGE=Python extraction" & goto fail

echo    configuring python313._pth...
>"%BASE%python\python313._pth" echo python313.zip
>>"%BASE%python\python313._pth" echo .
>>"%BASE%python\python313._pth" echo Lib\site-packages
>>"%BASE%python\python313._pth" echo ..\searxng
>>"%BASE%python\python313._pth" echo import site

:have_python

echo.
echo [2/4] pip...

"%BASE%python\python.exe" -m pip --version >nul 2>&1
if not errorlevel 1 goto have_pip

echo    downloading pip installer wheel...
if not exist "%BASE%dl" mkdir "%BASE%dl"
"%CURL%" -fsSL --connect-timeout 30 --retry 3 --retry-delay 2 -o "%BASE%dl\%PIPWHL_NAME%" "%PIPWHL_URL%"
if errorlevel 1 set "STAGE=pip download" & goto fail

echo    verifying checksum...
certutil -hashfile "%BASE%dl\%PIPWHL_NAME%" SHA256 | findstr /i "%PIPWHL_SHA256%" >nul
if errorlevel 1 goto pip_checksum_fail
goto pip_checksum_ok

:pip_checksum_fail
del /f /q "%BASE%dl\%PIPWHL_NAME%" >nul 2>&1
set "STAGE=pip checksum verification (downloaded file did not match the expected SHA256 - possible corrupt/incomplete download or tampering)"
goto fail

:pip_checksum_ok
echo    installing pip...
rem the wheel path goes in via sys.argv, never interpolated into the Python
rem source: a quote character in the folder path must not break the code
"%BASE%python\python.exe" -c "import sys; w=sys.argv.pop(1); sys.path.insert(0, w); import runpy; sys.argv[1:]=['install', '--no-warn-script-location', w]; runpy.run_module('pip', run_name='__main__')" "%BASE%dl\%PIPWHL_NAME%"
if errorlevel 1 set "STAGE=pip install" & goto fail

"%BASE%python\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 set "STAGE=pip install (pip still not usable after installing it)" & goto fail

:have_pip

echo.
echo [3/4] Windows compatibility shims...
if not exist "%BASE%python\Lib\site-packages" mkdir "%BASE%python\Lib\site-packages"
copy /y "%BASE%shims\pwd.py" "%BASE%python\Lib\site-packages\" >nul
if errorlevel 1 set "STAGE=shims copy (pwd.py)" & goto fail
copy /y "%BASE%shims\sitecustomize.py" "%BASE%python\Lib\site-packages\" >nul
if errorlevel 1 set "STAGE=shims copy (sitecustomize.py)" & goto fail

rem --- snapshot the shipped defaults as *.dist; update.py compares these
rem --- copies against future kit releases to detect changed defaults.
rem --- (Before v0.1.7 start.bat's first run wrote a secret into
rem --- settings.yml, which made this pre-first-run ordering essential;
rem --- the secret lives in data\secret_key now, but snapshotting early
rem --- stays correct either way.)
if not exist "%BASE%settings.yml.dist" copy /y "%BASE%settings.yml" "%BASE%settings.yml.dist" >nul
if not exist "%BASE%limiter.toml.dist" copy /y "%BASE%limiter.toml" "%BASE%limiter.toml.dist" >nul

echo.
echo [4/4] SearXNG (downloads source + Python dependencies)...
"%BASE%python\python.exe" "%BASE%update.py" --install
if errorlevel 1 set "STAGE=SearXNG install (update.py --install)" & goto fail

echo.
echo Cleaning up temporary files...
if exist "%BASE%dl" rmdir /s /q "%BASE%dl"

echo.
echo ==============================================
echo   Install complete - starting PortableSearXNG
echo ==============================================
call "%BASE%start.bat"
exit /b 0

:fail
echo.
echo ==============================================
echo   INSTALL FAILED
echo ==============================================
echo Stage that failed: %STAGE%
echo.
echo Fix the issue ^(usually network^) and re-run install.bat - it resumes
echo where it left off.
pause
exit /b 1

rem --- crude string-length helper: strlen VARNAME OUTVARNAME ---
:strlen
setlocal EnableDelayedExpansion
set "s=!%~1!"
set "len=0"
:strlen_loop
if defined s (
    set "s=!s:~1!"
    set /a "len+=1"
    goto strlen_loop
)
endlocal & set "%~2=%len%"
goto :eof
