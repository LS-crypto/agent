"""大总管：在终端查看用户活动日志（带中文注释）。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.agent.activity import refresh_activity_summary
from core.agent.console import answer, out, step, warn
from core.paths import PROJECT_ROOT, RUNTIME_ROOT
from core.user.paths import log_file, logs_dir


def _event_label(record: dict) -> tuple[str, str]:
    """将 JSONL 记录转为终端行 + 中文说明。"""
    event = record.get("event", "?")
    t = record.get("time", "")
    user_id = record.get("user_id", "?")

    if event == "session_start":
        return f"[会话开始] 用户 {user_id}", f"{t} 用户启动 Agent"
    if event == "user_message":
        return f"[用户消息] {record.get('content', '')}", f"{t} 用户发送消息"
    if event == "loop_round":
        return (
            f"[第 {record.get('round')} 轮] 请求模型",
            f"{t} 共 {record.get('tool_count')} 个工具",
        )
    if event == "model_tool_decision":
        return (
            f"[模型决策] 调用 {record.get('count')} 个工具",
            f"{t} 返回 tool_calls",
        )
    if event == "tool_call":
        args = json.dumps(record.get("args") or {}, ensure_ascii=False)
        return f"[工具] {record.get('tool')}({args})", f"{t} Agent 调用工具"
    if event == "tool_result":
        text = str(record.get("result", record.get("preview", "")))[:200]
        ok = record.get("success")
        return f"[工具结果] {text}", f"{t} 工具返回，success={ok}"
    if event == "assistant_reply":
        content = str(record.get("content", ""))[:120]
        return f"[回复] {content}", f"{t} 模型最终回复"
    if event == "error":
        return f"[错误] {record.get('message', '')}", f"{t} 执行出错"
    if event == "session_end":
        return f"[会话结束] 用户 {user_id}", f"{t} 用户结束会话"
    return json.dumps(record, ensure_ascii=False), f"{t} 未知事件类型：{event}"


def view_logs(user_id: str | None, date_str: str) -> int:
    day_dir = logs_dir() / date_str
    if not day_dir.is_dir():
        warn(f"目录不存在：{day_dir}", "该日期尚无用户活动记录")
        return 1

    files = sorted(day_dir.glob("*.jsonl"))
    if user_id:
        files = [day_dir / f"{user_id}.jsonl"]

    if not files or not any(f.is_file() for f in files):
        warn("未找到日志文件", f"日期={date_str}，用户={user_id or '全部'}")
        return 1

    step("大总管视图", f"读取 runtime/logs/{date_str}/ 下的活动记录")
    total = 0

    for path in files:
        if not path.is_file():
            continue
        out(f"--- 日志文件: {path.relative_to(RUNTIME_ROOT)} ---", "以下为该用户当日全部事件")
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                text, note = _event_label(record)
                out(text, note)
                total += 1

    answer(f"共 {total} 条活动记录", "大总管查看完毕")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="大总管：查看用户 Agent 活动日志")
    parser.add_argument("--user", "-u", help="指定用户 ID，默认查看当日全部用户")
    parser.add_argument(
        "--date", "-d",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="日期 YYYY-MM-DD，默认今天",
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="刷新 admin/activity_summary.json 汇总文件",
    )
    args = parser.parse_args()

    if args.summary:
        path = refresh_activity_summary(args.date)
        step("更新汇总", f"已写入 {path.relative_to(PROJECT_ROOT)}")
        out(path.read_text(encoding="utf-8")[:500], "activity_summary.json 内容预览")

    return view_logs(args.user, args.date)


if __name__ == "__main__":
    raise SystemExit(main())
