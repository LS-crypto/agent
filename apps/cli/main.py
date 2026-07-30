"""编程 Agent CLI 入口：终端流式输出 + 多会话 + 工具可视化。

同步 web 端能力：
  - 双 Provider LLM（DeepSeek / MiniMax）按 model 自动取 key
  - 优先 Web BYOK → 环境变量 fallback
  - 会话软删除（.archived/ 子目录）+ /restore
  - /rollback（撤回最后一轮 user/assistant）
  - /login /logout /whoami 连 web 后端拉 Key
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from apps.cli import auth as cli_auth
from apps.cli import sessions as cli_sessions
from core.agent.coding_agent import CodingAgent
from core.config import (
    get_api_key_env_for_provider,
    get_provider_for_model,
)
from core.models.sync import list_agent_models
from core.skills.loader import discover_skills
from core.tools.policy import build_confirmation_detail


# ── 终端颜色 ──────────────────────────────────────────────

class C:
    """ANSI 颜色（Windows 10+ / PowerShell 原生支持）。"""
    R = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREY = "\033[90m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    BLUE = "\033[34m"


# ── Provider / Key 解析 ──────────────────────────────────────

# 仅声明视觉支持的有无；当前所有 provider（DeepSeek / MiniMax）都无视觉。
_VISION_PROVIDERS: set[str] = set()


def _resolve_provider(model_id: str | None) -> str:
    """根据 --model 解析所属 provider（默认 deepseek）。"""
    return get_provider_for_model(model_id)


def _resolve_api_key(
    *,
    provider: str,
    auth: cli_auth.CliAuth | None,
    verbose: bool,
) -> str | None:
    """按优先级取 Key：Web BYOK → 环境变量。"""
    env_var = get_api_key_env_for_provider(provider)
    key = cli_auth.get_api_key_with_fallback(
        provider=provider, env_var=env_var, auth=auth
    )
    if key and verbose:
        source = "web BYOK" if auth else f"env {env_var}"
        print(f"{C.DIM}· API key 来源: {source}（provider={provider}）{C.R}")
    return key


def _check_vision_supported(provider: str) -> bool:
    return provider in _VISION_PROVIDERS


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
    started = [False]

    def printer(chunk: str) -> None:
        if not started[0]:
            print(f"\n{C.BOLD}Agent>{C.R} ", end="", flush=True)
            started[0] = True
        print(chunk, end="", flush=True)

    def finish() -> None:
        if started[0]:
            print()
            started[0] = False

    def reset() -> None:
        started[0] = False

    return printer, finish, reset


# ── 图片（当前 provider 不支持视觉） ──────────────────────────

def _handle_image_command(arg: str) -> bool:
    """所有当前 provider 都无视觉模型，/image 命令直接禁用。"""
    print(
        f"{C.RED}✗ 当前 Provider（DeepSeek / MiniMax）都不支持视觉输入，"
        f"/image 命令暂不可用{C.R}"
    )
    return True  # 已处理


def _guess_mime(suffix: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(suffix.lower(), "image/jpeg")


# ── 命令处理 ──────────────────────────────────────────────

def _print_active_sessions(current: str | None) -> None:
    sessions = cli_sessions.list_active()
    if not sessions:
        print(f"{C.DIM}暂无活跃会话{C.R}")
        return
    print(f"\n{C.BOLD}活跃会话:{C.R}")
    for i, s in enumerate(sessions, 1):
        mark = f" {C.GREEN}← 当前{C.R}" if s["name"] == current else ""
        print(f"  {C.DIM}{i:>3}.{C.R} {s['name']}{C.DIM}  ({s['messages']} 条消息){C.R}{mark}")


def _handle_command(
    cmd: str,
    agent: CodingAgent,
    current_session: list[str],
    auth: cli_auth.CliAuth | None,
) -> str | None:
    """处理 / 命令。返回 None=已处理；字符串=要发给 Agent 的文本；"__EXIT__"=退出。"""
    parts = cmd.strip().split(maxsplit=1)
    name = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if name in ("/new",):
        new_name = arg.strip() or cli_sessions.default_session_name()
        agent.reset()
        agent.start_session()
        current_session.clear()
        current_session.append(new_name)
        cli_sessions.save_active(new_name, list(agent.session.messages))
        print(f"{C.GREEN}✓ 新会话: {new_name}{C.R}")
        return None

    elif name in ("/list", "/ls"):
        _print_active_sessions(current_session[0] if current_session else None)
        return None

    elif name in ("/switch", "/sw"):
        target = arg.strip()
        if not target:
            print(f"{C.YELLOW}用法: /switch <会话名>{C.R}")
            return None
        try:
            msgs = cli_sessions.load_active(target)
        except FileNotFoundError:
            print(f"{C.RED}✗ 会话不存在: {target}{C.R}")
            return None
        agent.session.messages = msgs
        agent.session.save()
        current_session.clear()
        current_session.append(target)
        print(f"{C.GREEN}✓ 切换到: {target}（{len(msgs)} 条消息）{C.R}")
        return None

    elif name in ("/delete", "/rm", "/del"):
        target = arg.strip()
        if not target:
            print(f"{C.YELLOW}用法: /delete <会话名> [--force]{C.R}")
            return None
        # 解析 --force
        parts2 = target.split()
        name_target = parts2[0]
        force = "--force" in parts2 or "-f" in parts2
        if force:
            if cli_sessions.hard_delete(name_target):
                print(f"{C.GREEN}✓ 彻底删除: {name_target}{C.R}")
                if current_session and current_session[0] == name_target:
                    current_session.clear()
                    current_session.append(cli_sessions.default_session_name())
            else:
                print(f"{C.RED}✗ 会话不存在: {name_target}{C.R}")
        else:
            if cli_sessions.soft_delete(name_target):
                print(f"{C.GREEN}✓ 已归档: {name_target}（/restore {name_target} 可恢复）{C.R}")
                if current_session and current_session[0] == name_target:
                    current_session.clear()
                    current_session.append(cli_sessions.default_session_name())
            else:
                print(f"{C.RED}✗ 会话不存在: {name_target}{C.R}")
        return None

    elif name in ("/restore",):
        target = arg.strip()
        if not target:
            print(f"{C.YELLOW}用法: /restore <会话名>{C.R}")
            return None
        if cli_sessions.restore(target):
            print(f"{C.GREEN}✓ 已恢复: {target}{C.R}")
        else:
            print(f"{C.RED}✗ 恢复失败（不存在或活跃里已有同名）{C.R}")
        return None

    elif name in ("/archived",):
        items = cli_sessions.list_archived()
        if not items:
            print(f"{C.DIM}暂无归档会话{C.R}")
            return None
        print(f"\n{C.BOLD}归档会话（软删除，可 /restore 恢复）:{C.R}")
        for i, s in enumerate(items, 1):
            print(
                f"  {C.DIM}{i:>3}.{C.R} {s['name']}{C.DIM}  "
                f"({s['messages']} 条 · 归档 {s.get('archived_at') or ''}){C.R}"
            )
        return None

    elif name in ("/rollback",):
        msgs = list(agent.session.messages)
        # 找到最后一对 user/assistant
        last_user = None
        last_assistant = None
        for i in range(len(msgs) - 1, -1, -1):
            role = msgs[i].get("role")
            if role == "assistant" and last_assistant is None:
                last_assistant = i
            elif role == "user" and last_user is None:
                last_user = i
                break
        if last_user is None:
            print(f"{C.YELLOW}当前会话无 user 消息可回滚{C.R}")
            return None
        # 删除从 last_user 到末尾
        del msgs[last_user:]
        agent.session.messages = msgs
        agent.session.save()
        # 同步到 cli_sessions/<current>.json
        cur = current_session[0] if current_session else None
        if cur:
            try:
                cli_sessions.save_active(cur, msgs)
            except OSError:
                pass
        print(f"{C.GREEN}✓ 已回滚最后一轮（移除 1 条 user + 1 条 assistant）{C.R}")
        return None

    elif name in ("/reset",):
        agent.reset()
        agent.start_session()
        cur = current_session[0] if current_session else None
        if cur:
            try:
                cli_sessions.save_active(cur, list(agent.session.messages))
            except OSError:
                pass
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

    elif name in ("/login",):
        api_base = auth.api_base if auth else os.getenv("SHELDON_API_BASE", "http://127.0.0.1:8765")
        print(f"目标: {api_base}")
        email = input("邮箱: ").strip()
        password = input("密码: ").strip()
        try:
            new_auth = cli_auth.login(api_base, email, password)
            print(
                f"{C.GREEN}✓ 已登录: {new_auth.user_email} ({new_auth.user_role}){C.R}"
            )
            print(f"{C.DIM}  token 已保存，下次启动自动续期{C.R}")
        except Exception as exc:
            print(f"{C.RED}✗ 登录失败: {exc}{C.R}")
        return None

    elif name in ("/logout",):
        cli_auth.CliAuth.clear()
        print(f"{C.GREEN}✓ 已登出（web token 已清）{C.R}")
        return None

    elif name in ("/whoami",):
        if auth:
            print(
                f"{C.GREEN}已登录{C.R}  {auth.user_email}  role={auth.user_role}  "
                f"api={auth.api_base}"
            )
        else:
            print(f"{C.DIM}未连接 Web 后端（仅 env key 模式）{C.R}")
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
{C.BOLD}会话管理:{C.R}
  {C.CYAN}/new [名称]{C.R}      新建会话（默认 session-N）
  {C.CYAN}/list | /ls{C.R}      列活跃会话
  {C.CYAN}/switch <名>{C.R}     切换会话（/sw）
  {C.CYAN}/delete <名>{C.R}     归档会话（可恢复）
  {C.CYAN}/delete <名> --force{C.R}  彻底删除（不可恢复）
  {C.CYAN}/archived{C.R}         列归档会话
  {C.CYAN}/restore <名>{C.R}    恢复归档会话
  {C.CYAN}/reset{C.R}           清空当前会话消息
  {C.CYAN}/rollback{C.R}        撤回最后一轮 user/assistant

{C.BOLD}能力查询:{C.R}
  {C.CYAN}/models{C.R}          查看可用模型（DeepSeek + MiniMax）
  {C.CYAN}/skills{C.R}          查看可用 Skills

{C.BOLD}Web 鉴权（拉 BYOK Key）:{C.R}
  {C.CYAN}/login{C.R}           登录 Web 后端（保存 token）
  {C.CYAN}/logout{C.R}          清除登录态
  {C.CYAN}/whoami{C.R}          查看当前登录态

{C.BOLD}其他:{C.R}
  {C.CYAN}/help | /?{C.R}       显示帮助
  {C.CYAN}/exit | /quit{C.R}    退出

{C.DIM}直接输入文字即可对话，支持多轮上下文。{C.R}
{C.DIM}/image 命令暂不可用（当前 Provider 均不支持视觉）。{C.R}
""")


# ── 主循环 ──────────────────────────────────────────────

def _cmd_login_standalone(api_base: str, email: str, password: str) -> int:
    """--login 子命令入口。"""
    try:
        auth = cli_auth.login(api_base, email, password)
        print(f"✓ 已登录: {auth.user_email} ({auth.user_role})")
        print(f"  token 已保存到 {cli_auth._auth_file()}")
        return 0
    except Exception as exc:
        print(f"✗ 登录失败: {exc}", file=sys.stderr)
        return 1


def _cmd_list_models() -> int:
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
    print("\n用法: sheldon --model deepseek-chat | --model MiniMax-M2.7")
    return 0


def _cmd_list_skills() -> int:
    print("Sheldon Agent Skills（Agent 可 list_skills / use_skill 调用）:\n")
    for s in discover_skills():
        desc = (s.description or "")[:80]
        print(f"  {C.CYAN}{s.name:24}{C.R} {desc}")
    print("\n用法: 在对话中说「加载 disk-storage 技能」或让 Agent 调用 use_skill")
    return 0


def _load_or_init_session(agent: CodingAgent, current_session: list[str]) -> None:
    """如果 cli_sessions/<name>.json 存在则加载；否则用 CodingAgent 现有 messages。"""
    cur = current_session[0]
    try:
        msgs = cli_sessions.load_active(cur)
        agent.session.messages = msgs
        agent.session.save()
    except FileNotFoundError:
        # 首次使用 → 把 CodingAgent 的当前 messages 写到 cli_sessions
        cli_sessions.save_active(cur, list(agent.session.messages))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sheldon 编程 Agent CLI — 流式输出 · 多会话 · 工具可视化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  sheldon                                # 启动交互模式
  sheldon --model deepseek-chat          # 指定 DeepSeek 模型
  sheldon --model MiniMax-M2.7           # 指定 MiniMax 模型
  sheldon --yes                          # 自动确认所有工具
  sheldon --tools                        # 显示工具调用过程
  sheldon "帮我写一个快速排序"            # 单次提问模式
  sheldon --login                        # 登录 Web 后端拉 BYOK Key
        """,
    )
    parser.add_argument("--user", "-u", default="default", help="用户 ID")
    parser.add_argument("--api-base", default=None,
                        help="Web 后端地址（默认 http://127.0.0.1:8765）")
    parser.add_argument("--login", action="store_true",
                        help="登录 Web 后端并保存 token（然后启动）")
    parser.add_argument("--logout", action="store_true",
                        help="清除 Web 登录态然后启动")
    parser.add_argument("--reset", action="store_true", help="清空会话记忆")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="显示详细日志（模型路由、key 来源等）")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="自动允许所有 review 级工具")
    parser.add_argument("--tools", "-t", action="store_true",
                        help="实时显示工具调用过程")
    parser.add_argument("--model", "-m", default=None,
                        help="模型 id 或 auto（默认 auto，启用复杂度路由）")
    parser.add_argument("--permission", "-p", default=None,
                        choices=["conservative", "balanced", "permissive"],
                        help="权限档位")
    parser.add_argument("--skills", action="store_true",
                        help="列出可用 Skills 并退出")
    parser.add_argument("--list-models", action="store_true",
                        help="列出 Agent 可用模型目录并退出")
    parser.add_argument("--image", "-i", action="append", default=[],
                        help="附加图片路径（暂不可用：当前 Provider 不支持视觉）")
    parser.add_argument("question", nargs="?", default=None,
                        help="单次提问（不进入交互模式）")
    parser.add_argument("--login-email", default=None, help="配合 --login 使用")
    parser.add_argument("--login-password", default=None, help="配合 --login 使用")
    args = parser.parse_args()

    # ── 快捷命令 ──
    if args.skills:
        return _cmd_list_skills()
    if args.list_models:
        return _cmd_list_models()

    # ── 加载 / 处理 Web 登录态 ──
    auth: cli_auth.CliAuth | None = None
    api_base = args.api_base or os.getenv("SHELDON_API_BASE", "http://127.0.0.1:8765")
    if args.logout:
        cli_auth.CliAuth.clear()
        print("✓ 已登出")
        return 0
    if args.login:
        email = args.login_email or input("邮箱: ").strip()
        password = args.login_password or input("密码: ")
        rc = _cmd_login_standalone(api_base, email, password)
        if rc != 0:
            return rc
        # 登录成功后继续启动
    auth = cli_auth.CliAuth.load()
    # 校验 token 是否过期（用 /api/auth/me）
    if auth is not None:
        try:
            cli_auth._http_json(f"{auth.api_base}/api/auth/me", token=auth.token)
        except Exception:
            print(f"{C.YELLOW}⚠ Web 登录态已过期，重新登录{C.R}")
            cli_auth.CliAuth.clear()
            auth = None

    # ── Provider / Key 解析 ──
    provider = _resolve_provider(args.model)
    api_key = _resolve_api_key(provider=provider, auth=auth, verbose=args.verbose)
    if not api_key:
        env_var = get_api_key_env_for_provider(provider)
        auth_hint = "（或 /login 登录 Web 后端拉 BYOK Key）" if auth is None else ""
        print(
            f"{C.RED}✗ 缺少 {provider} provider 的 API Key。{C.R}\n"
            f"  请设置环境变量 {env_var}{auth_hint}",
            file=sys.stderr,
        )
        return 2

    # ── 初始化 Agent ──
    confirm_handler = _cli_confirm_handler(args.yes, args.tools)
    tool_callback = _make_tool_display_callback(args.tools)
    stream_print, stream_finish, stream_reset = _make_stream_printer()

    agent = CodingAgent(
        user_id=args.user,
        resume=not args.reset,
        verbose=args.verbose,
        api_key=api_key,
    )
    if args.reset:
        agent.reset()
        agent.start_session()

    current_session: list[str] = [cli_sessions.default_session_name()]
    _load_or_init_session(agent, current_session)

    # ── 单次提问模式 ──
    if args.question:
        reply = agent.chat(
            args.question,
            confirm_handler=confirm_handler,
            on_event=tool_callback,
            session_id="cli",
            model=args.model,
            permission=args.permission,
            text_callback=stream_print,
            images=None,  # 当前 provider 不支持视觉，禁用
        )
        stream_finish()
        # 保存会话
        try:
            cli_sessions.save_active(current_session[0], list(agent.session.messages))
        except OSError:
            pass
        print(f"\n{C.DIM}— 单次提问完成 —{C.R}")
        return 0

    # ── 交互模式 ─
    mode = "自动确认" if args.yes else "需确认"
    model_hint = args.model or "auto（自动路由）"
    perm_hint = args.permission or "balanced"
    tools_hint = "工具可视化开" if args.tools else "工具可视化关"
    auth_hint = f" · Web 已登录 {auth.user_email}" if auth else " · 仅 env key"
    print(
        f"\n{C.BOLD}Sheldon Agent{C.R} 就绪"
        f" | 模型: {C.CYAN}{model_hint}{C.R} (provider={provider})"
        f" | 权限: {perm_hint}"
        f" | {mode}"
        f" | {tools_hint}"
        f"{auth_hint}"
        f"\n{C.DIM}输入 /help 查看命令 | exit 退出{C.R}\n"
    )

    try:
        while True:
            try:
                user_input = input(f"{C.GREEN}You>{C.R} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{C.DIM}— 再见 —{C.R}")
                break

            if not user_input:
                continue

            # /image 拦截
            if user_input.lower().startswith("/image"):
                _handle_image_command(user_input)
                continue

            # 命令
            if user_input.startswith("/"):
                result = _handle_command(user_input, agent, current_session, auth)
                if result == "__EXIT__":
                    break
                continue

            # 发送消息
            stream_reset()
            reply = agent.chat(
                user_input,
                confirm_handler=confirm_handler,
                on_event=tool_callback,
                session_id="cli",
                model=args.model,
                permission=args.permission,
                text_callback=stream_print,
                images=None,
            )
            stream_finish()
            # 保存会话
            try:
                cli_sessions.save_active(
                    current_session[0], list(agent.session.messages)
                )
            except OSError:
                pass

    finally:
        agent.end_session()
        try:
            cli_sessions.save_active(
                current_session[0], list(agent.session.messages)
            )
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())