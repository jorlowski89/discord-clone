import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import models

from .models import Channel, DirectConversation, DirectMessage, Message
from .realtime import serialize_message


class ChannelConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        self.group_name = f"channel_{self.slug}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.channel_id = await self.get_joined_channel_id()
        if self.channel_id is None:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        content = (payload.get("content") or "").strip()
        if not content:
            return

        if await self.user_is_blocked():
            await self.send_json(
                {
                    "type": "error",
                    "message": "Twoje konto jest zablokowane i nie moze pisac.",
                }
            )
            return

        message = await self.create_message(content)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message": message,
            },
        )

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def get_joined_channel_id(self):
        try:
            channel = Channel.objects.get(slug=self.slug, members=self.user)
        except Channel.DoesNotExist:
            return None
        return channel.id

    @database_sync_to_async
    def user_is_blocked(self):
        self.user.refresh_from_db(fields=["is_blocked"])
        return self.user.is_blocked

    @database_sync_to_async
    def create_message(self, content):
        message = Message.objects.create(
            channel_id=self.channel_id,
            author=self.user,
            content=content,
        )
        return serialize_message(message)


class DirectConversationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"dm_{self.conversation_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        if not await self.user_can_access_conversation():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        content = (payload.get("content") or "").strip()
        if not content:
            return

        if await self.user_is_blocked():
            await self.send_json(
                {
                    "type": "error",
                    "message": "Twoje konto jest zablokowane i nie moze pisac.",
                }
            )
            return

        message = await self.create_message(content)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "direct.message",
                "message": message,
            },
        )

    async def direct_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def user_can_access_conversation(self):
        return DirectConversation.objects.filter(
            pk=self.conversation_id,
        ).filter(
            models.Q(user_one=self.user) | models.Q(user_two=self.user)
        ).exists()

    @database_sync_to_async
    def user_is_blocked(self):
        self.user.refresh_from_db(fields=["is_blocked"])
        return self.user.is_blocked

    @database_sync_to_async
    def create_message(self, content):
        message = DirectMessage.objects.create(
            conversation_id=self.conversation_id,
            author=self.user,
            content=content,
        )
        return serialize_message(message)
