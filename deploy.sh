#!/bin/bash
# ============================================================
# TenoHMS — PythonAnywhere Deploy Script
# Run this in the PythonAnywhere Bash console
# ============================================================
set -e

echo "============================================"
echo "  TenoHMS PythonAnywhere Deployment"
echo "============================================"

# --- Configuration (edit these if needed) ---
REPO_URL="https://github.com/ibrahimkhalif5/TenoHC.git"
PROJECT_DIR="TenoHMS"
PA_USER=$(whoami)

echo ""
echo "[1/7] Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "  Directory already exists, pulling latest..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo ""
echo "[2/7] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo ""
echo "[3/7] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[4/7] Setting up .env file..."
if [ ! -f ".env" ]; then
    SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

    cat > .env << EOF
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${PA_USER}.pythonanywhere.com
DJANGO_SETTINGS_MODULE=tenohms.settings.pythonanywhere

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=THHIMS <noreply@tenohms.com>

# Security
CSRF_TRUSTED_ORIGINS=https://${PA_USER}.pythonanywhere.com
EOF
    echo "  .env file created!"
else
    echo "  .env file already exists, skipping."
fi

echo ""
echo "[5/7] Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "[6/7] Running migrations..."
python manage.py migrate

echo ""
echo "[7/7] Creating superuser..."
echo "  You will be prompted to create an admin account:"
python manage.py createsuperuser

echo ""
echo "============================================"
echo "  NEXT STEPS (on the Web tab):"
echo "============================================"
echo ""
echo "  1. Web tab → Add new web app"
echo "     - Manual configuration → Python 3.10"
echo ""
echo "  2. Click WSGI config file → replace with:"
echo ""
echo "     import os"
echo "     import sys"
echo ""
echo "     project_home = '/home/${PA_USER}/TenoHMS'"
echo "     if project_home not in sys.path:"
echo "         sys.path.insert(0, project_home)"
echo ""
echo "     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tenohms.settings.pythonanywhere')"
echo ""
echo "     try:"
echo "         from dotenv import load_dotenv"
echo "         load_dotenv()"
echo "     except ImportError:"
echo "         pass"
echo ""
echo "     from django.core.wsgi import get_wsgi_application"
echo "     application = get_wsgi_application()"
echo ""
echo "  3. Add Static files:"
echo "     /static/ -> /home/${PA_USER}/TenoHMS/staticfiles"
echo "     /media/  -> /home/${PA_USER}/TenoHMS/media"
echo ""
echo "  4. Click Reload"
echo ""
echo "  Your site: https://${PA_USER}.pythonanywhere.com"
echo "============================================"
