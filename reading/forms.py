from django import forms

from .models import Book, Category, Tag


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        items = data if isinstance(data, (list, tuple)) else [data]
        return [f for f in (single(d, initial) for d in items) if f]


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "genre", "original_url", "status", "rating",
                  "started_at", "completed_at", "description", "personal_review"]
        widgets = {
            "started_at": forms.DateInput(attrs={"type": "date"}),
            "completed_at": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "personal_review": forms.Textarea(attrs={"rows": 5}),
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
        }


class MemoryForm(forms.Form):
    book = forms.ModelChoiceField(Book.objects.all(), required=False)
    category = forms.ModelChoiceField(Category.objects.all(), required=False)
    dialogue = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}),
                               help_text="The dialogue or passage, typed out (optional).")
    thoughts = forms.CharField(required=False, label="Personal thoughts",
                               widget=forms.Textarea(attrs={"rows": 5}))
    book_url = forms.URLField(required=False, label="Book link")
    tags = forms.CharField(required=False, help_text="Comma separated, e.g. angst, possessive, favourite dialogue")
    favourite = forms.BooleanField(required=False)
    images = MultipleFileField(required=False, label="Screenshots",
                               help_text="PNG, JPG or WEBP. You can pick several.")


def parse_tags(text, kind):
    tags, seen = [], set()
    for raw in (text or "").split(","):
        name = " ".join(raw.split())[:60]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        tag = Tag.objects.filter(kind=kind, name__iexact=name).first() or Tag.objects.create(kind=kind, name=name)
        tags.append(tag)
    return tags
