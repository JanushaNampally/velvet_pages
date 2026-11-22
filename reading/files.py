"""Encrypted screenshot storage on private disk (never exposed by a public URL)."""
import io
import re
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image

from core.crypto import open_sealed, seal

Image.MAX_IMAGE_PIXELS = 60_000_000
ALLOWED = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"), "WEBP": ("image/webp", "webp")}
KEY_RE = re.compile(r"^[0-9a-f]{32}$")


def screenshots_root() -> Path:
    p = Path(settings.PRIVATE_STORAGE_ROOT) / "screenshots"
    p.mkdir(parents=True, exist_ok=True)
    return p


def store_image(master: bytes, upload):
    if upload.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError(f"{upload.name}: file is larger than {settings.MAX_UPLOAD_BYTES // 1048576} MB.")
    raw = upload.read()
    try:
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
        img.verify()
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise ValidationError(f"{upload.name}: not a valid image.")
    if fmt not in ALLOWED:
        raise ValidationError(f"{upload.name}: only PNG, JPG and WEBP are supported.")
    thumb = img.copy()
    thumb.thumbnail((480, 640))
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, "JPEG", quality=80)
    name = uuid.uuid4().hex
    root = screenshots_root()
    (root / f"{name}.bin").write_bytes(seal(master, raw))
    (root / f"{name}.thumb.bin").write_bytes(seal(master, buf.getvalue()))
    return name, ALLOWED[fmt][0]


def read_image(master: bytes, storage_key: str, thumb=False) -> bytes:
    if not KEY_RE.match(storage_key):
        raise FileNotFoundError
    path = screenshots_root() / (f"{storage_key}.thumb.bin" if thumb else f"{storage_key}.bin")
    return open_sealed(master, path.read_bytes())


def remove_image_files(storage_key: str):
    if not KEY_RE.match(storage_key):
        return
    for suffix in (".bin", ".thumb.bin"):
        (screenshots_root() / f"{storage_key}{suffix}").unlink(missing_ok=True)
