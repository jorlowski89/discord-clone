from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Channel(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_channels",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="channels",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"#{self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "channel"
            slug = base_slug
            counter = 2
            while Channel.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("channel_detail", kwargs={"slug": self.slug})


class Message(models.Model):
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="chat/images/", blank=True, null=True)
    audio = models.FileField(upload_to="chat/audio/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.author} in {self.channel}"


class DirectConversation(models.Model):
    user_one = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_conversations_started",
    )
    user_two = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_conversations_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_one", "user_two"],
                name="unique_direct_conversation_pair",
            ),
            models.CheckConstraint(
                condition=~models.Q(user_one=models.F("user_two")),
                name="direct_conversation_distinct_users",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_one} <-> {self.user_two}"

    @classmethod
    def get_or_create_between(cls, first_user, second_user):
        if first_user.pk == second_user.pk:
            raise ValueError("Cannot create a direct conversation with yourself.")

        user_one, user_two = sorted(
            [first_user, second_user],
            key=lambda user: user.pk,
        )
        return cls.objects.get_or_create(user_one=user_one, user_two=user_two)

    def includes(self, user) -> bool:
        return user.pk in {self.user_one_id, self.user_two_id}

    def other_user(self, user):
        if user.pk == self.user_one_id:
            return self.user_two
        if user.pk == self.user_two_id:
            return self.user_one
        raise ValueError("User is not a participant in this conversation.")

    def get_absolute_url(self):
        return reverse("direct_conversation_detail", kwargs={"pk": self.pk})


class DirectMessage(models.Model):
    conversation = models.ForeignKey(
        DirectConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="direct_messages",
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="dm/images/", blank=True, null=True)
    audio = models.FileField(upload_to="dm/audio/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"DM from {self.author}"
