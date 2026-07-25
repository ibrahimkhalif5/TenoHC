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
    # Generate secret key
    SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

    cat > .env << EOF
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${PA_USER}.pythonanywhere.com
DJANGO_SETTINGS_MODULE=tenohms.settings.pythonanywhere

# MySQL Database
DB_ENGINE=django.db.backends.mysql
DB_NAME=${PA_USER}\$thhims_db
DB_USER=${PA_USER}
DB_PASSWORD=CHANGE_ME_AFTER_CREATING_DB
DB_HOST=${PA_USER}.mysql.pythonanywhere.com
DB_PORT=

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
    echo ""
    echo "  *** IMPORTANT: Edit .env and set DB_PASSWORD ***"
    echo "  Run: nano .env"
    echo "  Change CHANGE_ME_AFTER_CREATING_DB to your MySQL password"
    echo ""
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
echo "[7/8] Creating superuser..."
echo "  You will be prompted to create an admin account:"
python manage.py createsuperuser

echo ""
echo "[8/8] Setup complete!"
echo ""
echo "============================================"
echo "  NEXT STEPS (do these on the Web tab):"
echo "============================================"
echo ""
echo "  1. Go to Web tab → Add new web app"
echo "     - Manual configuration → Python 3.10"
echo ""
echo "  2. Click WSGI config file → replace contents with:"
echo "     (I'll print it below)"
echo ""
echo "  3. Add Static files:"
echo "     /static/ -> /home/${PA_USER}/TenoHMS/staticfiles"
echo "     /media/  -> /home/${PA_USER}/TenoHMS/media"
echo ""
echo "  4. Click Reload"
echo ""
echo "  Your site: https://${PA_USER}.pythonanywhere.com"
echo "============================================"
