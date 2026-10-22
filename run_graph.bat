@echo off
setlocal

if "%~1"=="" (
    echo Usage: run_graph.bat ^<markdown-directory^> [--output ^<html-file^>]
    echo Example: run_graph.bat demo_notes --output index.html
    exit /b 2
)

if exist "%~dp0.runtime\python\python.exe" (
    "%~dp0.runtime\python\python.exe" "%~dp0main.py" %*
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python is not installed. Run setup_and_run.ps1 first.
        exit /b 1
    )
    python "%~dp0main.py" %*
)
exit /b %errorlevel%
