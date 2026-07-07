@echo off
rem FROZEN: this file is deliberately never replaced by a scripts update.
rem cmd re-reads a running .bat by byte offset, so rewriting it mid-run
rem corrupts execution. All real logic lives in update.py - change that.
setlocal EnableExtensions
cd /d "%~dp0"

set "BASE=%~dp0"
set "PY=%BASE%python\python.exe"

echo ==============================================
echo   PortableSearXNG - updater
echo ==============================================

rem goto-style on purpose: echoing %PY% inside a ( ) block breaks cmd's parser
rem when the install path contains parentheses, e.g. "...\My Tools (1)\"
if exist "%PY%" goto have_python
echo [ERROR] Portable Python not found at:
echo    %PY%
echo Run install.bat first.
pause
exit /b 1

:have_python
"%PY%" "%BASE%update.py" %*
set "RC=%errorlevel%"
pause
exit /b %RC%
