@echo off
echo ============================================
echo   TenoHMS - Building Desktop Executable
echo ============================================

echo.
echo [1/4] Activating virtual environment...
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
)

echo.
echo [2/4] Installing build dependencies...
pip install --no-cache-dir pyinstaller
pip install --no-cache-dir -r requirements.txt

echo.
echo [3/4] Running collectstatic...
python manage.py collectstatic --noinput

echo.
echo [4/4] Building executable...
pyinstaller TenoHMS.spec --clean --noconfirm

echo.
echo ============================================
echo   BUILD COMPLETE!
echo   Output: dist\TenoHMS\TenoHMS.exe
echo ============================================
echo.
echo   To run: dist\TenoHMS\TenoHMS.exe
echo.
pause
