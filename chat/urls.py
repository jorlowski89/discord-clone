from django.urls import path

from . import views

urlpatterns = [
    path("", views.channel_list, name="channel_list"),
    path("new/", views.channel_create, name="channel_create"),
    path("dm/", views.direct_conversation_list, name="direct_conversation_list"),
    path(
        "dm/start/<int:user_id>/",
        views.direct_conversation_start,
        name="direct_conversation_start",
    ),
    path(
        "dm/<int:pk>/",
        views.direct_conversation_detail,
        name="direct_conversation_detail",
    ),
    path(
        "dm/messages/<int:message_id>/react/",
        views.toggle_direct_message_reaction,
        name="toggle_direct_message_reaction",
    ),
    path(
        "messages/<int:message_id>/react/",
        views.toggle_message_reaction,
        name="toggle_message_reaction",
    ),
    path("<slug:slug>/", views.channel_detail, name="channel_detail"),
    path("<slug:slug>/join/", views.channel_join, name="channel_join"),
]
