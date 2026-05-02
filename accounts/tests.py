from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from chat.models import Channel, DirectConversation, DirectMessage, Message


User = get_user_model()


class AccountsFlowTests(TestCase):
    def test_home_page_is_available(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PyCord")

    def test_home_page_shows_latest_incoming_activity(self):
        user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="StrongPassword123",
        )
        other_user = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="StrongPassword123",
        )
        conversation, _ = DirectConversation.get_or_create_between(user, other_user)
        DirectMessage.objects.create(
            conversation=conversation,
            author=other_user,
            content="Private ping",
        )
        channel = Channel.objects.create(name="General", created_by=other_user)
        channel.members.add(user, other_user)
        Message.objects.create(
            channel=channel,
            author=other_user,
            content="Channel ping",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, "Private ping")
        self.assertContains(response, "Channel ping")

    def test_user_can_register(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "tester",
                "email": "tester@example.com",
                "bio": "Hello",
                "password1": "StrongPassword123",
                "password2": "StrongPassword123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="tester").exists())

    def test_first_user_can_claim_admin_role(self):
        user = User.objects.create_user(
            username="firstadmin",
            email="firstadmin@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("claim_first_admin"))

        user.refresh_from_db()
        self.assertRedirects(response, reverse("admin_panel"))
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_admin_claim_is_blocked_when_admin_exists(self):
        User.objects.create_user(
            username="existingadmin",
            email="existingadmin@example.com",
            password="StrongPassword123",
            role="admin",
        )
        user = User.objects.create_user(
            username="lateuser",
            email="lateuser@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("claim_first_admin"))

        user.refresh_from_db()
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(user.role, "user")

    def test_user_online_status_uses_last_seen(self):
        user = User.objects.create_user(
            username="statususer",
            email="statususer@example.com",
            password="StrongPassword123",
            last_seen=timezone.now(),
        )

        self.assertTrue(user.is_online)

        user.last_seen = timezone.now() - timezone.timedelta(minutes=6)

        self.assertFalse(user.is_online)

    def test_logout_marks_user_offline(self):
        user = User.objects.create_user(
            username="logoutstatus",
            email="logoutstatus@example.com",
            password="StrongPassword123",
            last_seen=timezone.now(),
        )
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))

        user.refresh_from_db()
        self.assertRedirects(response, reverse("home"))
        self.assertIsNone(user.last_seen)

    def test_presence_endpoint_returns_live_status(self):
        user = User.objects.create_user(
            username="presence-reader",
            email="presence-reader@example.com",
            password="StrongPassword123",
        )
        other_user = User.objects.create_user(
            username="presence-other",
            email="presence-other@example.com",
            password="StrongPassword123",
            last_seen=timezone.now(),
        )
        self.client.force_login(user)

        response = self.client.get(reverse("presence_status"), {"ids": str(other_user.id)})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"users": [{"id": other_user.id, "online": True}]},
        )

    def test_user_can_register_with_weak_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "weakpass",
                "email": "weakpass@example.com",
                "bio": "",
                "password1": "1",
                "password2": "1",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="weakpass").exists())

    def test_user_can_change_password_from_profile(self):
        user = User.objects.create_user(
            username="passworduser",
            email="passworduser@example.com",
            password="old",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("profile"),
            {
                "action": "password",
                "old_password": "old",
                "new_password1": "1",
                "new_password2": "1",
            },
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertTrue(user.check_password("1"))

    def test_regular_user_cannot_open_moderation_panel(self):
        user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("moderation_panel"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nie masz uprawnien do tej sekcji.")

    def test_moderator_can_open_moderation_panel(self):
        moderator = User.objects.create_user(
            username="mod",
            email="mod@example.com",
            password="StrongPassword123",
            role="moderator",
        )
        self.client.force_login(moderator)

        response = self.client.get(reverse("moderation_panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panel moderacji")

    def test_only_admin_can_open_admin_panel(self):
        admin = User.objects.create_user(
            username="boss",
            email="boss@example.com",
            password="StrongPassword123",
            role="admin",
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centrum kontroli")

    def test_superuser_can_open_admin_panel(self):
        superuser = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(superuser)

        response = self.client.get(reverse("admin_panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centrum kontroli")

    def test_unknown_page_uses_custom_404(self):
        response = self.client.get("/brak-takiej-strony/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Strona nie została znaleziona", status_code=404)

    def test_uploaded_media_is_served_by_url(self):
        media_file = settings.MEDIA_ROOT / "test-media.txt"
        media_file.write_text("media ok", encoding="utf-8")

        try:
            response = self.client.get("/media/test-media.txt")
            content = b"".join(response.streaming_content)
            response.close()
        finally:
            media_file.unlink(missing_ok=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, b"media ok")

    def test_admin_can_update_user_role(self):
        admin = User.objects.create_user(
            username="boss",
            email="boss@example.com",
            password="StrongPassword123",
            role="admin",
        )
        user = User.objects.create_user(
            username="helper",
            email="helper@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("update_user_role", args=[user.id]),
            {"role": "moderator"},
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("admin_panel"))
        self.assertEqual(user.role, "moderator")

    def test_admin_can_block_regular_user(self):
        admin = User.objects.create_user(
            username="adminblock",
            email="adminblock@example.com",
            password="StrongPassword123",
            role="admin",
        )
        user = User.objects.create_user(
            username="loud",
            email="loud@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(admin)

        response = self.client.post(reverse("toggle_user_block", args=[user.id]))

        user.refresh_from_db()
        self.assertRedirects(response, reverse("admin_panel"))
        self.assertTrue(user.is_blocked)

    def test_moderator_can_block_regular_user(self):
        moderator = User.objects.create_user(
            username="mod2",
            email="mod2@example.com",
            password="StrongPassword123",
            role="moderator",
        )
        user = User.objects.create_user(
            username="loud",
            email="loud@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(moderator)

        response = self.client.post(
            reverse("toggle_user_block", args=[user.id]),
            follow=True,
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("moderation_panel"))
        self.assertTrue(user.is_blocked)

    def test_moderator_can_delete_message(self):
        moderator = User.objects.create_user(
            username="mod3",
            email="mod3@example.com",
            password="StrongPassword123",
            role="moderator",
        )
        author = User.objects.create_user(
            username="author",
            email="author@example.com",
            password="StrongPassword123",
        )
        channel = Channel.objects.create(name="General", created_by=author)
        message = Message.objects.create(
            channel=channel,
            author=author,
            content="Niegrzeczna wiadomość",
        )
        self.client.force_login(moderator)

        response = self.client.post(reverse("delete_message", args=[message.id]))

        message.refresh_from_db()
        self.assertRedirects(response, channel.get_absolute_url())
        self.assertTrue(message.is_deleted)

    def test_moderation_panel_filters_messages(self):
        admin = User.objects.create_user(
            username="filteradmin",
            email="filteradmin@example.com",
            password="StrongPassword123",
            role="admin",
        )
        first_author = User.objects.create_user(
            username="firstauthor",
            email="firstauthor@example.com",
            password="StrongPassword123",
        )
        second_author = User.objects.create_user(
            username="secondauthor",
            email="secondauthor@example.com",
            password="StrongPassword123",
        )
        first_channel = Channel.objects.create(name="First", created_by=admin)
        second_channel = Channel.objects.create(name="Second", created_by=admin)
        Message.objects.create(
            channel=first_channel,
            author=first_author,
            content="Visible message",
        )
        Message.objects.create(
            channel=second_channel,
            author=second_author,
            content="Hidden message",
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("moderation_panel"),
            {"user": first_author.id, "channel": first_channel.id},
        )

        self.assertContains(response, "Visible message")
        self.assertNotContains(response, "Hidden message")

    def test_admin_can_delete_channel(self):
        admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="StrongPassword123",
            role="admin",
        )
        channel = Channel.objects.create(name="Tmp", created_by=admin)
        self.client.force_login(admin)

        response = self.client.post(reverse("delete_channel", args=[channel.id]))

        self.assertRedirects(response, reverse("moderation_panel"))
        self.assertFalse(Channel.objects.filter(id=channel.id).exists())

    def test_admin_sees_channel_management_in_moderation_panel(self):
        admin = User.objects.create_user(
            username="channeladmin",
            email="channeladmin@example.com",
            password="StrongPassword123",
            role="admin",
        )
        Channel.objects.create(name="General", created_by=admin)
        self.client.force_login(admin)

        response = self.client.get(reverse("moderation_panel"))

        self.assertContains(response, "Kanały")
        self.assertContains(response, "Usuń kanał")
        self.assertContains(response, "# General")

    def test_moderator_does_not_see_channel_management(self):
        moderator = User.objects.create_user(
            username="onlymod",
            email="onlymod@example.com",
            password="StrongPassword123",
            role="moderator",
        )
        Channel.objects.create(name="General", created_by=moderator)
        self.client.force_login(moderator)

        response = self.client.get(reverse("moderation_panel"))

        self.assertNotContains(response, "Usuń kanał")

    def test_moderation_panel_shows_user_blocking(self):
        admin = User.objects.create_user(
            username="adminwithoutusers",
            email="adminwithoutusers@example.com",
            password="StrongPassword123",
            role="admin",
        )
        User.objects.create_user(
            username="regularuser",
            email="regularuser@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("moderation_panel"))

        self.assertContains(response, "Zablokuj")
        self.assertContains(response, "Użytkownicy</h2>")

    def test_admin_can_delete_user(self):
        admin = User.objects.create_user(
            username="deleteadmin",
            email="deleteadmin@example.com",
            password="StrongPassword123",
            role="admin",
        )
        user = User.objects.create_user(
            username="delete-me",
            email="delete-me@example.com",
            password="StrongPassword123",
        )
        self.client.force_login(admin)

        response = self.client.post(reverse("delete_user", args=[user.id]))

        self.assertRedirects(response, reverse("admin_panel"))
        self.assertFalse(User.objects.filter(id=user.id).exists())

    def test_admin_cannot_delete_self(self):
        admin = User.objects.create_user(
            username="selfadmin",
            email="selfadmin@example.com",
            password="StrongPassword123",
            role="admin",
        )
        self.client.force_login(admin)

        response = self.client.post(reverse("delete_user", args=[admin.id]))

        self.assertRedirects(response, reverse("admin_panel"))
        self.assertTrue(User.objects.filter(id=admin.id).exists())

    def test_blocked_user_cannot_edit_profile(self):
        user = User.objects.create_user(
            username="blocked",
            email="blocked@example.com",
            password="StrongPassword123",
            is_blocked=True,
            bio="Old bio",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("profile"),
            {"email": "changed@example.com", "bio": "Changed bio"},
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.email, "blocked@example.com")
        self.assertEqual(user.bio, "Old bio")

    def test_blocked_moderator_cannot_delete_message(self):
        moderator = User.objects.create_user(
            username="blockedmod",
            email="blockedmod@example.com",
            password="StrongPassword123",
            role="moderator",
            is_blocked=True,
        )
        author = User.objects.create_user(
            username="writer",
            email="writer@example.com",
            password="StrongPassword123",
        )
        channel = Channel.objects.create(name="Moderated", created_by=author)
        message = Message.objects.create(
            channel=channel,
            author=author,
            content="Still here",
        )
        self.client.force_login(moderator)

        response = self.client.post(reverse("delete_message", args=[message.id]))

        message.refresh_from_db()
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(message.is_deleted)
