from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chat.models import Channel, Message


User = get_user_model()


class AccountsFlowTests(TestCase):
    def test_home_page_is_available(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PyCord")

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
        self.assertContains(response, "Strona nie zostala znaleziona", status_code=404)

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

        response = self.client.post(reverse("toggle_user_block", args=[user.id]))

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
            content="Niegrzeczna wiadomosc",
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

        self.assertContains(response, "Kanaly")
        self.assertContains(response, "Usun kanal")
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

        self.assertNotContains(response, "Usun kanal")

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
