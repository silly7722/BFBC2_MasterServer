from django.urls import path

from Plasma.consumer import PlasmaConsumer

websocket_urlpatterns = [
    path("plasma", PlasmaConsumer.as_asgi()),
]
