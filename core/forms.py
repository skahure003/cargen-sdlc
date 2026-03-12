from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "Choose a username for your requester account.",
            "email": "Enter your work email address.",
            "password1": "Create a password.",
            "password2": "Repeat the password to confirm it.",
        }
        for field_name, placeholder in placeholders.items():
            self.fields[field_name].widget.attrs["placeholder"] = placeholder

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
