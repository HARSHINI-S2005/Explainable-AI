"""
ASGI config for college_recommender project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'college_recommender.settings')

application = get_asgi_application()










