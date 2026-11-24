import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from diary.models import DiaryEntry
from diary.views import filter_entries
from reading.models import Book, Memory
from reading.services import filtered_memories, hydrate

from . import backup as bk
from .crypto import vault_key
from .models import Backup


def dashboard(request):
    key = vault_key(request)
    recent_dates = list(DiaryEntry.objects.values("entry_date").annotate(c=Count("id")).order_by("-entry_date")[:6])
    last_backup = Backup.objects.filter(status="verified").first()
    return render(request, "core/dashboard.html", {
        "today": timezone.localdate(),
        "memory_count": Memory.objects.count(), "book_count": Book.objects.count(),
        "fav_count": Memory.objects.filter(favourite=True).count(),
        "recent_memories": hydrate(list(Memory.objects.select_related("book").prefetch_related("images")[:6]), key),
        "favourites": hydrate(list(Memory.objects.filter(favourite=True).select_related("book").prefetch_related("images")[:4]), key),
        "diary_count": DiaryEntry.objects.count(),
        "last_entry": DiaryEntry.objects.order_by("-entry_date").values_list("entry_date", flat=True).first(),
        "recent_dates": recent_dates, "last_backup": last_backup,
        "backup_stale": not last_backup or (timezone.now() - last_backup.created_at).days >= 7,
    })


def search(request):
    q = request.GET.get("q", "").strip()
    scope = request.GET.get("scope", "all")
    key = vault_key(request)
    reading = diary = []
    if q:
        if scope in ("all", "reading"):
            reading = filtered_memories({"q": q}, key)[:40]
        if scope in ("all", "diary"):
            diary = filter_entries({"q": q}, key)[:40]
    return render(request, "core/search.html", {"q": q, "scope": scope, "reading": reading, "diary": diary})


def settings_view(request):
    owner = request.user
    via_google = request.session.get("auth_via") == "google"
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "prefs":
            owner.diary_previews = request.POST.get("diary_previews") == "on"
            owner.save(update_fields=["diary_previews"])
            messages.success(request, "Saved.")
        elif action == "password":
            cur, new, conf = (request.POST.get(k, "") for k in ("current", "new", "confirm"))
            if not via_google and not owner.check_password(cur):
                messages.error(request, "Current password is incorrect.")
            elif len(new) < 8 or new != conf:
                messages.error(request, "New password must match and be at least 8 characters.")
            else:
                owner.set_password(new)
                owner.save(update_fields=["password"])
                update_session_auth_hash(request, owner)   # keeps you logged in
                messages.success(request, "Password changed.")
        return redirect("settings")
    return render(request, "core/settings.html", {"via_google": via_google})
# ------------------------------------------------------------------ backups
def backup_home(request):
    return render(request, "core/backup.html", {"backups": Backup.objects.all()[:30]})


@require_POST
def backup_create(request):
    b = bk.create_backup(request.user, "manual")
    (messages.success if b.status == "verified" else messages.error)(
        request, "Backup created and verified." if b.status == "verified" else f"Backup failed: {b.note}")
    bk.prune_backups(20)
    return redirect("backup_home")


def _backup_path(pk):
    b = get_object_or_404(Backup, pk=pk)
    path = bk.backup_dir() / b.storage_key
    if not path.exists():
        raise Http404
    return b, path


def backup_download(request, pk):
    b, path = _backup_path(pk)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=b.storage_key)


@require_POST
def backup_verify(request, pk):
    b, path = _backup_path(pk)
    ok, msg = bk.verify_archive(path)
    b.status, b.note, b.verified_at = ("verified" if ok else "failed"), msg, timezone.now()
    b.save()
    (messages.success if ok else messages.error)(request, msg)
    return redirect("backup_home")


@require_POST
def backup_export(request):
    b = bk.create_backup(request.user, "export")
    if b.status != "verified":
        messages.error(request, f"Export failed: {b.note}")
        return redirect("backup_home")
    return FileResponse(open(bk.backup_dir() / b.storage_key, "rb"), as_attachment=True, filename=b.storage_key)


@require_POST
def backup_export_readable(request):
    if not request.user.check_password(request.POST.get("password", "")):
        messages.error(request, "Password incorrect — readable export not created.")
        return redirect("backup_home")
    data = bk.build_readable_export(vault_key(request))
    resp = HttpResponse(data, content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="velvet-readable-{timezone.localdate()}.zip"'
    return resp


@require_POST
def backup_restore(request):
    up = request.FILES.get("archive")
    if not up or request.POST.get("confirm") != "on":
        messages.error(request, "Choose an archive and tick the confirmation box.")
        return redirect("backup_home")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        for chunk in up.chunks():
            tmp.write(chunk)
    try:
        bk.restore_archive(request.user, tmp.name)
    except Exception as exc:
        messages.error(request, f"Restore failed: {exc}")
        return redirect("backup_home")
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    messages.success(request, "Restore complete. (A pre-restore safety backup was saved.)")
    return redirect("dashboard")