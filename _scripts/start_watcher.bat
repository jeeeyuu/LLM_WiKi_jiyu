@echo off
REM start_watcher.bat — Launch the Python watcher for Cowork dispatch bridge
REM
REM This script assumes:
REM   - Python env named 'llmwiki' (or customize PYTHON path below)
REM   - Current directory is the wiki root
REM
REM Set these environment variables BEFORE running, or edit the defaults:
REM   - PYTHON: absolute path to python.exe in your env
REM   - WIKI_ROOT: path to wiki root (default: current directory)
REM   - ZOTERO_DIR: path to Zotero data directory (default: %%USERPROFILE%%\Zotero)

setlocal enabledelayedexpansion

REM Try to auto-detect Python env
if "%PYTHON%"=="" (
    REM Look for conda-managed env named 'llmwiki'
    for /d %%A in ("%USERPROFILE%\.conda\envs\*") do (
        if "%%~nxA"=="llmwiki" (
            set "PYTHON=%%A\Scripts\python.exe"
            goto found_env
        )
    )
    REM Fallback: use whatever 'python' is in PATH
    set "PYTHON=python"
)

:found_env

if "%WIKI_ROOT%"=="" (
    set "WIKI_ROOT=%CD%"
)

if "%ZOTERO_DIR%"=="" (
    set "ZOTERO_DIR=%USERPROFILE%\Zotero"
)

echo.
echo +----------------------------------------------------+
echo  LLM Wiki Watcher
echo  PYTHON=%PYTHON%
echo  WIKI_ROOT=%WIKI_ROOT%
echo  ZOTERO_DIR=%ZOTERO_DIR%
echo  Ctrl+C to stop
echo +----------------------------------------------------+
echo.

set "SCRIPT=%WIKI_ROOT%\_scripts\watcher.py"

"%PYTHON%" "%SCRIPT%"
