from django.contrib import admin

from .models import Channel, Message


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
