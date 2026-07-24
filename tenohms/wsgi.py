"""
WSGI config for tenohms project.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenohms.settings.production")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
