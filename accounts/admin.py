from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Profil komunikatora",
            {
                "fields": (
                    "avatar",
                    "bio",
                    "role",
                    "is_blocked",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Dodatkowe informacje",
            {
                "fields": (
                    "email",
                    "role",
                )
            },
        ),
    )
    list_display = ("username", "email", "role", "is_staff", "is_blocked")
    search_fields = ("username", "email")
