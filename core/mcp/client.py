"""外部 HTTP API 客户端：超时、JSON、日志脱敏。"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20

_SENSITIVE_HEADERS = frozenset(
    {"authorization", "x-subscription-token", "x-api-key", "api-key"}
)


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _SENSITIVE_HEADERS:
            out[k] = "***"
        else:
            out[k] = v
    return out


def _redact_url(url: str) -> str:
    return re.sub(r"(token=|key=)[^&]+", r"\1***", url, flags=re.I)


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any] | str]:
    """发起 HTTP 请求，返回 (status_code, parsed_json 或 raw_text)。"""
    hdrs = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
    logger.debug(
        "mcp http %s %s headers=%s",
        method.upper(),
        _redact_url(url),
        _redact_headers(hdrs),
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read().decode("utf-8", errors="replace") if e.fp else str(e.reason)
    except urllib.error.URLError as e:
        return 0, {"success": False, "error": str(e.reason)}

    try:
        parsed: dict[str, Any] | str = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = raw

    return status, parsed


def http_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any] | str]:
    return http_request("GET", url, headers=headers, timeout=timeout)


def http_post(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, Any] | str]:
    return http_request("POST", url, headers=headers, body=body, timeout=timeout)
