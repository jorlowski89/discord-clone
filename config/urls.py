from django.contrib import admin
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve as serve_static

from accounts.views import custom_404, home

urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("channels/", include("chat.urls")),
    path("admin/", admin.site.urls),
    re_path(
        r"^media/(?P<path>.*)$",
        serve_static,
        {"document_root": settings.MEDIA_ROOT},
        name="media",
    ),
]

handler404 = custom_404

urlpatterns += [
    re_path(r"^.*$", custom_404, name="custom_404"),
]
