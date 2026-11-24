import re
from datetime import date

from django import forms

USERNAME_RE = re.compile(r"^(?=.*[A-Za-z])[A-Za-z0-9_.]{3,30}$")


class SetupForm(forms.Form):
    username = forms.CharField(min_length=3, max_length=30, help_text="Letters, numbers, _ and . only")
    date_of_birth = forms.DateField(label="Date of birth", widget=forms.DateInput(attrs={"type": "date"}))
    password = forms.CharField(min_length=8, label="Password (8+ characters)", widget=forms.PasswordInput)
    confirm = forms.CharField(label="Repeat password", widget=forms.PasswordInput)
    setup_token = forms.CharField(required=False, label="Setup token", widget=forms.PasswordInput)

    def __init__(self, *args, require_token=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not require_token:
            del self.fields["setup_token"]

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if not USERNAME_RE.match(u):
            raise forms.ValidationError("Use 3–30 letters, numbers, _ or . (at least one letter).")
        return u

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        today = date.today()
        if dob >= today or dob.year < today.year - 120:
            raise forms.ValidationError("Enter a valid date of birth.")
        return dob

    def clean(self):
        d = super().clean()
        if d.get("password") != d.get("confirm"):
            raise forms.ValidationError("Passwords do not match.")
        return d


class LoginForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="Username or email",
                                 widget=forms.TextInput(attrs={"autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))