"""会话级工具调用速率限制（内存）。"""

from __future__ import annotations

import time
from collections import defaultdict

from core.tools.policy import policy_error

PER_MINUTE = 30
PER_HOUR = 100


class ToolRateLimiter:
    def __init__(self) -> None:
        self._minute: dict[str, list[float]] = defaultdict(list)
        self._hour: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> None:
        self._minute[key] = [t for t in self._minute[key] if now - t < 60]
        self._hour[key] = [t for t in self._hour[key] if now - t < 3600]

    def check(self, key: str) -> dict | None:
        now = time.time()
        self._prune(key, now)
        if len(self._minute[key]) >= PER_MINUTE:
            return policy_error("工具调用过于频繁，请稍后再试（每分钟上限）", "rate_limit")
        if len(self._hour[key]) >= PER_HOUR:
            return policy_error("工具调用过于频繁，请稍后再试（每小时上限）", "rate_limit")
        return None

    def record(self, key: str) -> None:
        now = time.time()
        self._prune(key, now)
        self._minute[key].append(now)
        self._hour[key].append(now)


_default_limiter = ToolRateLimiter()


def get_rate_limiter() -> ToolRateLimiter:
    return _default_limiter
