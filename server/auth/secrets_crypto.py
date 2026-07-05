"""用户 API Key 加密存储（AES-GCM）。"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LEN = 12


def _master_secret() -> str:
    secret = os.getenv("MASTER_SECRET", "").strip()
    if secret:
        return secret
    return "dev-insecure-master-secret-change-me"


def _derive_key() -> bytes:
    return hashlib.sha256(_master_secret().encode("utf-8")).digest()


def encrypt_secret(plaintext: str) -> str:
    aesgcm = AESGCM(_derive_key())
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(blob: str) -> str:
    raw = base64.b64decode(blob)
    nonce, ciphertext = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
    aesgcm = AESGCM(_derive_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
