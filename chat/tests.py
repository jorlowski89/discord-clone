from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Channel, Message


class ChannelFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="StrongPass123",
        )

    def test_user_can_create_joined_channel(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("channel_create"),
            {"name": "General", "description": "Main room"},
        )

        channel = Channel.objects.get(name="General")
        self.assertRedirects(response, channel.get_absolute_url())
        self.assertTrue(channel.members.filter(pk=self.user.pk).exists())

    def test_member_can_send_text_message(self):
        channel = Channel.objects.create(name="General", created_by=self.user)
        channel.members.add(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            channel.get_absolute_url(),
            {"content": "Hello there"},
        )

        self.assertRedirects(response, channel.get_absolute_url())
        self.assertEqual(Message.objects.filter(channel=channel).count(), 1)
