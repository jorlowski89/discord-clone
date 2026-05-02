import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import models

from .models import Channel, DirectConversation, DirectMessage, Message
from .realtime import serialize_message


VOICE_PARTICIPANTS = {}


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


class VoiceChannelConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        self.group_name = f"voice_channel_{self.slug}"
        self.user = self.scope["user"]
        self.in_voice = False

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.channel_id = await self.get_joined_channel_id()
        if self.channel_id is None:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_presence()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            if self.in_voice:
                self.remove_voice_participant()
                await self.broadcast_presence()
                await self.broadcast_signal(
                    {
                        "type": "user_left",
                        "user_id": self.user.id,
                        "username": self.user.username,
                    }
                )
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        signal_type = payload.get("type")
        if signal_type not in {
            "join_voice",
            "leave",
            "offer",
            "answer",
            "ice_candidate",
        }:
            return

        if signal_type == "join_voice":
            if await self.user_is_blocked():
                await self.send_json(
                    {
                        "type": "error",
                        "message": "Zablokowane konto nie moze dolaczyc do rozmowy glosowej.",
                    }
                )
                return

            self.in_voice = True
            self.add_voice_participant()
            await self.broadcast_presence()
            await self.broadcast_signal(
                {
                    "type": "user_joined",
                    "user_id": self.user.id,
                    "username": self.user.username,
                }
            )
            return

        if signal_type == "leave":
            self.in_voice = False
            self.remove_voice_participant()
            await self.broadcast_presence()
            await self.broadcast_signal(
                {
                    "type": "user_left",
                    "user_id": self.user.id,
                    "username": self.user.username,
                }
            )
            return

        if not self.in_voice:
            return

        payload["sender_user_id"] = self.user.id
        payload["sender_username"] = self.user.username

        await self.broadcast_signal(payload)

    async def voice_signal(self, event):
        await self.send_json(event["payload"])

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))

    async def send_presence(self):
        await self.send_json(
            {
                "type": "voice_presence",
                "participants": self.get_voice_participants(),
            }
        )

    async def broadcast_presence(self):
        await self.broadcast_signal(
            {
                "type": "voice_presence",
                "participants": self.get_voice_participants(),
            }
        )

    async def broadcast_signal(self, payload):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "voice.signal",
                "payload": payload,
            },
        )

    def get_voice_participants(self):
        participants = VOICE_PARTICIPANTS.get(self.slug, {})
        return [
            {"user_id": user_id, "username": username}
            for user_id, username in participants.items()
        ]

    def add_voice_participant(self):
        VOICE_PARTICIPANTS.setdefault(self.slug, {})[self.user.id] = self.user.username

    def remove_voice_participant(self):
        participants = VOICE_PARTICIPANTS.get(self.slug, {})
        participants.pop(self.user.id, None)
        if not participants:
            VOICE_PARTICIPANTS.pop(self.slug, None)

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
