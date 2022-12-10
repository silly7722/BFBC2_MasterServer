"""
ASGI config for BFBC2_MasterServer project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BFBC2_MasterServer.settings")

django_asgi_app = get_asgi_application()

from Plasma.urls import websocket_urlpatterns as plasma_websocket_urlpatterns
from Theater.models import Lobby
from Theater.urls import websocket_urlpatterns as theater_websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(plasma_websocket_urlpatterns + theater_websocket_urlpatterns)
        ),
    }
)

# Remove all lobbies on server start
Lobby.objects.all().delete()
