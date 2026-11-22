"""Backups, verification, restore and exports.

Private content inside archives is already AES-256-GCM ciphertext (diary, dialogues,
thoughts, screenshots). Book titles/authors, tag names and dates are stored as plain
metadata so the archive stays organised and searchable offline.
"""
import base64
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils import timezone

from diary.models import MOOD_LABELS, DiaryEntry
from reading.files import KEY_RE, read_image, screenshots_root
from reading.models import Book, Category, Memory, MemoryImage, Tag

from .crypto import dec_text_safe
from .models import Backup

FILE_RE = re.compile(r"^[0-9a-f]{32}(\.thumb)?\.bin$")
RESTORE_ORDER = ["tags/tags.json", "tags/categories.json", "books/book_metadata.json",
                 "memories/memory_metadata.json", "memories/image_metadata.json", "diary/diary_metadata.json"]


def backup_dir() -> Path:
    p = Path(settings.PRIVATE_STORAGE_ROOT) / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ser(qs):
    return serializers.serialize("json", qs, indent=1).encode()


class _Writer:
    def __init__(self, z):
        self.z, self.files = z, {}

    def add(self, name, data: bytes):
        self.z.writestr(name, data)
        self.files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def build_archive(owner, dest: Path):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        w = _Writer(z)
        images = list(MemoryImage.objects.all())
        entries = list(DiaryEntry.objects.all())
        w.add("books/book_metadata.json", _ser(Book.objects.all()))
        w.add("memories/memory_metadata.json", _ser(Memory.objects.all()))
        w.add("memories/image_metadata.json", _ser(images))
        for img in images:
            for suffix in (".bin", ".thumb.bin"):
                p = screenshots_root() / f"{img.storage_key}{suffix}"
                if p.exists():
                    w.add(f"memories/screenshots/{img.storage_key}{suffix}", p.read_bytes())
        w.add("diary/diary_metadata.json", _ser(entries))
        for e in entries:
            w.add(f"diary/encrypted_entries/{e.pk}.bin", bytes(e.content_enc))
        w.add("tags/tags.json", _ser(Tag.objects.all()))
        w.add("tags/categories.json", _ser(Category.objects.all()))
        b64 = lambda b: base64.b64encode(bytes(b)).decode()
        w.add("security/key_material.json", json.dumps({
            "note": "Wrapped keys: useless without your passphrase or recovery key.",
            "kdf_salt": b64(owner.kdf_salt), "wrapped_master_pw": b64(owner.wrapped_master_pw),
            "wrapped_master_rec": b64(owner.wrapped_master_rec)}, indent=1).encode())
        manifest = {"app": "Velvet Pages", "format": 1, "created": timezone.now().isoformat(),
                    "counts": {"books": Book.objects.count(), "memories": Memory.objects.count(),
                               "screenshots": len(images), "diary_entries": len(entries),
                               "tags": Tag.objects.count(), "categories": Category.objects.count()},
                    "files": w.files}
        z.writestr("export_manifest.json", json.dumps(manifest, indent=1))
    return manifest


def verify_archive(path):
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                return False, f"Corrupt entry in archive: {bad}"
            manifest = json.loads(z.read("export_manifest.json"))
            if manifest.get("app") != "Velvet Pages":
                return False, "Not a Velvet Pages archive."
            for name, meta in manifest["files"].items():
                if hashlib.sha256(z.read(name)).hexdigest() != meta["sha256"]:
                    return False, f"Checksum mismatch: {name}"
        return True, "All checksums match."
    except Exception as exc:
        return False, f"Unreadable archive ({type(exc).__name__})."


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(owner, kind="manual") -> Backup:
    name = f"velvet-{kind}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    path = backup_dir() / name
    b = Backup.objects.create(kind=kind, storage_key=name)
    try:
        build_archive(owner, path)
        ok, msg = verify_archive(path)
        b.size, b.sha256 = path.stat().st_size, _sha256_file(path)
        b.status = "verified" if ok else "failed"
        b.note, b.verified_at = msg, timezone.now()
    except Exception as exc:
        b.status, b.note = "failed", f"Backup failed ({type(exc).__name__})."
    b.save()
    return b


def prune_backups(keep=10):
    for b in Backup.objects.filter(kind__in=["scheduled", "manual"])[keep:]:
        (backup_dir() / b.storage_key).unlink(missing_ok=True)
        b.delete()


def restore_archive(owner, path, restore_keys=False):
    ok, msg = verify_archive(path)
    if not ok:
        raise ValueError(msg)
    safety = create_backup(owner, "pre-restore")       # safety net before wiping anything
    if safety.status != "verified":
        raise ValueError("Could not create the pre-restore safety backup; restore aborted.")
    root = screenshots_root()
    with zipfile.ZipFile(path) as z:
        new_keys = set()
        for name in z.namelist():
            if name.startswith("memories/screenshots/"):
                base = name.rsplit("/", 1)[-1]
                if FILE_RE.match(base):
                    (root / base).write_bytes(z.read(name))
                    new_keys.add(base.split(".")[0])
        old_keys = {i.storage_key for i in MemoryImage.objects.all()}
        with transaction.atomic():
            for model in (DiaryEntry, Memory, Book, Tag, Category):
                model.objects.all().delete()
            for name in RESTORE_ORDER:
                for obj in serializers.deserialize("json", z.read(name).decode()):
                    obj.save()
            if restore_keys:
                k = json.loads(z.read("security/key_material.json"))
                owner.kdf_salt = base64.b64decode(k["kdf_salt"])
                owner.wrapped_master_pw = base64.b64decode(k["wrapped_master_pw"])
                owner.wrapped_master_rec = base64.b64decode(k["wrapped_master_rec"])
                owner.save(update_fields=["kdf_salt", "wrapped_master_pw", "wrapped_master_rec"])
            with connection.cursor() as c:
                for sql in connection.ops.sequence_reset_sql(no_style(), [Book, Category, Tag, Memory, MemoryImage, DiaryEntry]):
                    c.execute(sql)
    for key in old_keys - new_keys:
        for suffix in (".bin", ".thumb.bin"):
            (root / f"{key}{suffix}").unlink(missing_ok=True)
    return safety


def build_readable_export(master) -> bytes:
    """Decrypted, human-readable archive (plain text!). Requires the unlocked vault."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        memories = []
        for m in Memory.objects.select_related("book", "category").prefetch_related("tags", "images"):
            files = []
            for img in m.images.all():
                ext = img.content_type.split("/")[-1].replace("jpeg", "jpg")
                arc = f"screenshots/{img.storage_key}.{ext}"
                try:
                    z.writestr(arc, read_image(master, img.storage_key))
                    files.append(arc)
                except Exception:
                    pass
            memories.append({"id": m.pk, "book": m.book.title if m.book else "", "author": m.book.author if m.book else "",
                             "category": m.category.name if m.category else "", "tags": [t.name for t in m.tags.all()],
                             "dialogue": dec_text_safe(master, m.dialogue_enc), "thoughts": dec_text_safe(master, m.thoughts_enc),
                             "url": m.book_url, "favourite": m.favourite, "created": m.created_at.isoformat(), "screenshots": files})
        z.writestr("memories.json", json.dumps(memories, indent=2, ensure_ascii=False))
        books = [{"title": b.title, "author": b.author, "genre": b.genre, "url": b.original_url, "status": b.get_status_display(),
                  "rating": b.rating, "started": str(b.started_at or ""), "completed": str(b.completed_at or ""),
                  "description": b.description, "review": b.personal_review} for b in Book.objects.all()]
        z.writestr("books.json", json.dumps(books, indent=2, ensure_ascii=False))
        for e in DiaryEntry.objects.prefetch_related("tags"):
            title = dec_text_safe(master, e.title_enc)
            mood = MOOD_LABELS.get(dec_text_safe(master, e.mood_enc), "")
            body = (f"# {title or 'Untitled'}\n\nDate: {e.entry_date}\nMood: {mood}\n"
                    f"Tags: {', '.join(t.name for t in e.tags.all())}\n\n{dec_text_safe(master, e.content_enc)}\n")
            z.writestr(f"diary/{e.entry_date}_{e.pk}.md", body)
        z.writestr("README.txt", "Decrypted export from Velvet Pages. This archive is NOT encrypted - store it safely.\n")
    return buf.getvalue()
