@echo off
setlocal

if exist "%~dp0.runtime\python\python.exe" (
    if "%~1"=="" (
        "%~dp0.runtime\python\python.exe" "%~dp0main.py" build "%CD%"
    ) else (
        "%~dp0.runtime\python\python.exe" "%~dp0main.py" build %*
    )
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python is not installed. Run setup_and_run.ps1 first.
        exit /b 1
    )
    if "%~1"=="" (
        python "%~dp0main.py" build "%CD%"
    ) else (
        python "%~dp0main.py" build %*
    )
)
exit /b %errorlevel%
