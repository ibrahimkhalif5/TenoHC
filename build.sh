#!/bin/bash
echo "============================================"
echo "  TenoHMS - Building Desktop Application"
echo "============================================"

echo ""
echo "[1/4] Setting up environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo ""
echo "[2/4] Installing build dependencies..."
pip install --no-cache-dir pyinstaller
pip install --no-cache-dir -r requirements.txt

echo ""
echo "[3/4] Running collectstatic..."
python manage.py collectstatic --noinput

echo ""
echo "[4/4] Building executable..."
pyinstaller TenoHMS.spec --clean --noconfirm

echo ""
echo "============================================"
echo "  BUILD COMPLETE!"
echo "  Output: dist/TenoHMS/"
echo "============================================"
echo ""
echo "  To run: ./dist/TenoHMS/TenoHMS"
echo ""
