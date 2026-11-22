from datetime import datetime

from core.crypto import dec_text_safe

from .models import Memory


def hydrate(memories, key):
    for m in memories:
        m.dialogue = dec_text_safe(key, m.dialogue_enc)
        m.thoughts = dec_text_safe(key, m.thoughts_enc)
    return memories


def _date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def filtered_memories(params, key, force_fav=False):
    qs = Memory.objects.select_related("book", "category").prefetch_related("tags", "images")
    for field, lookup in (("book", "book_id"), ("tag", "tags__id"), ("category", "category_id")):
        v = params.get(field, "")
        if v.isdigit():
            qs = qs.filter(**{lookup: int(v)})
    if params.get("author"):
        qs = qs.filter(book__author__icontains=params["author"])
    if params.get("genre"):
        qs = qs.filter(book__genre__icontains=params["genre"])
    if force_fav or params.get("fav") == "1":
        qs = qs.filter(favourite=True)
    if (d := _date(params.get("date_from"))):
        qs = qs.filter(created_at__date__gte=d)
    if (d := _date(params.get("date_to"))):
        qs = qs.filter(created_at__date__lte=d)
    items = hydrate(list(qs.distinct()), key)
    q = (params.get("q") or "").strip().lower()
    if q:
        def hay(m):
            parts = [m.dialogue, m.thoughts, m.book_url,
                     m.book.title if m.book else "", m.book.author if m.book else "",
                     m.category.name if m.category else ""] + [t.name for t in m.tags.all()]
            return " ".join(parts).lower()
        items = [m for m in items if q in hay(m)]
    return items
