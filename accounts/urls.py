from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LoginForm
from . import views

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("presence/", views.presence_status, name="presence_status"),
    path("claim-admin/", views.claim_first_admin, name="claim_first_admin"),
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("moderation/", views.moderation_panel, name="moderation_panel"),
    path("control-center/", views.admin_panel, name="admin_panel"),
    path("users/<int:user_id>/role/", views.update_user_role, name="update_user_role"),
    path("users/<int:user_id>/block/", views.toggle_user_block, name="toggle_user_block"),
    path("users/<int:user_id>/delete/", views.delete_user, name="delete_user"),
    path(
        "messages/<int:message_id>/delete/",
        views.delete_message,
        name="delete_message",
    ),
    path(
        "channels/<int:channel_id>/delete/",
        views.delete_channel,
        name="delete_channel",
    ),
]
