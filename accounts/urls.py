from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LoginForm
from .views import admin_panel, moderation_panel, profile_view, register_view

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
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", register_view, name="register"),
    path("profile/", profile_view, name="profile"),
    path("moderation/", moderation_panel, name="moderation_panel"),
    path("control-center/", admin_panel, name="admin_panel"),
]
