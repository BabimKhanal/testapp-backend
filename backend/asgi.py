# backend/asgi.py
import os
from django.core.asgi import get_asgi_application

# Set the settings module before any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Now get the ASGI application (this initializes Django)
django_asgi_app = get_asgi_application()

# After Django is ready, import the rest
from channels.routing import ProtocolTypeRouter, URLRouter
from api.middleware import JwtAuthMiddleware
from api.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})