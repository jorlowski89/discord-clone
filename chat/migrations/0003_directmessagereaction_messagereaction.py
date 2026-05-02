from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0002_directconversation_directmessage_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DirectMessageReaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "emoji",
                    models.CharField(
                        choices=[
                            ("👍", "Lubię"),
                            ("❤️", "Super"),
                            ("😂", "Śmieszne"),
                        ],
                        max_length=8,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="direct_message_reactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reactions",
                        to="chat.directmessage",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MessageReaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "emoji",
                    models.CharField(
                        choices=[
                            ("👍", "Lubię"),
                            ("❤️", "Super"),
                            ("😂", "Śmieszne"),
                        ],
                        max_length=8,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_reactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reactions",
                        to="chat.message",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="directmessagereaction",
            constraint=models.UniqueConstraint(
                fields=("message", "author", "emoji"),
                name="unique_direct_message_reaction",
            ),
        ),
        migrations.AddConstraint(
            model_name="messagereaction",
            constraint=models.UniqueConstraint(
                fields=("message", "author", "emoji"),
                name="unique_message_reaction",
            ),
        ),
    ]
