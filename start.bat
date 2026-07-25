@echo off
:: TenoHMS Server Starter
:: This file is used by Task Scheduler for auto-start and can also be run manually.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Activate virtualenv
if exist "%PROJECT_DIR%venv\Scripts\activate.bat" (
    call "%PROJECT_DIR%venv\Scripts\activate.bat"
) else (
    echo ERROR: Virtual environment not found at %PROJECT_DIR%venv
    echo Run setup.bat first.
    pause
    exit /b 1
)

:: Run migrations silently
python manage.py migrate --run-syncdb --verbosity 0 2>nul

:: Find available port (8000-8010)
set PORT=8000
for /l %%p in (8000,1,8010) do (
    netstat -an | findstr ":%%p " | findstr "LISTENING" >nul 2>&1
    if errorlevel 1 (
        set PORT=%%p
        goto :found_port
    )
)
:found_port

echo %PORT% > "%PROJECT_DIR%.current_port"

echo TenoHMS starting on port %PORT%...
python manage.py runserver 127.0.0.1:%PORT%
