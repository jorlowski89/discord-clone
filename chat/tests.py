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

    def test_blocked_member_cannot_send_message(self):
        self.user.is_blocked = True
        self.user.save(update_fields=["is_blocked"])
        channel = Channel.objects.create(name="General", created_by=self.user)
        channel.members.add(self.user)
        self.client.force_login(self.user)

        response = self.client.post(
            channel.get_absolute_url(),
            {"content": "Blocked message"},
        )

        self.assertRedirects(response, channel.get_absolute_url())
        self.assertFalse(Message.objects.filter(channel=channel).exists())

    def test_blocked_user_cannot_create_channel(self):
        self.user.is_blocked = True
        self.user.save(update_fields=["is_blocked"])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("channel_create"),
            {"name": "Blocked room", "description": "Nope"},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(Channel.objects.filter(name="Blocked room").exists())

    def test_blocked_user_cannot_join_channel(self):
        self.user.is_blocked = True
        self.user.save(update_fields=["is_blocked"])
        channel = Channel.objects.create(name="General", created_by=self.user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("channel_join", args=[channel.slug]))

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(channel.members.filter(pk=self.user.pk).exists())

    def test_blocked_member_sees_disabled_message_notice(self):
        self.user.is_blocked = True
        self.user.save(update_fields=["is_blocked"])
        channel = Channel.objects.create(name="General", created_by=self.user)
        channel.members.add(self.user)
        self.client.force_login(self.user)

        response = self.client.get(channel.get_absolute_url())

        self.assertContains(response, "Wysylanie wiadomosci jest zablokowane")
