@echo off
echo ============================================
echo   TenoHMS - Remove Auto-Start
echo ============================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if exist "%STARTUP_FOLDER%\TenoHMS.lnk" (
    del "%STARTUP_FOLDER%\TenoHMS.lnk"
    echo Auto-start removed successfully.
) else (
    echo Auto-start shortcut not found - nothing to remove.
)

echo.
pause
