from django import forms


class SetupForm(forms.Form):
    display_name = forms.CharField(max_length=80, label="Your name")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=25, label="Phone number (with country code)",
                            widget=forms.TextInput(attrs={"placeholder": "+91 98765 43210"}))
    password = forms.CharField(min_length=8, label="Password (8+ characters)", widget=forms.PasswordInput)
    confirm = forms.CharField(label="Repeat password", widget=forms.PasswordInput)
    setup_token = forms.CharField(required=False, label="Setup token", widget=forms.PasswordInput)

    def __init__(self, *args, require_token=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not require_token:
            del self.fields["setup_token"]

    def clean(self):
        d = super().clean()
        if d.get("password") != d.get("confirm"):
            raise forms.ValidationError("Passwords do not match.")
        return d


class LoginForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="Email or phone number",
                                 widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class CodeForm(forms.Form):
    code = forms.CharField(min_length=6, max_length=6, label="6-digit code",
                           widget=forms.TextInput(attrs={"autofocus": True, "inputmode": "numeric", "autocomplete": "one-time-code"}))


class ForgotForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="Your email or phone number",
                                 widget=forms.TextInput(attrs={"autofocus": True}))


class ResetForm(forms.Form):
    code = forms.CharField(min_length=6, max_length=6, label="6-digit code sent to your phone",
                           widget=forms.TextInput(attrs={"autofocus": True, "inputmode": "numeric"}))
    new_password = forms.CharField(min_length=8, label="New password (8+ characters)", widget=forms.PasswordInput)
    confirm = forms.CharField(label="Repeat new password", widget=forms.PasswordInput)

    def clean(self):
        d = super().clean()
        if d.get("new_password") != d.get("confirm"):
            raise forms.ValidationError("Passwords do not match.")
        return d