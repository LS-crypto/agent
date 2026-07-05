"""读取 runtime/logs/ 中的用户活动 JSONL。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.user.paths import log_file, logs_dir


def read_user_activity(
    *,
    date_str: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
    events: list[str] | None = None,
) -> list[dict[str, Any]]:
    """读取指定日期/用户的活动事件。"""
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    limit = max(1, min(limit, 500))
    event_set = set(events) if events else None
    rows: list[dict[str, Any]] = []

    if user_id:
        paths = [log_file(user_id, date_str)]
    else:
        day_dir = logs_dir() / date_str
        if not day_dir.is_dir():
            return []
        paths = sorted(day_dir.glob("*.jsonl"))

    for path in paths:
        if not path.is_file():
            continue
        uid = path.stem
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event_set and record.get("event") not in event_set:
                    continue
                record.setdefault("user_id", uid)
                rows.append(record)

    rows.sort(key=lambda r: r.get("time", ""))
    return rows[-limit:]
