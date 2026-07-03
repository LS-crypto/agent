"""编程 Agent CLI 入口：终端仅显示问答，详细过程写入 runtime/logs/。"""

from __future__ import annotations

import argparse
import json

from core.agent.coding_agent import CodingAgent
from core.models.sync import list_agent_models
from core.skills.loader import discover_skills
from core.tools.policy import build_confirmation_detail


def _cli_confirm_handler(auto_yes: bool):
    def handler(tool: str, args: dict) -> bool:
        if auto_yes:
            return True
        detail = build_confirmation_detail(tool, args)
        sev = detail.get("severity", "medium")
        print(f"\n[需确认·{sev}] {tool}")
        print(f"  摘要: {detail['summary']}")
        print(f"  说明: {detail['explanation'].replace('<strong>', '').replace('</strong>', '').replace('<code>', '').replace('</code>', '')}")
        print(f"  影响: {detail['impact']}")
        if tool == "write_file":
            preview = str(args.get("content", ""))[:300]
            if preview:
                print(f"  内容预览: {preview}{'…' if len(str(args.get('content', ''))) > 300 else ''}")
        elif tool == "execute_command":
            print(f"  命令: {args.get('command', '')}")
        else:
            print(f"  参数: {json.dumps(args, ensure_ascii=False)[:200]}")
        ans = input("允许？(y/N): ").strip().lower()
        return ans in ("y", "yes")

    return handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Sheldon 编程 Agent CLI")
    parser.add_argument("--user", "-u", default="default", help="用户 ID")
    parser.add_argument("--reset", action="store_true", help="清空会话记忆")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="在终端显示工具调用等详细过程（默认仅写日志）",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="自动允许所有 review 级工具（开发用，跳过终端确认）",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="模型 id 或 auto（默认 auto，启用复杂度路由）",
    )
    parser.add_argument(
        "--permission", "-p",
        default=None,
        choices=["conservative", "balanced", "permissive"],
        help="权限档位：conservative 保守 / balanced 平衡 / permissive 宽松",
    )
    parser.add_argument(
        "--skills",
        action="store_true",
        help="列出可用 Skills 并退出",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="列出 Agent 可用模型目录并退出",
    )
    args = parser.parse_args()

    if args.skills:
        print("Sheldon Agent Skills（Agent 可 list_skills / use_skill 调用）:\n")
        for s in discover_skills():
            desc = (s.description or "")[:80]
            print(f"  {s.name:24} {desc}")
        print("\n用法: 在对话中说「加载 disk-storage 技能」或让 Agent 调用 use_skill")
        return 0

    if args.list_models:
        data = list_agent_models(check_remote=False)
        print("Sheldon Agent 模型目录（静态择优，不含 embedding/图像等）:\n")
        for m in data["models"]:
            mark = ""
            if m["id"] == data["auto_model_id"]:
                mark = " [路由]"
            elif m.get("is_default"):
                mark = " [默认]"
            avail = "" if m.get("available", True) else " (账号未开通)"
            print(f"  {m['id']:22} {m['label']}{mark}{avail}")
            print(f"    {m['group']} · {m.get('description', '')}")
        print(f"\n用法: uv run python -m apps.cli --model qwen3.7-plus")
        return 0

    confirm_handler = _cli_confirm_handler(args.yes)

    agent = CodingAgent(
        user_id=args.user,
        resume=not args.reset,
        verbose=args.verbose,
    )
    if args.reset:
        agent.reset()
        agent.start_session()

    mode = "自动确认 review 工具" if args.yes else "review 工具需终端确认"
    model_hint = args.model or "auto（自动路由）"
    perm_hint = args.permission or "balanced（默认）"
    print(
        f"Agent 就绪 | 模型: {model_hint} | 权限: {perm_hint} | {mode} | "
        f"详细日志: runtime/logs/ | exit 退出 | /reset 清空会话"
    )

    try:
        while True:
            try:
                user_input = input("\nYou> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
                break
            if user_input.lower() == "/reset":
                agent.reset()
                agent.start_session()
                print("Agent> 会话已重置。")
                continue

            reply = agent.chat(
                user_input,
                confirm_handler=confirm_handler,
                session_id="cli",
                model=args.model,
                permission=args.permission,
            )
            print(f"\nAgent> {reply}")

    finally:
        agent.end_session()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
