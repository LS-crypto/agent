"""用户 API Key 加密存取。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from server.auth.secrets_crypto import decrypt_secret, encrypt_secret
from server.db.database import get_connection

PROVIDER_DASHSCOPE = "dashscope"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def mask_api_key(key: str) -> str:
    key = key.strip()
    if len(key) <= 8:
        return "***"
    return f"{key[:3]}***{key[-4:]}"


class UserSecretsRepository:
    def upsert(self, user_id: str, provider: str, plaintext: str) -> None:
        ciphertext = encrypt_secret(plaintext.strip())
        now = _now()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_secrets (user_id, provider, ciphertext, key_version, updated_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    ciphertext = excluded.ciphertext,
                    key_version = user_secrets.key_version + 1,
                    updated_at = excluded.updated_at
                """,
                (user_id, provider, ciphertext, now),
            )

    def delete(self, user_id: str, provider: str) -> bool:
        with get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM user_secrets WHERE user_id = ? AND provider = ?",
                (user_id, provider),
            )
            return cur.rowcount > 0

    def get_row(self, user_id: str, provider: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT user_id, provider, ciphertext, key_version, updated_at
                FROM user_secrets
                WHERE user_id = ? AND provider = ?
                """,
                (user_id, provider),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def has_secret(self, user_id: str, provider: str = PROVIDER_DASHSCOPE) -> bool:
        return self.get_row(user_id, provider) is not None

    def get_plaintext(self, user_id: str, provider: str = PROVIDER_DASHSCOPE) -> str | None:
        row = self.get_row(user_id, provider)
        if row is None:
            return None
        return decrypt_secret(row["ciphertext"])

    def get_status(self, user_id: str, provider: str = PROVIDER_DASHSCOPE) -> dict[str, Any]:
        row = self.get_row(user_id, provider)
        if row is None:
            return {
                "configured": False,
                "hint": None,
                "updated_at": None,
            }
        plaintext = decrypt_secret(row["ciphertext"])
        return {
            "configured": True,
            "hint": mask_api_key(plaintext),
            "updated_at": row["updated_at"],
        }
