from django.contrib import admin

from .models import Channel, DirectConversation, DirectMessage, Message


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("channel", "author", "created_at", "is_deleted")
    list_filter = ("channel", "is_deleted", "created_at")
    search_fields = ("content", "author__username", "channel__name")


@admin.register(DirectConversation)
class DirectConversationAdmin(admin.ModelAdmin):
    list_display = ("user_one", "user_two", "created_at")
    search_fields = ("user_one__username", "user_two__username")


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "author", "created_at", "is_deleted")
    list_filter = ("is_deleted", "created_at")
    search_fields = (
        "content",
        "author__username",
        "conversation__user_one__username",
        "conversation__user_two__username",
    )
