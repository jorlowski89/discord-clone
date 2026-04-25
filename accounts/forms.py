from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Login",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Login"}),
    )
    password = forms.CharField(
        label="Haslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Haslo"}
        ),
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
    )
    username = forms.CharField(
        label="Login",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Login"}),
    )
    bio = forms.CharField(
        label="Opis",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Napisz kilka slow o sobie",
            }
        ),
    )
    password1 = forms.CharField(
        label="Haslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Haslo"}
        ),
    )
    password2 = forms.CharField(
        label="Powtorz haslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Powtorz haslo"}
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "bio")


class ProfileForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ("email", "bio", "avatar")
        widgets = {
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Opis profilu",
                }
            ),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class ProfilePasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Aktualne haslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Aktualne haslo"}
        ),
    )
    new_password1 = forms.CharField(
        label="Nowe haslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Nowe haslo"}
        ),
    )
    new_password2 = forms.CharField(
        label="Powtorz nowe haslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Powtorz nowe haslo"}
        ),
    )
