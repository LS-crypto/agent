"""会话记忆：多轮对话 messages 管理。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.user.paths import workspace_sessions


class Session:
    """内存中的多轮会话上下文。"""

    def __init__(
        self,
        user_id: str,
        system_prompt: str,
        *,
        persist_json: bool = True,
        messages: list[dict[str, Any]] | None = None,
    ) -> None:
        self.user_id = user_id
        self.system_prompt = system_prompt
        self.persist_json = persist_json
        self.messages: list[dict[str, Any]] = (
            messages
            if messages is not None
            else [{"role": "system", "content": system_prompt}]
        )

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": self.system_prompt}]

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self.messages if m.get("role") == "user")

    def _session_file(self) -> Path:
        return workspace_sessions(self.user_id) / "current.json"

    def save(self) -> None:
        if not self.persist_json:
            return
        path = self._session_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.messages, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> bool:
        if not self.persist_json:
            return False
        path = self._session_file()
        if not path.is_file():
            return False
        self.messages = json.loads(path.read_text(encoding="utf-8"))
        return True
