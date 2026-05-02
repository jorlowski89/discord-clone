from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from accounts.models import User

from .consumers import (
    ChannelConsumer,
    DirectConversationConsumer,
    VOICE_PARTICIPANTS,
    VoiceChannelConsumer,
)
from .models import Channel, DirectConversation, DirectMessage, Message


class ChannelConsumerTests(TransactionTestCase):
    def make_communicator(self, user, channel):
        communicator = WebsocketCommunicator(
            ChannelConsumer.as_asgi(),
            f"/ws/channels/{channel.slug}/",
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {"kwargs": {"slug": channel.slug}}
        return communicator

    def test_member_can_send_realtime_channel_message(self):
        user = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="StrongPass123",
        )
        channel = Channel.objects.create(name="General", created_by=user)
        channel.members.add(user)

        async def websocket_flow():
            communicator = self.make_communicator(user, channel)
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to({"content": "Hello realtime"})
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return response

        response = async_to_sync(websocket_flow)()

        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"]["content"], "Hello realtime")
        self.assertEqual(response["message"]["author"], "sender")
        self.assertTrue(
            Message.objects.filter(channel=channel, content="Hello realtime").exists()
        )

    def test_non_member_cannot_connect_to_channel_socket(self):
        owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="StrongPass123",
        )
        outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="StrongPass123",
        )
        channel = Channel.objects.create(name="General", created_by=owner)
        channel.members.add(owner)

        async def websocket_flow():
            communicator = self.make_communicator(outsider, channel)
            connected, _ = await communicator.connect()
            return connected

        connected = async_to_sync(websocket_flow)()

        self.assertFalse(connected)


class DirectConversationConsumerTests(TransactionTestCase):
    def make_communicator(self, user, conversation):
        communicator = WebsocketCommunicator(
            DirectConversationConsumer.as_asgi(),
            f"/ws/dm/{conversation.id}/",
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": conversation.id},
        }
        return communicator

    def test_participant_can_send_realtime_direct_message(self):
        sender = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="StrongPass123",
        )
        receiver = User.objects.create_user(
            username="receiver",
            email="receiver@example.com",
            password="StrongPass123",
        )
        conversation, _ = DirectConversation.get_or_create_between(sender, receiver)

        async def websocket_flow():
            communicator = self.make_communicator(sender, conversation)
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to({"content": "Hej realtime DM"})
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return response

        response = async_to_sync(websocket_flow)()

        self.assertEqual(response["type"], "message")
        self.assertEqual(response["message"]["content"], "Hej realtime DM")
        self.assertEqual(response["message"]["author"], "sender")
        self.assertTrue(
            DirectMessage.objects.filter(
                conversation=conversation,
                content="Hej realtime DM",
            ).exists()
        )

    def test_non_participant_cannot_connect_to_direct_socket(self):
        first_user = User.objects.create_user(
            username="first",
            email="first@example.com",
            password="StrongPass123",
        )
        second_user = User.objects.create_user(
            username="second",
            email="second@example.com",
            password="StrongPass123",
        )
        outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="StrongPass123",
        )
        conversation, _ = DirectConversation.get_or_create_between(
            first_user,
            second_user,
        )

        async def websocket_flow():
            communicator = self.make_communicator(outsider, conversation)
            connected, _ = await communicator.connect()
            return connected

        connected = async_to_sync(websocket_flow)()

        self.assertFalse(connected)


class VoiceChannelConsumerTests(TransactionTestCase):
    def setUp(self):
        VOICE_PARTICIPANTS.clear()

    def make_communicator(self, user, channel):
        communicator = WebsocketCommunicator(
            VoiceChannelConsumer.as_asgi(),
            f"/ws/voice/{channel.slug}/",
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {"kwargs": {"slug": channel.slug}}
        return communicator

    def test_member_can_observe_voice_channel_presence(self):
        user = User.objects.create_user(
            username="speaker",
            email="speaker@example.com",
            password="StrongPass123",
        )
        channel = Channel.objects.create(name="General", created_by=user)
        channel.members.add(user)

        async def websocket_flow():
            communicator = self.make_communicator(user, channel)
            connected, _ = await communicator.connect()
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return connected, response

        connected, response = async_to_sync(websocket_flow)()

        self.assertTrue(connected)
        self.assertEqual(response["type"], "voice_presence")
        self.assertEqual(response["participants"], [])

    def test_voice_join_is_broadcast_to_channel_observers(self):
        speaker = User.objects.create_user(
            username="speaker",
            email="speaker@example.com",
            password="StrongPass123",
        )
        observer = User.objects.create_user(
            username="observer",
            email="observer@example.com",
            password="StrongPass123",
        )
        channel = Channel.objects.create(name="General", created_by=speaker)
        channel.members.add(speaker, observer)

        async def websocket_flow():
            speaker_socket = self.make_communicator(speaker, channel)
            observer_socket = self.make_communicator(observer, channel)
            speaker_connected, _ = await speaker_socket.connect()
            observer_connected, _ = await observer_socket.connect()
            await speaker_socket.receive_json_from()
            await observer_socket.receive_json_from()

            await speaker_socket.send_json_to({"type": "join_voice"})
            speaker_presence = await speaker_socket.receive_json_from()
            observer_presence = await observer_socket.receive_json_from()
            await speaker_socket.disconnect()
            await observer_socket.disconnect()
            return speaker_connected, observer_connected, speaker_presence, observer_presence

        speaker_connected, observer_connected, speaker_presence, observer_presence = (
            async_to_sync(websocket_flow)()
        )

        self.assertTrue(speaker_connected)
        self.assertTrue(observer_connected)
        self.assertEqual(speaker_presence["type"], "voice_presence")
        self.assertEqual(observer_presence["type"], "voice_presence")
        self.assertEqual(
            observer_presence["participants"],
            [{"user_id": speaker.id, "username": "speaker"}],
        )

    def test_non_member_cannot_connect_to_voice_channel(self):
        owner = User.objects.create_user(
            username="owner2",
            email="owner2@example.com",
            password="StrongPass123",
        )
        outsider = User.objects.create_user(
            username="outsider2",
            email="outsider2@example.com",
            password="StrongPass123",
        )
        channel = Channel.objects.create(name="Voice", created_by=owner)
        channel.members.add(owner)

        async def websocket_flow():
            communicator = self.make_communicator(outsider, channel)
            connected, _ = await communicator.connect()
            return connected

        connected = async_to_sync(websocket_flow)()

        self.assertFalse(connected)
