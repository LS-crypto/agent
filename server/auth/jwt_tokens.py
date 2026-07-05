"""JWT 签发与校验。"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

DEFAULT_EXPIRE_HOURS = 168


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if secret:
        return secret
    return "dev-insecure-jwt-secret-change-me"


def _expire_hours() -> int:
    raw = os.getenv("JWT_EXPIRE_HOURS", "").strip()
    if not raw:
        return DEFAULT_EXPIRE_HOURS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_EXPIRE_HOURS


def create_access_token(*, user_id: str, email: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=_expire_hours()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
