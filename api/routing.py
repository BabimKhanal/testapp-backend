# api/routing.py
from api.consumers import ChatConsumer
from django.urls import re_path

websocket_urlpatterns = [
    re_path(r"ws/chat/$", ChatConsumer.as_asgi())
]