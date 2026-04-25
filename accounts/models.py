from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Administrator"
    MODERATOR = "moderator", "Moderator"
    USER = "user", "Uzytkownik"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )
    is_blocked = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["email"]

    @property
    def has_admin_access(self) -> bool:
        return self.is_superuser or self.role == UserRole.ADMIN

    @property
    def has_moderation_access(self) -> bool:
        return self.has_admin_access or self.role == UserRole.MODERATOR

    def __str__(self) -> str:
        return self.username
