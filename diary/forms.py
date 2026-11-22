from django import forms

from reading.models import Book

from .models import MOODS


class EntryForm(forms.Form):
    title = forms.CharField(required=False, max_length=200)
    entry_date = forms.DateField(label="Date", widget=forms.DateInput(attrs={"type": "date"}))
    mood = forms.ChoiceField(choices=[("", "— no mood —")] + MOODS, required=False)
    content = forms.CharField(label="", widget=forms.Textarea(attrs={"rows": 20, "class": "editor", "autofocus": True,
                                                                      "placeholder": "Write freely. No one can read this but you."}))
    tags = forms.CharField(required=False, help_text="Comma separated, e.g. personal, dreams, self-reflection")
    book = forms.ModelChoiceField(Book.objects.all(), required=False, label="Related book (optional)")
    favourite = forms.BooleanField(required=False)
