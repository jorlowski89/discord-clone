from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/channels/<slug:slug>/", consumers.ChannelConsumer.as_asgi()),
    path("ws/dm/<int:conversation_id>/", consumers.DirectConversationConsumer.as_asgi()),
]
