"""
Encryption at rest (AES-256-GCM via the `cryptography` library).

Diary text, dialogues, thoughts and screenshots are stored as ciphertext. The key is created
automatically the first time it is needed and kept in  private_storage/data.key
(or in the VELVET_DATA_KEY environment variable). You never have to type or remember it.

Keep data.key safe: without it, existing encrypted data cannot be read.
"""
import base64
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

NONCE_LEN = 12
TAG_LEN = 16
_cache = {}


class DecryptionError(Exception):
    pass


def data_key() -> bytes:
    env_key = os.environ.get("VELVET_DATA_KEY")
    if env_key:
        key = base64.urlsafe_b64decode(env_key.encode())
        if len(key) != 32:
            raise RuntimeError("VELVET_DATA_KEY must be 32 bytes, urlsafe-base64 encoded.")
        return key
    path = Path(settings.PRIVATE_STORAGE_ROOT) / "data.key"
    key = _cache.get(path)
    if key is None:
        if path.exists():
            key = path.read_bytes()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            key = os.urandom(32)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
        _cache[path] = key
    return key


def vault_key(request=None) -> bytes:
    """Kept under this name so the rest of the code needs no changes."""
    return data_key()


def seal(key: bytes, data: bytes) -> bytes:
    nonce = os.urandom(NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, data, None)


def open_sealed(key: bytes, blob) -> bytes:
    blob = bytes(blob)
    if len(blob) < NONCE_LEN + TAG_LEN:
        raise DecryptionError("blob too short")
    try:
        return AESGCM(key).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], None)
    except InvalidTag as exc:
        raise DecryptionError("authentication failed") from exc


def enc_text(key: bytes, text: str) -> bytes:
    return seal(key, text.encode("utf-8")) if text else b""


def dec_text(key: bytes, blob) -> str:
    blob = bytes(blob) if blob else b""
    return open_sealed(key, blob).decode("utf-8") if blob else ""


def dec_text_safe(key: bytes, blob) -> str:
    try:
        return dec_text(key, blob)
    except DecryptionError:
        return "[unreadable — wrong key or corrupted data]"