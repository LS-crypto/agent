"""编程 Agent CLI 入口：终端流式输出 + 多会话 + 工具可视化。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from core.agent.coding_agent import CodingAgent
from core.models.sync import list_agent_models
from core.skills.loader import discover_skills
from core.tools.policy import build_confirmation_detail


# ── 终端颜色 ──────────────────────────────────────────────

class C:
    """ANSI 颜色（Windows 10+ / PowerShell 原生支持）。\033[0m 重置。\033[90m 暗灰。\033[36m 青色。\033[33m 黄色。\033[32m 绿色。\033[31m 红色。\033[1m 加粗。\033[2m 暗色。"""
    R = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREY = "\033[90m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    BLUE = "\033[34m"


# ── 会话管理 ──────────────────────────────────────────────

CLI_SESSIONS_DIR = Path(os.environ.get("SHELLDON_CLI_SESSIONS", "")) or (
    Path(__file__).resolve().parents[2] / "runtime" / "cli_sessions"
)


def _cli_session_path(session_name: str) -> Path:
    CLI_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return CLI_SESSIONS_DIR / f"{session_name}.json"


def _list_cli_sessions() -> list[dict]:
    if not CLI_SESSIONS_DIR.exists():
        return []
    sessions = []
    for f in sorted(CLI_SESSIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "name": f.stem,
                "messages": len(data.get("messages", [])),
                "updated": data.get("updated_at", f.stat().st_mtime),
            })
        except Exception:
            pass
    return sessions


def _delete_cli_session(name: str) -> bool:
    p = _cli_session_path(name)
    if p.exists():
        p.unlink()
        return True
    return False


# ── 确认处理器 ──────────────────────────────────────────────

def _cli_confirm_handler(auto_yes: bool, show_tools: bool):
    def handler(tool: str, args: dict) -> bool:
        if auto_yes:
            return True
        detail = build_confirmation_detail(tool, args)
        sev = detail.get("severity", "medium")
        color = C.YELLOW if sev == "high" else C.CYAN
        print(f"\n{color}[需确认·{sev}]{C.R} {C.BOLD}{tool}{C.R}")
        print(f"  {C.DIM}摘要:{C.R} {detail['summary']}")
        print(f"  {C.DIM}说明:{C.R} {detail['explanation'].replace('<strong>', '').replace('</strong>', '').replace('<code>', '').replace('</code>', '')}")
        print(f"  {C.DIM}影响:{C.R} {detail['impact']}")
        if tool == "write_file":
            preview = str(args.get("content", ""))[:300]
            if preview:
                print(f"  {C.DIM}内容预览:{C.R} {preview}{'…' if len(str(args.get('content', ''))) > 300 else ''}")
        elif tool == "execute_command":
            print(f"  {C.DIM}命令:{C.R} {args.get('command', '')}")
        else:
            print(f"  {C.DIM}参数:{C.R} {json.dumps(args, ensure_ascii=False)[:200]}")
        ans = input(f"\n{C.GREEN}允许？(y/N):{C.R} ").strip().lower()
        return ans in ("y", "yes")

    return handler


# ── 工具调用显示 ──────────────────────────────────────────────

def _make_tool_display_callback(show_tools: bool):
    """返回 on_event 回调，用于在终端实时显示工具调用。"""
    if not show_tools:
        return None

    def on_event(record: dict) -> None:
        ev = record.get("event")
        if ev == "tool_call":
            name = record.get("tool", "?")
            args = record.get("args", {})
            # 精简显示
            arg_summary = ""
            if "file_path" in args:
                arg_summary = args["file_path"]
            elif "command" in args:
                arg_summary = args["command"][:80]
            elif "query" in args:
                arg_summary = args["query"][:80]
            else:
                arg_summary = json.dumps(args, ensure_ascii=False)[:80]
            print(f"\n{C.CYAN}⚙ {name}{C.R} {C.DIM}{arg_summary}{C.R}")
        elif ev == "tool_result":
            ok = record.get("success", False)
            name = record.get("tool", "?")
            status = f"{C.GREEN}✓{C.R}" if ok else f"{C.RED}✗{C.R}"
            print(f"  {status} {C.DIM}{name} 完成{C.R}")

    return on_event


# ── 流式文本打印 ──────────────────────────────────────────────

def _make_stream_printer():
    """返回 (printer, finish, reset) 三元组。"""
    started = [False]

    def printer(chunk: str) -> None:
        if not started[0]:
            print(f"\n{C.BOLD}Agent>{C.R} ", end="", flush=True)
            started[0] = True
        print(chunk, end="", flush=True)

    def finish() -> None:
        if started[0]:
            print()  # 换行
            started[0] = False

    def reset() -> None:
        started[0] = False

    return printer, finish, reset


# ── 命令处理 ──────────────────────────────────────────────

def _handle_command(cmd: str, agent: CodingAgent, current_session: list[str]) -> str | None:
    """处理 / 命令。返回 None 表示已处理，返回字符串表示要发送给 Agent 的文本。"""
    parts = cmd.strip().split(maxsplit=1)
    name = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if name in ("/new",):
        session_name = arg.strip() or f"session-{len(_list_cli_sessions()) + 1}"
        agent.reset()
        agent.start_session()
        current_session.clear()
        current_session.append(session_name)
        print(f"{C.GREEN}✓ 新会话: {session_name}{C.R}")
        return None

    elif name in ("/list", "/ls"):
        sessions = _list_cli_sessions()
        if not sessions:
            print(f"{C.DIM}暂无历史会话{C.R}")
        else:
            print(f"\n{C.BOLD}历史会话:{C.R}")
            for i, s in enumerate(sessions, 1):
                mark = f" {C.GREEN}← 当前{C.R}" if s["name"] == (current_session[0] if current_session else "") else ""
                print(f"  {C.DIM}{i:>3}.{C.R} {s['name']}{C.DIM}  ({s['messages']} 条消息){C.R}{mark}")
        return None

    elif name in ("/switch", "/sw"):
        if not arg.strip():
            print(f"{C.YELLOW}用法: /switch <会话名>{C.R}")
            return None
        target = arg.strip()
        p = _cli_session_path(target)
        if not p.exists():
            print(f"{C.RED}✗ 会话不存在: {target}{C.R}")
            return None
        agent.reset()
        agent.start_session()
        current_session.clear()
        current_session.append(target)
        print(f"{C.GREEN}✓ 切换到: {target}{C.R}")
        return None

    elif name in ("/delete", "/rm", "/del"):
        if not arg.strip():
            print(f"{C.YELLOW}用法: /delete <会话名>{C.R}")
            return None
        if _delete_cli_session(arg.strip()):
            print(f"{C.GREEN}✓ 已删除: {arg.strip()}{C.R}")
        else:
            print(f"{C.RED}✗ 会话不存在: {arg.strip()}{C.R}")
        return None

    elif name in ("/reset",):
        agent.reset()
        agent.start_session()
        print(f"{C.GREEN}✓ 会话已重置{C.R}")
        return None

    elif name in ("/models",):
        data = list_agent_models(check_remote=False)
        print(f"\n{C.BOLD}可用模型:{C.R}")
        for m in data["models"]:
            mark = ""
            if m["id"] == data["auto_model_id"]:
                mark = f" {C.CYAN}[路由]{C.R}"
            elif m.get("is_default"):
                mark = f" {C.GREEN}[默认]{C.R}"
            avail = "" if m.get("available", True) else f" {C.RED}(未开通){C.R}"
            print(f"  {m['id']:22} {m['label']}{mark}{avail}")
            print(f"    {C.DIM}{m['group']} · {m.get('description', '')}{C.R}")
        return None

    elif name in ("/skills",):
        print(f"\n{C.BOLD}可用 Skills:{C.R}")
        for s in discover_skills():
            desc = (s.description or "")[:80]
            print(f"  {C.CYAN}{s.name:24}{C.R} {desc}")
        return None

    elif name in ("/help", "/?", "help"):
        _print_help()
        return None

    elif name in ("/exit", "/quit", "exit", "quit"):
        return "__EXIT__"

    else:
        print(f"{C.RED}未知命令: {name}，输入 /help 查看帮助{C.R}")
        return None


def _print_help() -> None:
    print(f"""
{C.BOLD}命令列表:{C.R}
  {C.CYAN}/new [名称]{C.R}      新建会话
  {C.CYAN}/list{C.R}            列出所有会话
  {C.CYAN}/switch <名称>{C.R}   切换会话
  {C.CYAN}/delete <名称>{C.R}   删除会话
  {C.CYAN}/reset{C.R}           重置当前会话
  {C.CYAN}/models{C.R}          查看可用模型
  {C.CYAN}/skills{C.R}          查看可用 Skills
  {C.CYAN}/image <路径>{C.R}    附加图片（发送时一起提交）
  {C.CYAN}/help{C.R}            显示帮助
  {C.CYAN}/exit{C.R}            退出

{C.DIM}直接输入文字即可对话，支持多轮上下文。{C.R}
""")


# ── 主循环 ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sheldon 编程 Agent CLI — 流式输出 · 多会话 · 工具可视化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  sheldon                          # 启动交互模式
  sheldon --model qwen3.7-plus     # 指定模型
  sheldon --yes                    # 自动确认所有工具
  sheldon --tools                  # 显示工具调用过程
  sheldon "帮我写一个快速排序"      # 单次提问模式
        """,
    )
    parser.add_argument("--user", "-u", default="default", help="用户 ID")
    parser.add_argument("--reset", action="store_true", help="清空会话记忆")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志（模型路由、压缩等）",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="自动允许所有 review 级工具（跳过终端确认）",
    )
    parser.add_argument(
        "--tools", "-t",
        action="store_true",
        help="实时显示工具调用过程",
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
    parser.add_argument(
        "--image", "-i",
        action="append",
        default=[],
        help="附加图片路径（可多次指定）",
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="单次提问（不进入交互模式）",
    )
    args = parser.parse_args()

    # ── 快捷命令 ──
    if args.skills:
        print("Sheldon Agent Skills（Agent 可 list_skills / use_skill 调用）:\n")
        for s in discover_skills():
            desc = (s.description or "")[:80]
            print(f"  {C.CYAN}{s.name:24}{C.R} {desc}")
        print("\n用法: 在对话中说「加载 disk-storage 技能」或让 Agent 调用 use_skill")
        return 0

    if args.list_models:
        data = list_agent_models(check_remote=False)
        print("Sheldon Agent 模型目录（静态择优，不含 embedding/图像等）:\n")
        for m in data["models"]:
            mark = ""
            if m["id"] == data["auto_model_id"]:
                mark = f" {C.CYAN}[路由]{C.R}"
            elif m.get("is_default"):
                mark = f" {C.GREEN}[默认]{C.R}"
            avail = "" if m.get("available", True) else f" {C.RED}(账号未开通){C.R}"
            print(f"  {m['id']:22} {m['label']}{mark}{avail}")
            print(f"    {C.DIM}{m['group']} · {m.get('description', '')}{C.R}")
        print(f"\n用法: sheldon --model qwen3.7-plus")
        return 0

    # ── 初始化 Agent ──
    confirm_handler = _cli_confirm_handler(args.yes, args.tools)
    tool_callback = _make_tool_display_callback(args.tools)
    stream_print, stream_finish, stream_reset = _make_stream_printer()

    agent = CodingAgent(
        user_id=args.user,
        resume=not args.reset,
        verbose=args.verbose,
    )
    if args.reset:
        agent.reset()
        agent.start_session()

    # 当前会话名
    current_session: list[str] = ["default"]

    # ── 单次提问模式 ──
    if args.question:
        pending_images = _load_images(args.image)
        reply = agent.chat(
            args.question,
            confirm_handler=confirm_handler,
            on_event=tool_callback,
            session_id="cli",
            model=args.model,
            permission=args.permission,
            text_callback=stream_print,
            images=pending_images or None,
        )
        stream_finish()
        print(f"\n{C.DIM}— 单次提问完成 —{C.R}")
        return 0

    # ── 交互模式 ─
    mode = "自动确认" if args.yes else "需确认"
    model_hint = args.model or "auto（自动路由）"
    perm_hint = args.permission or "balanced"
    tools_hint = "工具可视化开" if args.tools else "工具可视化关"
    print(
        f"\n{C.BOLD}Sheldon Agent{C.R} 就绪"
        f" | 模型: {C.CYAN}{model_hint}{C.R}"
        f" | 权限: {perm_hint}"
        f" | {mode}"
        f" | {tools_hint}"
        f"\n{C.DIM}输入 /help 查看命令 | exit 退出{C.R}\n"
    )

    pending_images: list[str] = []

    try:
        while True:
            try:
                # 图片提示
                img_hint = ""
                if pending_images:
                    img_hint = f" {C.YELLOW}[{len(pending_images)} 张图片待发送]{C.R}"
                user_input = input(f"{C.GREEN}You>{C.R}{img_hint} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{C.DIM}— 再见 —{C.R}")
                break

            if not user_input:
                continue

            # 处理命令
            if user_input.startswith("/"):
                # /image 特殊处理
                if user_input.lower().startswith("/image"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print(f"{C.YELLOW}用法: /image <图片路径>{C.R}")
                        continue
                    img_path = parts[1].strip()
                    p = Path(img_path)
                    if not p.exists():
                        print(f"{C.RED}✗ 文件不存在: {img_path}{C.R}")
                        continue
                    if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                        print(f"{C.RED}✗ 不支持的格式: {p.suffix}（仅支持 jpg/png/gif/webp）{C.R}")
                        continue
                    import base64
                    data = base64.b64encode(p.read_bytes()).decode("ascii")
                    mime = _guess_mime(p.suffix)
                    pending_images.append(f"data:{mime};base64,{data}")
                    print(f"{C.GREEN}✓ 已添加: {p.name}{C.R}")
                    continue

                result = _handle_command(user_input, agent, current_session)
                if result == "__EXIT__":
                    break
                continue

            # 发送消息
            images_to_send = pending_images[:] if pending_images else None
            pending_images.clear()

            stream_reset()
            reply = agent.chat(
                user_input,
                confirm_handler=confirm_handler,
                on_event=tool_callback,
                session_id="cli",
                model=args.model,
                permission=args.permission,
                text_callback=stream_print,
                images=images_to_send,
            )
            stream_finish()

    finally:
        agent.end_session()

    return 0


def _load_images(paths: list[str]) -> list[str]:
    """从文件路径加载 base64 图片列表。"""
    import base64
    result = []
    for p_str in paths:
        p = Path(p_str)
        if not p.exists():
            print(f"{C.RED}✗ 图片不存在: {p_str}{C.R}", file=sys.stderr)
            continue
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        mime = _guess_mime(p.suffix)
        result.append(f"data:{mime};base64,{data}")
    return result


def _guess_mime(suffix: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(suffix.lower(), "image/jpeg")


if __name__ == "__main__":
    raise SystemExit(main())
