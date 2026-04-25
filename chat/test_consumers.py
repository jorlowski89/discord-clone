from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from accounts.models import User

from .consumers import ChannelConsumer, DirectConversationConsumer
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
