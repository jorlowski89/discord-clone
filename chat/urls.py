from django.urls import path

from . import views

urlpatterns = [
    path("", views.channel_list, name="channel_list"),
    path("new/", views.channel_create, name="channel_create"),
    path("<slug:slug>/", views.channel_detail, name="channel_detail"),
    path("<slug:slug>/join/", views.channel_join, name="channel_join"),
]
