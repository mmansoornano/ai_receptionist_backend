"""
WSGI config for receptionist project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'receptionist.settings.production')

application = get_wsgi_application()
