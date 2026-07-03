"""简易向量/关键词长期记忆：跨会话检索用户项目上下文。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.paths import RUNTIME_ROOT


def _memory_dir(user_id: str) -> Path:
    path = RUNTIME_ROOT / "memory" / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", text) if len(t) > 1}


class VectorMemory:
    """关键词重叠检索（无 embedding 依赖，便于离线运行）。"""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.path = _memory_dir(user_id) / "entries.jsonl"

    def add(self, content: str, *, tags: list[str] | None = None) -> None:
        record = {"content": content.strip(), "tags": tags or []}
        if not record["content"]:
            return
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scored: list[tuple[float, dict[str, Any]]] = []
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                text = rec.get("content", "")
                overlap = len(q_tokens & _tokenize(text))
                if overlap > 0:
                    scored.append((overlap, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    def format_context(self, query: str) -> str:
        hits = self.search(query)
        if not hits:
            return ""
        lines = ["## 相关历史记忆", ""]
        for h in hits:
            lines.append(f"- {h['content'][:300]}")
        return "\n".join(lines)
