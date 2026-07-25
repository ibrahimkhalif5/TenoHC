"""
WSGI config for tenohms project.
On PythonAnywhere, set DJANGO_SETTINGS_MODULE via the Web tab's WSGI config.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenohms.settings.pythonanywhere")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
