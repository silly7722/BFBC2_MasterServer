from django.urls import path

from Theater.consumer import TheaterConsumer

websocket_urlpatterns = [
    path("theater", TheaterConsumer.as_asgi()),
]
