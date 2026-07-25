@echo off
echo ============================================
echo   TenoHMS - Auto-Start Setup
echo ============================================
echo.

:: Get the directory where this script is running
set "INSTALL_DIR=%~dp0"
set "EXE_PATH=%INSTALL_DIR%TenoHMS.exe"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Check if exe exists
if not exist "%EXE_PATH%" (
    echo ERROR: TenoHMS.exe not found in %INSTALL_DIR%
    echo Please run this script from the TenoHMS folder.
    pause
    exit /b 1
)

echo [1/3] Creating VBS launcher script...

:: Create a VBS script that runs the exe silently (no console window)
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%INSTALL_DIR%"
echo WshShell.Run "cmd /c cd /d ""%INSTALL_DIR%"" && TenoHMS.exe", 0, False
) > "%INSTALL_DIR%start_tenohms.vbs"

echo [2/3] Copying to Windows Startup folder...

:: Create a shortcut in the Startup folder
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set shortcut = WshShell.CreateShortcut^("%STARTUP_FOLDER%\TenoHMS.lnk"^)
echo shortcut.TargetPath = "%INSTALL_DIR%start_tenohms.vbs"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%"
echo shortcut.Description = "TenoHMS Hospital Management System"
echo shortcut.Save
) > "%TEMP%\create_shortcut.vbs"

cscript //nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"

echo [3/3] Creating desktop shortcut...

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo Set shortcut = WshShell.CreateShortcut^("%USERPROFILE%\Desktop\TenoHMS.lnk"^)
echo shortcut.TargetPath = "%EXE_PATH%"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%"
echo shortcut.Description = "TenoHMS Hospital Management System"
echo shortcut.Save
) > "%TEMP%\create_desktop_shortcut.vbs"

cscript //nologo "%TEMP%\create_desktop_shortcut.vbs"
del "%TEMP%\create_desktop_shortcut.vbs"

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo   - TenoHMS will start automatically on boot
echo   - Desktop shortcut created
echo   - To REMOVE auto-start, delete this file:
echo     %STARTUP_FOLDER%\TenoHMS.lnk
echo.
echo   To start now, double-click TenoHMS.exe
echo ============================================
pause
