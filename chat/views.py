from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ChannelForm, MessageForm
from .models import Channel


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
