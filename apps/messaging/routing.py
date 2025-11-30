# apps/messaging/routing.py

from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Chat WebSocket
    re_path(r'ws/chat/(?P<conversation_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),

    # Online Status WebSocket
    path('ws/status/', consumers.OnlineStatusConsumer.as_asgi()),
]