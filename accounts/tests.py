from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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

    def test_unknown_page_uses_custom_404(self):
        response = self.client.get("/brak-takiej-strony/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Strona nie zostala znaleziona", status_code=404)
