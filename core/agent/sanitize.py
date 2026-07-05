"""日志脱敏（S2）：写入 activity JSONL 前移除密钥与敏感片段。"""

from __future__ import annotations

import re
from typing import Any

_SK_PATTERNS = (
    re.compile(r"sk-[a-zA-Z0-9]{8,}", re.IGNORECASE),
    re.compile(r"DASHSCOPE_API_KEY\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9._\-]+", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"github_pat_[a-zA-Z0-9_]{20,}", re.IGNORECASE),
    re.compile(r"BSA[a-zA-Z0-9]{8,}", re.IGNORECASE),
)


def _redact_string(text: str) -> str:
    out = text
    for pat in _SK_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(v) for v in value]
    return value


def sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    return sanitize_value(record)
