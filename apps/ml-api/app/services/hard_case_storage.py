"""Opt-in encrypted storage of hard cases for the next training iteration.

This module is **disabled by default**. It only activates when:

1. ``Settings.hard_case_storage_enabled`` is true; and
2. ``Settings.hard_case_key`` decodes to a 32-byte AES-256 key.

Until that, :func:`store_hard_case` becomes a no-op so the request path is
unaffected. Enabling it requires a documented legal/UX review (see
``docs/PRIVACY.md`` §"Cuándo se almacenan imágenes").

File layout: each case is written as ``<case_id>.bin`` in
``Settings.hard_case_storage_dir``. The first 12 bytes are the AES-GCM nonce,
followed by ciphertext+tag.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StoredCase:
    case_id: str
    path: Path


def _load_key(b64: str | None) -> bytes | None:
    if not b64:
        return None
    try:
        key = base64.b64decode(b64, validate=True)
    except Exception:  # noqa: BLE001
        return None
    if len(key) != 32:
        return None
    return key


def is_enabled(settings: Settings) -> bool:
    return bool(settings.hard_case_storage_enabled) and _load_key(settings.hard_case_key) is not None


def store_hard_case(image_bytes: bytes, settings: Settings) -> StoredCase | None:
    """Encrypt and persist ``image_bytes``. Returns ``None`` if disabled."""
    if not is_enabled(settings):
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        logger.warning("hard_case_storage_missing_cryptography")
        return None

    key = _load_key(settings.hard_case_key)
    assert key is not None  # is_enabled checked

    out_dir = Path(settings.hard_case_storage_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    case_id = uuid.uuid4().hex
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, image_bytes, associated_data=case_id.encode("utf-8"))
    out = out_dir / f"{case_id}.bin"
    out.write_bytes(nonce + ciphertext)
    logger.info("hard_case_stored", case_id=case_id, bytes=len(image_bytes))
    return StoredCase(case_id=case_id, path=out)


def load_hard_case(case_id: str, settings: Settings) -> bytes | None:
    """Inverse of :func:`store_hard_case`. Used by the offline review tool."""
    if not is_enabled(settings):
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    key = _load_key(settings.hard_case_key)
    assert key is not None
    path = Path(settings.hard_case_storage_dir) / f"{case_id}.bin"
    if not path.is_file():
        return None
    blob = path.read_bytes()
    nonce, payload = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, payload, associated_data=case_id.encode("utf-8"))
