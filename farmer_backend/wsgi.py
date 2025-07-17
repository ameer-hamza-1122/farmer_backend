"""
WSGI config for farmer_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmer_backend.settings')

application = get_wsgi_application()

# Warp the application with WhiteNoise to serve static files
application = WhiteNoise(application, root=os.path.join(os.path.dirname(__file__), 'static'))
