from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import unblocked_required
from .forms import ChannelForm, DirectMessageForm, MessageForm
from .models import Channel, DirectConversation


User = get_user_model()


@login_required
def channel_list(request):
    channels = Channel.objects.prefetch_related("members")
    joined_channel_ids = set(request.user.channels.values_list("id", flat=True))
    return render(
        request,
        "chat/channel_list.html",
        {
            "channels": channels,
            "joined_channel_ids": joined_channel_ids,
        },
    )


@login_required
@unblocked_required
def channel_create(request):
    if request.method == "POST":
        form = ChannelForm(request.POST)
        if form.is_valid():
            channel = form.save(commit=False)
            channel.created_by = request.user
            channel.save()
            channel.members.add(request.user)
            messages.success(request, "Kanal zostal utworzony.")
            return redirect(channel)
    else:
        form = ChannelForm()

    return render(request, "chat/channel_form.html", {"form": form})


@login_required
@unblocked_required
def channel_join(request, slug):
    channel = get_object_or_404(Channel, slug=slug)
    channel.members.add(request.user)
    messages.success(request, f"Dolaczono do kanalu #{channel.name}.")
    return redirect(channel)


@login_required
def channel_detail(request, slug):
    channel = get_object_or_404(
        Channel.objects.prefetch_related("members").select_related("created_by"),
        slug=slug,
    )
    is_member = channel.members.filter(pk=request.user.pk).exists()

    if not is_member:
        return render(
            request,
            "chat/channel_detail.html",
            {
                "channel": channel,
                "is_member": False,
                "messages_list": [],
                "form": None,
            },
        )

    if request.method == "POST":
        if request.user.is_blocked:
            messages.error(request, "Twoje konto jest zablokowane i nie moze pisac.")
            return redirect(channel)

        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.channel = channel
            message.author = request.user
            message.save()
            return redirect(channel)
    else:
        form = MessageForm()

    messages_list = (
        channel.messages.select_related("author")
        .filter(is_deleted=False)
        .order_by("created_at")
    )
    return render(
        request,
        "chat/channel_detail.html",
        {
            "channel": channel,
            "is_member": True,
            "messages_list": messages_list,
            "form": form,
        },
    )


@login_required
def direct_conversation_list(request):
    conversations = (
        DirectConversation.objects.select_related("user_one", "user_two")
        .filter(Q(user_one=request.user) | Q(user_two=request.user))
        .order_by("-created_at")
    )
    conversation_items = []
    for conversation in conversations:
        conversation_items.append(
            {
                "conversation": conversation,
                "other_user": conversation.other_user(request.user),
                "latest_message": conversation.messages.filter(is_deleted=False)
                .select_related("author")
                .order_by("-created_at")
                .first(),
            }
        )

    users = User.objects.exclude(pk=request.user.pk).order_by("username")
    return render(
        request,
        "chat/direct_list.html",
        {
            "conversation_items": conversation_items,
            "users": users,
        },
    )


@login_required
@unblocked_required
@require_POST
def direct_conversation_start(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)

    if other_user == request.user:
        messages.error(request, "Nie mozesz zaczac rozmowy z samym soba.")
        return redirect("direct_conversation_list")

    conversation, _created = DirectConversation.get_or_create_between(
        request.user,
        other_user,
    )
    return redirect(conversation)


@login_required
def direct_conversation_detail(request, pk):
    conversation = get_object_or_404(
        DirectConversation.objects.select_related("user_one", "user_two"),
        pk=pk,
    )
    if not conversation.includes(request.user):
        messages.error(request, "Nie masz dostepu do tej rozmowy.")
        return redirect("direct_conversation_list")

    other_user = conversation.other_user(request.user)

    if request.method == "POST":
        if request.user.is_blocked:
            messages.error(request, "Twoje konto jest zablokowane i nie moze pisac.")
            return redirect(conversation)

        form = DirectMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.author = request.user
            message.save()
            return redirect(conversation)
    else:
        form = DirectMessageForm()

    messages_list = (
        conversation.messages.select_related("author")
        .filter(is_deleted=False)
        .order_by("created_at")
    )
    return render(
        request,
        "chat/direct_detail.html",
        {
            "conversation": conversation,
            "other_user": other_user,
            "messages_list": messages_list,
            "form": form,
        },
    )
