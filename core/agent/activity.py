"""用户活动记录：详细过程写入 runtime/logs/，终端默认不输出。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any

from core.agent.console import answer, out, step, tool, tool_result, warn
from core.agent.sanitize import sanitize_record
from core.user.paths import admin_dir, log_file, logs_dir
from core.paths import RUNTIME_ROOT

SUMMARY_PATH = admin_dir() / "activity_summary.json"


class ActivityLogger:
    """记录 Agent 活动到 JSONL；mirror_console=True 时同步打印到终端。"""

    def __init__(
        self,
        user_id: str,
        *,
        mirror_console: bool = False,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.user_id = user_id
        self.mirror_console = mirror_console
        self.on_event = on_event
        self._date_str = datetime.now().strftime("%Y-%m-%d")

    def _log_path(self) -> Path:
        path = log_file(self.user_id, self._date_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def log_event(self, event: str, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = sanitize_record(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "user_id": self.user_id,
                "event": event,
                **fields,
            }
        )
        with self._log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        try:
            from server.services.activity_bus import publish

            publish(record)
        except Exception:
            pass
        if self.mirror_console:
            self._mirror(record)
        if self.on_event:
            self.on_event(record)
        return record

    def _mirror(self, record: dict[str, Any]) -> None:
        event = record["event"]
        t = record.get("time", "")

        if event == "session_start":
            step("会话开始", f"用户 {self.user_id} 启动 Agent（{t}）")
        elif event == "user_message":
            out(f"[用户消息] {record.get('content', '')}", f"{t} 用户输入")
        elif event == "loop_round":
            out(
                f"[第 {record.get('round')} 轮] 请求模型",
                f"工具数 {record.get('tool_count')}（{t}）",
            )
        elif event == "model_tool_decision":
            out(
                f"[模型决策] 调用 {record.get('count')} 个工具",
                f"{t} 模型返回 tool_calls",
            )
        elif event == "tool_call":
            tool(
                record.get("tool", "?"),
                record.get("args") or {},
                f"{t} Agent 调用工具",
            )
        elif event == "tool_result":
            preview = str(record.get("preview", ""))[:200]
            tool_result(preview, f"{t} 工具完成 success={record.get('success')}")
        elif event == "assistant_reply":
            preview = str(record.get("content", ""))[:200]
            answer(preview, f"{t} 模型最终回复")
        elif event == "error":
            warn(record.get("message", ""), f"{t} 发生错误")
        elif event == "session_end":
            step("会话结束", f"用户 {self.user_id} 结束会话（{t}）")
        else:
            out(json.dumps(record, ensure_ascii=False), f"{t} 事件：{event}")

    def session_start(self) -> None:
        self.log_event("session_start")

    def user_message(self, content: str) -> None:
        self.log_event("user_message", content=content)

    def loop_round(self, round_num: int, tool_count: int) -> None:
        self.log_event("loop_round", round=round_num, tool_count=tool_count)

    def model_tool_decision(self, count: int) -> None:
        self.log_event("model_tool_decision", count=count)

    def tool_call(self, name: str, args: dict[str, Any]) -> None:
        self.log_event("tool_call", tool=name, args=args)

    def tool_result_event(self, success: bool, result: str) -> None:
        self.log_event(
            "tool_result",
            success=success,
            result=result,
            preview=result[:300],
        )

    def assistant_reply(self, content: str) -> None:
        self.log_event("assistant_reply", content=content)

    def error(self, message: str) -> None:
        self.log_event("error", message=message)

    def session_end(self) -> None:
        self.log_event("session_end")


def refresh_activity_summary(date_str: str | None = None) -> Path:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    day_dir = logs_dir() / date_str
    summary: dict[str, Any] = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "date": date_str,
        "users": {},
    }

    if day_dir.is_dir():
        for log_path in sorted(day_dir.glob("*.jsonl")):
            user_id = log_path.stem
            events: list[dict[str, Any]] = []
            with log_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            summary["users"][user_id] = {
                "log_file": str(log_path.relative_to(RUNTIME_ROOT)),
                "event_count": len(events),
                "last_event": events[-1]["event"] if events else None,
                "last_time": events[-1]["time"] if events else None,
            }

    admin_dir().mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return SUMMARY_PATH
