import calendar as pycal
from datetime import date, datetime

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.crypto import dec_text_safe, enc_text, vault_key
from reading.forms import parse_tags, pick_tags
from reading.models import Tag

from .forms import EntryForm
from .models import MOOD_LABELS, MOODS, DiaryEntry


def hydrate(entries, key):
    for e in entries:
        e.title = dec_text_safe(key, e.title_enc)
        e.content = dec_text_safe(key, e.content_enc)
        e.mood = dec_text_safe(key, e.mood_enc)
        e.mood_label = MOOD_LABELS.get(e.mood, "")
        e.words = len(e.content.split())
        e.chars = len(e.content)
    return entries


def filter_entries(params, key):
    qs = DiaryEntry.objects.select_related("book").prefetch_related("tags")
    try:
        if params.get("date"):
            qs = qs.filter(entry_date=datetime.strptime(params["date"], "%Y-%m-%d").date())
    except ValueError:
        pass
    if params.get("tag", "").isdigit():
        qs = qs.filter(tags__id=int(params["tag"]))
    if params.get("fav") == "1":
        qs = qs.filter(favourite=True)
    items = hydrate(list(qs.distinct()), key)
    if params.get("mood"):
        items = [e for e in items if e.mood == params["mood"]]
    q = (params.get("q") or "").strip().lower()
    if q:
        items = [e for e in items if q in " ".join(
            [e.title, e.content, e.mood_label, e.entry_date.isoformat()] + [t.name for t in e.tags.all()]).lower()]
    return items


def diary_home(request):
    key = vault_key(request)
    items = filter_entries(request.GET, key)
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "diary/home.html", {
        "page": page, "total": len(items), "qs": params.urlencode(), "f": request.GET,
        "moods": MOODS, "tags": Tag.objects.filter(kind="diary"),
        "previews": request.user.diary_previews, "today": date.today()})


def _save(request, form, entry=None):
    key, d = vault_key(request), form.cleaned_data
    entry = entry or DiaryEntry()
    entry.title_enc, entry.content_enc = enc_text(key, d["title"]), enc_text(key, d["content"])
    entry.mood_enc = enc_text(key, d["mood"])
    entry.entry_date, entry.favourite, entry.book = d["entry_date"], d["favourite"], d["book"]
    entry.save()
    entry.tags.set(pick_tags(request.user, "diary", d["tag_choices"], d["tags"]))
    return entry


def entry_create(request):
    try:
        start = datetime.strptime(request.GET.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        start = date.today()
    form = EntryForm(request.POST or None, initial={"entry_date": start})
    if request.method == "POST" and form.is_valid():
        e = _save(request, form)
        messages.success(request, "Entry saved.")
        return redirect("entry_detail", pk=e.pk)
    return render(request, "diary/entry_form.html", {"form": form, "title": "New entry"})

@require_POST
def quick_entry(request):
    """One-box note from the dashboard: saved straight into today's diary."""
    text = request.POST.get("content", "").strip()
    if text:
        DiaryEntry.objects.create(owner=request.user, content_enc=enc_text(vault_key(request), text),
                                  entry_date=date.today())
        messages.success(request, "Saved to today's diary.")
    else:
        messages.error(request, "Write something first.")
    return redirect("dashboard")

def entry_edit(request, pk):
    e = get_object_or_404(DiaryEntry, pk=pk)
    key = vault_key(request)
    initial = {"title": dec_text_safe(key, e.title_enc), "content": dec_text_safe(key, e.content_enc),
               "mood": dec_text_safe(key, e.mood_enc), "entry_date": e.entry_date, "book": e.book_id,
                              "favourite": e.favourite, "tag_choices": [str(t.pk) for t in e.tags.all()]}
    form = EntryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        _save(request, form, entry=e)
        messages.success(request, "Entry updated.")
        return redirect("entry_detail", pk=pk)
    return render(request, "diary/entry_form.html", {"form": form, "title": "Edit entry", "entry": e})


def entry_detail(request, pk):
    e = get_object_or_404(DiaryEntry.objects.select_related("book").prefetch_related("tags"), pk=pk)
    hydrate([e], vault_key(request))
    return render(request, "diary/entry_detail.html", {"e": e})


def entry_delete(request, pk):
    e = get_object_or_404(DiaryEntry, pk=pk)
    if request.method == "POST":
        e.delete()
        messages.success(request, "Entry deleted.")
        return redirect("diary_home")
    return render(request, "confirm_delete.html", {"what": "this diary entry", "back": "entry_detail", "back_pk": pk})


@require_POST
def entry_favourite(request, pk):
    e = get_object_or_404(DiaryEntry, pk=pk)
    e.favourite = not e.favourite
    e.save(update_fields=["favourite"])
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("entry_detail", pk=pk)


def calendar_view(request):
    today = date.today()
    try:
        year, month = int(request.GET.get("y", today.year)), int(request.GET.get("m", today.month))
        date(year, month, 1)
    except ValueError:
        year, month = today.year, today.month
    counts = {r["entry_date"].day: r["c"] for r in
              DiaryEntry.objects.filter(entry_date__year=year, entry_date__month=month)
              .values("entry_date").annotate(c=Count("id"))}
    weeks = [[{"day": d, "iso": date(year, month, d).isoformat() if d else "", "count": counts.get(d, 0),
               "today": d and date(year, month, d) == today} for d in week]
             for week in pycal.Calendar(firstweekday=0).monthdayscalendar(year, month)]
    py, pm = (year, month - 1) if month > 1 else (year - 1, 12)
    ny, nm = (year, month + 1) if month < 12 else (year + 1, 1)
    return render(request, "diary/calendar.html", {
        "weeks": weeks, "month_name": pycal.month_name[month], "year": year,
        "prev": f"?y={py}&m={pm}", "next": f"?y={ny}&m={nm}", "total": sum(counts.values()),
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]})
