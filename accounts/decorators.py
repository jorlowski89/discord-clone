from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            is_allowed = request.user.role in allowed_roles
            if "admin" in allowed_roles and request.user.is_superuser:
                is_allowed = True

            if not is_allowed:
                messages.error(request, "Nie masz uprawnien do tej sekcji.")
                return redirect("home")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def unblocked_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_blocked:
            messages.error(request, "Twoje konto jest zablokowane. Ta akcja jest niedostepna.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapped
