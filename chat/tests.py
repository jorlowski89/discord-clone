from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Channel, DirectConversation, DirectMessage, Message
from .realtime import serialize_message


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

    def test_message_serializer_includes_media_urls(self):
        self.user.avatar = "avatars/tester.png"
        self.user.save(update_fields=["avatar"])
        channel = Channel.objects.create(name="General", created_by=self.user)
        message = Message.objects.create(
            channel=channel,
            author=self.user,
            content="Media",
            image="chat/images/screen.png",
            audio="chat/audio/voice.webm",
        )

        payload = serialize_message(message)

        self.assertEqual(payload["content"], "Media")
        self.assertIn("avatars/tester.png", payload["avatar_url"])
        self.assertIn("chat/images/screen.png", payload["image_url"])
        self.assertIn("chat/audio/voice.webm", payload["audio_url"])

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

    def test_channel_list_can_be_searched(self):
        Channel.objects.create(
            name="Python",
            description="Projekt zaliczeniowy",
            created_by=self.user,
        )
        Channel.objects.create(
            name="Games",
            description="Offtopic",
            created_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("channel_list"), {"q": "python"})

        self.assertContains(response, "# Python")
        self.assertNotContains(response, "# Games")

    def test_user_can_start_direct_conversation(self):
        other_user = User.objects.create_user(
            username="friend",
            email="friend@example.com",
            password="StrongPass123",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("direct_conversation_start", args=[other_user.id])
        )

        conversation = DirectConversation.objects.get()
        self.assertRedirects(response, conversation.get_absolute_url())
        self.assertTrue(conversation.includes(self.user))
        self.assertTrue(conversation.includes(other_user))

    def test_direct_conversation_pair_is_reused(self):
        other_user = User.objects.create_user(
            username="friend",
            email="friend@example.com",
            password="StrongPass123",
        )

        first, _ = DirectConversation.get_or_create_between(self.user, other_user)
        second, created = DirectConversation.get_or_create_between(other_user, self.user)

        self.assertFalse(created)
        self.assertEqual(first, second)

    def test_user_can_send_direct_message(self):
        other_user = User.objects.create_user(
            username="friend",
            email="friend@example.com",
            password="StrongPass123",
        )
        conversation, _ = DirectConversation.get_or_create_between(
            self.user,
            other_user,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            conversation.get_absolute_url(),
            {"content": "Private hello"},
        )

        self.assertRedirects(response, conversation.get_absolute_url())
        self.assertEqual(DirectMessage.objects.filter(conversation=conversation).count(), 1)

    def test_non_participant_cannot_open_direct_conversation(self):
        other_user = User.objects.create_user(
            username="friend",
            email="friend@example.com",
            password="StrongPass123",
        )
        stranger = User.objects.create_user(
            username="stranger",
            email="stranger@example.com",
            password="StrongPass123",
        )
        conversation, _ = DirectConversation.get_or_create_between(
            self.user,
            other_user,
        )
        self.client.force_login(stranger)

        response = self.client.get(conversation.get_absolute_url())

        self.assertRedirects(response, reverse("direct_conversation_list"))

    def test_blocked_user_cannot_start_direct_conversation(self):
        self.user.is_blocked = True
        self.user.save(update_fields=["is_blocked"])
        other_user = User.objects.create_user(
            username="friend",
            email="friend@example.com",
            password="StrongPass123",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("direct_conversation_start", args=[other_user.id])
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(DirectConversation.objects.exists())

    def test_blocked_user_cannot_send_direct_message(self):
        self.user.is_blocked = True
        self.user.save(update_fields=["is_blocked"])
        other_user = User.objects.create_user(
            username="friend",
            email="friend@example.com",
            password="StrongPass123",
        )
        conversation, _ = DirectConversation.get_or_create_between(
            self.user,
            other_user,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            conversation.get_absolute_url(),
            {"content": "Blocked private hello"},
        )

        self.assertRedirects(response, conversation.get_absolute_url())
        self.assertFalse(DirectMessage.objects.filter(conversation=conversation).exists())

    def test_direct_user_list_can_be_searched(self):
        User.objects.create_user(
            username="anna",
            email="anna@example.com",
            password="StrongPass123",
        )
        User.objects.create_user(
            username="bartek",
            email="bartek@example.com",
            password="StrongPass123",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("direct_conversation_list"), {"q": "ann"})

        self.assertContains(response, "anna")
        self.assertNotContains(response, "bartek")
