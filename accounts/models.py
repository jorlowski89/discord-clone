from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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
    last_seen = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS = ["email"]

    @property
    def has_admin_access(self) -> bool:
        return self.is_superuser or self.role == UserRole.ADMIN

    @property
    def has_moderation_access(self) -> bool:
        return self.has_admin_access or self.role == UserRole.MODERATOR

    @property
    def is_online(self) -> bool:
        if not self.last_seen:
            return False
        return self.last_seen >= timezone.now() - timezone.timedelta(minutes=5)

    def __str__(self) -> str:
        return self.username
