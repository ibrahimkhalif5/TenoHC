import os
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "desktop-tenhms-prod-key-xk9!m3$vq2@p7j#n5t&w8e6r1u4y0z",
)

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Database — SQLite stored next to the exe
_resource_dir = os.environ.get("TENOHMS_BASE_DIR", str(BASE_DIR))  # noqa: F405
DB_DIR = os.environ.get("TENOHMS_DB_DIR", _resource_dir)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(DB_DIR, "db.sqlite3"),
    }
}

# Static & Media — bundled with the app
STATIC_ROOT = os.path.join(_resource_dir, "staticfiles")
MEDIA_ROOT = os.path.join(_resource_dir, "media")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# No email in desktop mode
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Security — local only
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
