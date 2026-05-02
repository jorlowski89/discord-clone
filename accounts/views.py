from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProfileForm, ProfilePasswordChangeForm, RegisterForm
from .models import User, UserRole
from .decorators import role_required, unblocked_required
from chat.models import Channel, DirectMessage, Message


def home(request):
    context = {}
    if request.user.is_authenticated:
        context["can_claim_admin"] = not User.objects.filter(
            Q(role=UserRole.ADMIN) | Q(is_superuser=True)
        ).exists()
        context["latest_direct_message"] = (
            DirectMessage.objects.select_related(
                "author",
                "conversation",
                "conversation__user_one",
                "conversation__user_two",
            )
            .filter(
                Q(conversation__user_one=request.user)
                | Q(conversation__user_two=request.user),
                is_deleted=False,
            )
            .exclude(author=request.user)
            .order_by("-created_at")
            .first()
        )
        context["latest_channel_message"] = (
            Message.objects.select_related("author", "channel")
            .filter(
                channel__members=request.user,
                is_deleted=False,
            )
            .exclude(author=request.user)
            .order_by("-created_at")
            .first()
        )

    return render(request, "home.html", context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Konto zostalo utworzone.")
            return redirect("home")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@require_POST
@login_required
def claim_first_admin(request):
    has_admin = User.objects.filter(
        Q(role=UserRole.ADMIN) | Q(is_superuser=True)
    ).exists()

    if has_admin:
        messages.error(request, "Administrator zostal juz utworzony.")
        return redirect("home")

    request.user.role = UserRole.ADMIN
    request.user.is_staff = True
    request.user.is_superuser = True
    request.user.save(update_fields=["role", "is_staff", "is_superuser"])
    messages.success(request, "Twoje konto zostalo pierwszym administratorem.")
    return redirect("admin_panel")


@require_POST
@login_required
def logout_view(request):
    request.user.last_seen = None
    request.user.save(update_fields=["last_seen"])
    logout(request)
    return redirect("home")


@login_required
def presence_status(request):
    raw_ids = request.GET.get("ids", "")
    user_ids = []
    for raw_id in raw_ids.split(","):
        if raw_id.strip().isdigit():
            user_ids.append(int(raw_id))

    users = User.objects.filter(id__in=user_ids[:100])
    return JsonResponse(
        {
            "users": [
                {
                    "id": user.id,
                    "online": user.is_online,
                }
                for user in users
            ]
        }
    )


@login_required
def profile_view(request):
    profile_form = ProfileForm(instance=request.user)
    password_form = ProfilePasswordChangeForm(request.user)

    if request.method == "POST":
        if request.user.is_blocked:
            messages.error(request, "Zablokowane konto nie moze edytowac profilu ani hasla.")
            return redirect("profile")

        if request.POST.get("action") == "password":
            password_form = ProfilePasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Haslo zostalo zmienione.")
                return redirect("profile")
        else:
            profile_form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil zostal zapisany.")
                return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "form": profile_form,
            "password_form": password_form,
        },
    )


@role_required(UserRole.MODERATOR, UserRole.ADMIN)
def moderation_panel(request):
    users = User.objects.order_by("username")
    channels = Channel.objects.select_related("created_by").order_by("name")
    selected_user_id = request.GET.get("user")
    selected_channel_id = request.GET.get("channel")
    messages_query = (
        Message.objects.select_related("author", "channel")
        .filter(is_deleted=False)
        .order_by("-created_at")
    )

    if selected_user_id:
        messages_query = messages_query.filter(author_id=selected_user_id)

    if selected_channel_id:
        messages_query = messages_query.filter(channel_id=selected_channel_id)

    return render(
        request,
        "accounts/moderation_panel.html",
        {
            "users": users,
            "channels": channels,
            "messages_list": messages_query,
            "selected_user_id": selected_user_id or "",
            "selected_channel_id": selected_channel_id or "",
        },
    )


@role_required(UserRole.ADMIN)
def admin_panel(request):
    users = User.objects.order_by("username")
    return render(
        request,
        "accounts/admin_panel.html",
        {
            "users": users,
            "role_choices": UserRole.choices,
        },
    )


def user_can_toggle_block(actor, target) -> bool:
    if actor == target:
        return False

    if actor.has_admin_access:
        return True

    return (
        actor.role == UserRole.MODERATOR
        and target.role == UserRole.USER
        and not target.is_superuser
    )


@require_POST
@role_required(UserRole.ADMIN)
@unblocked_required
def update_user_role(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    new_role = request.POST.get("role")

    if new_role not in UserRole.values:
        messages.error(request, "Wybrana rola jest nieprawidlowa.")
        return redirect("admin_panel")

    if user == request.user and new_role != UserRole.ADMIN:
        messages.error(request, "Nie mozesz odebrac sobie roli administratora.")
        return redirect("admin_panel")

    user.role = new_role
    user.save(update_fields=["role"])
    messages.success(request, f"Rola uzytkownika {user.username} zostala zmieniona.")
    return redirect("admin_panel")


@require_POST
@role_required(UserRole.MODERATOR, UserRole.ADMIN)
@unblocked_required
def toggle_user_block(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    next_url = request.POST.get("next") or (
        "admin_panel" if request.user.has_admin_access else "moderation_panel"
    )

    if not user_can_toggle_block(request.user, user):
        messages.error(request, "Nie mozesz zmienic blokady tego uzytkownika.")
        return redirect(next_url)

    user.is_blocked = not user.is_blocked
    user.save(update_fields=["is_blocked"])
    state = "zablokowany" if user.is_blocked else "odblokowany"
    messages.success(request, f"Uzytkownik {user.username} zostal {state}.")
    return redirect(next_url)


@require_POST
@role_required(UserRole.ADMIN)
@unblocked_required
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if user == request.user:
        messages.error(request, "Nie mozesz usunac samego siebie.")
        return redirect("admin_panel")

    username = user.username
    user.delete()
    messages.success(request, f"Uzytkownik {username} zostal usuniety.")
    return redirect("admin_panel")


@require_POST
@role_required(UserRole.MODERATOR, UserRole.ADMIN)
@unblocked_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, pk=message_id, is_deleted=False)
    message.is_deleted = True
    message.save(update_fields=["is_deleted"])
    messages.success(request, "Wiadomosc zostala usunieta.")
    return redirect(request.POST.get("next") or message.channel.get_absolute_url())


@require_POST
@role_required(UserRole.ADMIN)
@unblocked_required
def delete_channel(request, channel_id):
    channel = get_object_or_404(Channel, pk=channel_id)
    channel_name = channel.name
    channel.delete()
    messages.success(request, f"Kanal #{channel_name} zostal usuniety.")
    return redirect("moderation_panel")


def custom_404(request, exception=None):
    return render(request, "404.html", status=404)
