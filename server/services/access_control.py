"""J3：注册上限与全站并发聊天限制。"""

from __future__ import annotations

import os
import threading

_lock = threading.Lock()
_global_active = 0
_active_by_user: dict[str, int] = {}


class RegistrationCapError(PermissionError):
    """注册人数已达上限。"""


class ConcurrencyLimitError(PermissionError):
    """全站并发对话已满。"""


def max_registered_users() -> int:
    raw = os.getenv("MAX_REGISTERED_USERS", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def max_concurrent_chats() -> int:
    raw = os.getenv("MAX_CONCURRENT_CHATS", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def check_registration_allowed(current_count: int) -> None:
    cap = max_registered_users()
    if cap > 0 and current_count >= cap:
        raise RegistrationCapError("注册人数已达上限，请联系管理员")


class ChatConcurrencyGuard:
    """在 stream_chat 生命周期内占用一个并发槽位。"""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._acquired = False

    def __enter__(self) -> ChatConcurrencyGuard:
        cap = max_concurrent_chats()
        if cap <= 0:
            return self

        global _global_active
        with _lock:
            if _global_active >= cap:
                raise ConcurrencyLimitError(
                    f"当前在线对话较多，请稍后再试（上限 {cap}）"
                )
            _global_active += 1
            _active_by_user[self.user_id] = _active_by_user.get(self.user_id, 0) + 1
            self._acquired = True
        return self

    def __exit__(self, *_args: object) -> None:
        if not self._acquired:
            return

        global _global_active
        with _lock:
            _global_active = max(0, _global_active - 1)
            remaining = _active_by_user.get(self.user_id, 1) - 1
            if remaining <= 0:
                _active_by_user.pop(self.user_id, None)
            else:
                _active_by_user[self.user_id] = remaining
