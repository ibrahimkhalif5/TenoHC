@echo off
echo Stopping TenoHMS server...
taskkill /f /im python.exe /fi "WINDOWTITLE eq *manage.py*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *TenoHMS*" >nul 2>&1
echo TenoHMS stopped.
pause
