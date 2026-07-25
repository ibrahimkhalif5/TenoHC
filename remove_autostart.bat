@echo off
echo ============================================
echo   TenoHMS - Remove Auto-Start
echo ============================================
echo.

schtasks /delete /tn "TenoHMS" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo Auto-start removed successfully.
) else (
    echo Auto-start task not found - nothing to remove.
)

:: Also remove old startup folder shortcut if present
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_FOLDER%\TenoHMS.lnk" (
    del "%STARTUP_FOLDER%\TenoHMS.lnk"
    echo Old startup shortcut removed.
)

echo.
echo Auto-start has been removed.
echo TenoHMS will no longer start automatically on login.
echo.
pause
