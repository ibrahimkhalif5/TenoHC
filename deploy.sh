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
echo "[1/8] Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "  Directory already exists, pulling latest..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo ""
echo "[2/8] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo ""
echo "[3/8] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[4/8] Setting up .env file..."
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
DEFAULT_FROM_EMAIL=TCHIMS <noreply@tenohms.com>

# Security
CSRF_TRUSTED_ORIGINS=https://${PA_USER}.pythonanywhere.com
EOF
    echo "  .env file created!"
else
    echo "  .env file already exists, skipping."
fi

echo ""
echo "[5/8] Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "[6/8] Running migrations..."
python manage.py migrate

echo ""
echo "[7/8] Loading seed data..."
python manage.py load_seed_csv
python manage.py seed_item_master

echo ""
echo "[8/8] Creating superuser..."
echo "  You will be prompted to create an admin account:"
python manage.py createsuperuser

echo ""
echo "============================================"
echo "  NEXT STEPS (on the Web tab):"
echo "============================================"
echo ""
echo "  1. Web tab -> Add new web app"
echo "     - Manual configuration -> Python 3.12"
echo ""
echo "  2. Source code: /home/${PA_USER}/TenoHMS"
echo "     WSGI config file: use the default Django template"
echo ""
echo "  3. Add Static files mapping:"
echo "     /static/ -> /home/${PA_USER}/TenoHMS/staticfiles"
echo "     /media/  -> /home/${PA_USER}/TenoHMS/media"
echo ""
echo "  4. Set environment variable:"
echo "     DJANGO_SETTINGS_MODULE = tenohms.settings.pythonanywhere"
echo ""
echo "  5. Click Reload"
echo ""
echo "  Your site: https://${PA_USER}.pythonanywhere.com"
echo "============================================"
