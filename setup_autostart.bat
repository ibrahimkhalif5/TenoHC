@echo off
echo ============================================
echo   TenoHMS - Client Setup
echo ============================================
echo.

set "INSTALL_DIR=%~dp0"
set "TASK_NAME=TenoHMS"

:: ── Check Python is installed ─────────────────────────────
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo   Found Python %PY_VER%

:: ── Create virtual environment ────────────────────────────
echo [2/6] Setting up virtual environment...
if not exist "%INSTALL_DIR%venv" (
    python -m venv "%INSTALL_DIR%venv"
    echo   Created venv.
) else (
    echo   venv already exists.
)

:: Activate and install packages
call "%INSTALL_DIR%venv\Scripts\activate.bat"

echo [3/6] Installing packages...
pip install --upgrade pip --quiet
pip install -r "%INSTALL_DIR%requirements.txt" --quiet
echo   Packages installed.

:: ── Set environment ──────────────────────────────────────
set "DJANGO_SETTINGS_MODULE=tenohms.settings.desktop"

:: ── Run migrations ───────────────────────────────────────
echo [4/6] Setting up database...
cd /d "%INSTALL_DIR%"
python manage.py migrate --run-syncdb --verbosity 0
echo   Database ready.

:: ── Create default admin ─────────────────────────────────
echo [5/6] Creating default admin account...
python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','tenohms.settings.desktop'); django.setup(); from django.contrib.auth import get_user_model; User=get_user_model(); u=User.objects.filter(username='hassan'); print('  Admin already exists.' if u.exists() else (User.objects.create_superuser('hassan','hassan@tenohms.local','admin123',first_name='Hassan',last_name='Adan') and setattr(User.objects.get(username='hassan'),'role','ADMIN') or User.objects.get(username='hassan').save() or print('  Default admin created: hassan / admin123')))"

:: ── Seed data ────────────────────────────────────────────
echo [6/6] Seeding data...
python manage.py seed_wards --verbosity 0 2>nul
python manage.py seed_lab_tests --verbosity 0 2>nul
python manage.py seed_medicines --verbosity 0 2>nul
python manage.py seed_radiology_services --verbosity 0 2>nul
python manage.py seed_lab_templates --verbosity 0 2>nul
python manage.py seed_item_master --verbosity 0 2>nul
echo   Data seeded.

:: ── Register auto-start task ─────────────────────────────
echo.
echo Registering auto-start with Windows Task Scheduler...

:: Remove old task if exists
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Create task: runs at logon, runs whether user is logged in or not
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "wscript.exe ""%INSTALL_DIR%start_silent.vbs""" ^
    /sc onlogon ^
    /rl highest ^
    /f

if %errorlevel% equ 0 (
    echo   Auto-start registered successfully.
) else (
    echo   Could not register auto-start. You may need to run this script as Administrator.
    echo   You can also start TenoHMS manually by double-clicking start.bat
)

:: ── Create desktop shortcut ──────────────────────────────
echo.
echo Creating desktop shortcut...
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set shortcut = WshShell.CreateShortcut^("%USERPROFILE%\Desktop\TenoHMS.lnk"^)
echo shortcut.TargetPath = "%INSTALL_DIR%start.bat"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%"
echo shortcut.Description = "TenoHMS Hospital Management System"
echo shortcut.Save
) > "%TEMP%\create_shortcut.vbs"

cscript //nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"
echo   Desktop shortcut created.

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo   TenoHMS will start automatically when you log in.
echo   To start NOW, double-click  start.bat  or the desktop shortcut.
echo.
echo   Login:   hassan / admin123
echo   Address: http://127.0.0.1:8000
echo.
echo   To REMOVE auto-start, run: remove_autostart.bat
echo ============================================
pause
