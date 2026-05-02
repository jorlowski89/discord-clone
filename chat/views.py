from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import unblocked_required
from .forms import ChannelForm, DirectMessageForm, MessageForm
from .models import (
    REACTION_CHOICES,
    Channel,
    DirectConversation,
    DirectMessage,
    DirectMessageReaction,
    Message,
    MessageReaction,
)
from .realtime import broadcast_channel_message, broadcast_direct_message


User = get_user_model()


def attach_reaction_summary(messages_list, user):
    for message in messages_list:
        reactions = list(message.reactions.select_related("author"))
        summary = []
        for emoji, _label in REACTION_CHOICES:
            matching = [reaction for reaction in reactions if reaction.emoji == emoji]
            summary.append(
                {
                    "emoji": emoji,
                    "count": len(matching),
                    "user_reacted": any(
                        reaction.author_id == user.id for reaction in matching
                    ),
                }
            )
        message.reaction_summary = summary
    return messages_list


@login_required
def channel_list(request):
    query = (request.GET.get("q") or "").strip()
    channels = Channel.objects.prefetch_related("members")
    if query:
        channels = channels.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    joined_channel_ids = set(request.user.channels.values_list("id", flat=True))
    return render(
        request,
        "chat/channel_list.html",
        {
            "channels": channels,
            "joined_channel_ids": joined_channel_ids,
            "query": query,
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
            messages.success(request, "Kanał został utwórzony.")
            return redirect(channel)
    else:
        form = ChannelForm()

    return render(request, "chat/channel_form.html", {"form": form})


@login_required
@unblocked_required
def channel_join(request, slug):
    channel = get_object_or_404(Channel, slug=slug)
    channel.members.add(request.user)
    messages.success(request, f"Dołączono do kanału #{channel.name}.")
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
            messages.error(request, "Twoje konto jest zablokowane i nie może pisac.")
            return redirect(channel)

        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.channel = channel
            message.author = request.user
            message.save()
            broadcast_channel_message(message)
            return redirect(channel)
    else:
        form = MessageForm()

    messages_list = list(
        channel.messages.select_related("author")
        .prefetch_related("reactions")
        .filter(is_deleted=False)
        .order_by("created_at")
    )
    attach_reaction_summary(messages_list, request.user)
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
    query = (request.GET.get("q") or "").strip()
    conversations = (
        DirectConversation.objects.select_related("user_one", "user_two")
        .filter(Q(user_one=request.user) | Q(user_two=request.user))
        .order_by("-created_at")
    )
    if query:
        conversations = conversations.filter(
            Q(user_one=request.user, user_two__username__icontains=query)
            | Q(user_two=request.user, user_one__username__icontains=query)
            | Q(user_one=request.user, user_two__email__icontains=query)
            | Q(user_two=request.user, user_one__email__icontains=query)
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
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(bio__icontains=query)
        )
    return render(
        request,
        "chat/direct_list.html",
        {
            "conversation_items": conversation_items,
            "users": users,
            "query": query,
        },
    )


@login_required
@unblocked_required
@require_POST
def direct_conversation_start(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)

    if other_user == request.user:
        messages.error(request, "Nie możesz zacząć rozmówy z samym sobą.")
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
        messages.error(request, "Nie masz dostępu do tej rozmówy.")
        return redirect("direct_conversation_list")

    other_user = conversation.other_user(request.user)

    if request.method == "POST":
        if request.user.is_blocked:
            messages.error(request, "Twoje konto jest zablokowane i nie może pisac.")
            return redirect(conversation)

        form = DirectMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.author = request.user
            message.save()
            broadcast_direct_message(message)
            return redirect(conversation)
    else:
        form = DirectMessageForm()

    messages_list = list(
        conversation.messages.select_related("author")
        .prefetch_related("reactions")
        .filter(is_deleted=False)
        .order_by("created_at")
    )
    attach_reaction_summary(messages_list, request.user)
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


@login_required
@unblocked_required
@require_POST
def toggle_message_reaction(request, message_id):
    message = get_object_or_404(
        Message,
        pk=message_id,
        is_deleted=False,
        channel__members=request.user,
    )
    emoji = request.POST.get("emoji")
    if emoji not in dict(REACTION_CHOICES):
        messages.error(request, "Nieznana reakcja.")
        return redirect(message.channel)

    reaction, created = MessageReaction.objects.get_or_create(
        message=message,
        author=request.user,
        emoji=emoji,
    )
    if not created:
        reaction.delete()

    return redirect(request.POST.get("next") or message.channel.get_absolute_url())


@login_required
@unblocked_required
@require_POST
def toggle_direct_message_reaction(request, message_id):
    message = get_object_or_404(
        DirectMessage.objects.select_related("conversation"),
        pk=message_id,
        is_deleted=False,
    )
    if not message.conversation.includes(request.user):
        messages.error(request, "Nie masz dostępu do tej rozmówy.")
        return redirect("direct_conversation_list")

    emoji = request.POST.get("emoji")
    if emoji not in dict(REACTION_CHOICES):
        messages.error(request, "Nieznana reakcja.")
        return redirect(message.conversation)

    reaction, created = DirectMessageReaction.objects.get_or_create(
        message=message,
        author=request.user,
        emoji=emoji,
    )
    if not created:
        reaction.delete()

    return redirect(request.POST.get("next") or message.conversation.get_absolute_url())
