from django import forms

from .models import Channel, DirectMessage, Message


class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "np. general"}
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Krótki opis kanału",
                }
            ),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("content", "image", "audio")
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control chat-input",
                    "rows": 2,
                    "placeholder": "Napisz wiadomość",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control d-none",
                    "accept": "image/*",
                    "tabindex": "-1",
                }
            ),
            "audio": forms.ClearableFileInput(
                attrs={
                    "class": "form-control d-none",
                    "accept": "audio/*",
                    "tabindex": "-1",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        image = cleaned_data.get("image")
        audio = cleaned_data.get("audio")

        if not content and not image and not audio:
            raise forms.ValidationError("Wpisz tekst albo dodaj plik.")

        return cleaned_data


class DirectMessageForm(forms.ModelForm):
    class Meta:
        model = DirectMessage
        fields = ("content", "image", "audio")
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control chat-input",
                    "rows": 2,
                    "placeholder": "Napisz prywatną wiadomość",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control d-none",
                    "accept": "image/*",
                    "tabindex": "-1",
                }
            ),
            "audio": forms.ClearableFileInput(
                attrs={
                    "class": "form-control d-none",
                    "accept": "audio/*",
                    "tabindex": "-1",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        image = cleaned_data.get("image")
        audio = cleaned_data.get("audio")

        if not content and not image and not audio:
            raise forms.ValidationError("Wpisz tekst albo dodaj plik.")

        return cleaned_data
