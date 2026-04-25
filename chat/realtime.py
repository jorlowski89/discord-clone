from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone


def serialize_message(message):
    avatar_url = message.author.avatar.url if message.author.avatar else ""
    return {
        "id": message.id,
        "author": message.author.username,
        "avatar_url": avatar_url,
        "content": message.content,
        "created_at": timezone.localtime(message.created_at).strftime("%d.%m.%Y %H:%M"),
        "image_url": message.image.url if message.image else "",
        "audio_url": message.audio.url if message.audio else "",
    }


def broadcast_channel_message(message):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"channel_{message.channel.slug}",
        {
            "type": "chat.message",
            "message": serialize_message(message),
        },
    )


def broadcast_direct_message(message):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"dm_{message.conversation_id}",
        {
            "type": "direct.message",
            "message": serialize_message(message),
        },
    )
