from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.crypto import dec_text_safe, enc_text, vault_key
from diary.models import DiaryEntry

from .files import ALLOWED, read_image, remove_image_files, store_image
from .forms import BookForm, MemoryForm, parse_tags
from .models import Book, Category, Memory, MemoryImage, Tag
from .services import filtered_memories, hydrate


# ------------------------------------------------------------------ Reading space
def reading_space(request):
    key = vault_key(request)
    ctx = {
        "memory_count": Memory.objects.count(),
        "book_count": Book.objects.count(),
        "fav_count": Memory.objects.filter(favourite=True).count(),
        "recent": hydrate(list(Memory.objects.select_related("book").prefetch_related("images")[:8]), key),
        "favourites": hydrate(list(Memory.objects.filter(favourite=True).select_related("book")
                                   .prefetch_related("images")[:4]), key),
        "recent_books": Book.objects.order_by("-created_at")[:6],
    }
    return render(request, "reading/space.html", ctx)


# ------------------------------------------------------------------ Memories
def _gallery(request, title, force_fav=False):
    items = filtered_memories(request.GET, vault_key(request), force_fav=force_fav)
    page = Paginator(items, 24).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "reading/memory_list.html", {
        "page": page, "title": title, "total": len(items), "qs": params.urlencode(),
        "books": Book.objects.all(), "tags": Tag.objects.filter(kind="reading"),
        "categories": Category.objects.all(), "force_fav": force_fav, "f": request.GET,
    })


def memory_list(request):
    return _gallery(request, "My Memories")


def favourites(request):
    return _gallery(request, "Favourites", force_fav=True)


def memory_detail(request, pk):
    m = get_object_or_404(Memory.objects.select_related("book", "category").prefetch_related("tags", "images"), pk=pk)
    hydrate([m], vault_key(request))
    return render(request, "reading/memory_detail.html", {"m": m, "link": m.book_url or (m.book.original_url if m.book else "")})


def _save_memory(request, form, memory=None):
    key = vault_key(request)
    d = form.cleaned_data
    stored = []
    try:
        for up in d["images"]:
            stored.append(store_image(key, up))
    except ValidationError as exc:
        for name, _ct in stored:
            remove_image_files(name)
        form.add_error("images", exc)
        return None
    if memory is None:
        memory = Memory()
    memory.book, memory.category = d["book"], d["category"]
    memory.dialogue_enc = enc_text(key, d["dialogue"])
    memory.thoughts_enc = enc_text(key, d["thoughts"])
    memory.book_url, memory.favourite = d["book_url"], d["favourite"]
    memory.save()
    memory.tags.set(parse_tags(d["tags"], "reading"))
    for (name, ctype), up in zip(stored, d["images"]):
        MemoryImage.objects.create(memory=memory, storage_key=name, content_type=ctype, original_name=up.name[:200])
    return memory


def memory_create(request):
    initial = {}
    if request.GET.get("book", "").isdigit():
        initial["book"] = int(request.GET["book"])
    form = MemoryForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        m = _save_memory(request, form)
        if m:
            messages.success(request, "Memory saved.")
            return redirect("memory_detail", pk=m.pk)
    return render(request, "reading/memory_form.html", {"form": form, "title": "Save a memory"})


def memory_edit(request, pk):
    m = get_object_or_404(Memory, pk=pk)
    key = vault_key(request)
    initial = {"book": m.book_id, "category": m.category_id, "book_url": m.book_url, "favourite": m.favourite,
               "dialogue": dec_text_safe(key, m.dialogue_enc), "thoughts": dec_text_safe(key, m.thoughts_enc),
               "tags": ", ".join(t.name for t in m.tags.all())}
    form = MemoryForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        if _save_memory(request, form, memory=m):
            messages.success(request, "Memory updated.")
            return redirect("memory_detail", pk=m.pk)
    return render(request, "reading/memory_form.html",
                  {"form": form, "title": "Edit memory", "memory": m, "images": m.images.all()})


def memory_delete(request, pk):
    m = get_object_or_404(Memory, pk=pk)
    if request.method == "POST":
        for img in m.images.all():
            remove_image_files(img.storage_key)
        m.delete()
        messages.success(request, "Memory deleted.")
        return redirect("memory_list")
    return render(request, "confirm_delete.html", {
        "what": "this memory and its screenshots", "back": "memory_detail", "back_pk": m.pk})


@require_POST
def memory_favourite(request, pk):
    m = get_object_or_404(Memory, pk=pk)
    m.favourite = not m.favourite
    m.save(update_fields=["favourite"])
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("memory_detail", pk=pk)


def memory_image(request, pk):
    img = get_object_or_404(MemoryImage, pk=pk)
    thumb = request.GET.get("thumb") == "1"
    try:
        data = read_image(vault_key(request), img.storage_key, thumb=thumb)
    except FileNotFoundError:
        raise Http404
    except Exception:
        return HttpResponse("Could not decrypt image.", status=500)
    resp = HttpResponse(data, content_type="image/jpeg" if thumb else img.content_type)
    if request.GET.get("download") == "1":
        resp["Content-Disposition"] = f'attachment; filename="{img.original_name or "screenshot"}"'
    return resp


@require_POST
def memory_image_delete(request, pk):
    img = get_object_or_404(MemoryImage, pk=pk)
    memory_pk = img.memory_id
    remove_image_files(img.storage_key)
    img.delete()
    messages.success(request, "Screenshot removed.")
    return redirect("memory_edit", pk=memory_pk)


# ------------------------------------------------------------------ Books
def book_list(request):
    qs = Book.objects.annotate(n=Count("memories"))
    q, status = request.GET.get("q", "").strip(), request.GET.get("status", "")
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(author__icontains=q) | qs.filter(genre__icontains=q)
    if status:
        qs = qs.filter(status=status)
    return render(request, "reading/book_list.html", {"books": qs.distinct(), "statuses": Book.STATUS, "f": request.GET})


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    key = vault_key(request)
    memories = hydrate(list(book.memories.prefetch_related("images", "tags")), key)
    entries = list(DiaryEntry.objects.filter(book=book).order_by("-entry_date"))
    for e in entries:
        e.title = dec_text_safe(key, e.title_enc) or "Untitled entry"
    return render(request, "reading/book_detail.html", {"book": book, "memories": memories, "entries": entries})


def book_create(request):
    form = BookForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        b = form.save()
        messages.success(request, "Book added.")
        return redirect("book_detail", pk=b.pk)
    return render(request, "reading/book_form.html", {"form": form, "title": "Add a book"})


def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk)
    form = BookForm(request.POST or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Book updated.")
        return redirect("book_detail", pk=pk)
    return render(request, "reading/book_form.html", {"form": form, "title": f"Edit: {book.title}"})


def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    n = book.memories.count()
    if request.method == "POST":
        if request.POST.get("delete_memories") == "on":
            for m in book.memories.all():
                for img in m.images.all():
                    remove_image_files(img.storage_key)
                m.delete()
        book.delete()  # memories (if kept) just lose the book link
        messages.success(request, "Book deleted.")
        return redirect("book_list")
    return render(request, "confirm_delete.html", {
        "what": f"the book “{book.title}”", "back": "book_detail", "back_pk": pk,
        "extra_checkbox": f"Also permanently delete its {n} saved memor{'y' if n == 1 else 'ies'}" if n else "",
        "note": "By default the memories are kept and simply unlinked from this book."})


# ------------------------------------------------------------------ Tags & categories
def taxonomy(request):
    if request.method == "POST":
        action, name = request.POST.get("action", ""), " ".join(request.POST.get("name", "").split())
        obj_id = request.POST.get("id", "")
        kind = request.POST.get("kind", "reading")
        try:
            if action == "add_tag" and name:
                Tag.objects.get_or_create(name=name[:60], kind=kind if kind in ("reading", "diary") else "reading")
            elif action == "rename_tag" and name and obj_id.isdigit():
                Tag.objects.filter(pk=obj_id).update(name=name[:60])
            elif action == "delete_tag" and obj_id.isdigit():
                Tag.objects.filter(pk=obj_id).delete()
            elif action == "add_cat" and name:
                Category.objects.get_or_create(name=name[:80])
            elif action == "rename_cat" and name and obj_id.isdigit():
                Category.objects.filter(pk=obj_id).update(name=name[:80])
            elif action == "delete_cat" and obj_id.isdigit():
                Category.objects.filter(pk=obj_id).delete()
            messages.success(request, "Done.")
        except Exception:
            messages.error(request, "That name already exists.")
        return redirect("taxonomy")
    return render(request, "reading/taxonomy.html", {
        "reading_tags": Tag.objects.filter(kind="reading").annotate(n=Count("memories")),
        "diary_tags": Tag.objects.filter(kind="diary").annotate(n=Count("diary_entries")),
        "categories": Category.objects.annotate(n=Count("memories")),
    })
