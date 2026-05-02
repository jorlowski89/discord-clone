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


def notify_user(user_id, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"user_notifications_{user_id}",
        {
            "type": "notification.event",
            "payload": payload,
        },
    )


def notify_channel_message(message):
    url = message.channel.get_absolute_url()
    payload = {
        "kind": "channel",
        "url": url,
        "title": f"#{message.channel.name}",
        "author": message.author.username,
        "preview": message.content or "Nowa wiadomość multimedialna",
    }
    member_ids = (
        message.channel.members.exclude(id=message.author_id)
        .values_list("id", flat=True)
    )
    for user_id in member_ids:
        notify_user(user_id, payload)


def notify_direct_message(message):
    conversation = message.conversation
    receiver = conversation.other_user(message.author)
    notify_user(
        receiver.id,
        {
            "kind": "direct",
            "url": conversation.get_absolute_url(),
            "title": f"DM od {message.author.username}",
            "author": message.author.username,
            "preview": message.content or "Nowa wiadomość multimedialna",
        },
    )


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
    notify_channel_message(message)


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
    notify_direct_message(message)
