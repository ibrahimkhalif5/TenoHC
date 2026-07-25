import os
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "desktop-tenhms-prod-key-xk9!m3$vq2@p7j#n5t&w8e6r1u4y0z",
)

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Bundle dir = read-only files (templates, static) bundled inside exe
BUNDLE_DIR = os.environ.get("TENOHMS_BUNDLE_DIR", str(BASE_DIR))  # noqa: F405
# Data dir = writable location next to exe (db, media)
DATA_DIR = os.environ.get("TENOHMS_DATA_DIR", str(BASE_DIR))  # noqa: F405

# Database — stored next to the exe (writable)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(DATA_DIR, "db.sqlite3"),
    }
}

# Templates — inside the bundle
TEMPLATES[0]["DIRS"] = [os.path.join(BUNDLE_DIR, "templates")]  # noqa: F405

# Static files — inside the bundle
STATIC_ROOT = os.path.join(BUNDLE_DIR, "staticfiles")

# Media files — writable, next to the exe
MEDIA_ROOT = os.path.join(DATA_DIR, "media")

# Static URL source for collectstatic
STATICFILES_DIRS = [os.path.join(BUNDLE_DIR, "static")]

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
