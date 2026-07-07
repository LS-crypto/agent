"""工具层统一安全策略：路径、Shell、敏感文件、风险分级、权限档位。"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

from core.agent.permissions import PermissionTier, get_permission_tier

RiskLevel = Literal["allowed", "review", "blocked"]
SeverityLevel = Literal["low", "medium", "high"]

TOOL_RISK: dict[str, RiskLevel] = {
    "read_file": "allowed",
    "list_dir": "allowed",
    "grep": "allowed",
    "glob_search": "allowed",
    "write_file": "review",
    "edit_file": "review",
    "execute_command": "review",
    "git_status": "allowed",
    "git_diff": "allowed",
    "git_commit": "review",
    # 系统信息（Python 实现，无 Shell）
    "get_disk_usage": "allowed",
    "get_workspace_stats": "allowed",
    "get_env_info": "allowed",
    # Skills
    "list_skills": "allowed",
    "use_skill": "review",
    # MCP 兼容
    "get_current_time": "allowed",
    "fetch_url": "review",
    "memory_note_save": "review",
    "memory_note_search": "allowed",
    "memory_note_list": "allowed",
    "calculate": "allowed",
    # GitHub MCP（G1，只读 allowed / 写入 review）
    "github_search_issues": "allowed",
    "github_get_issue": "allowed",
    "github_list_pulls": "allowed",
    "github_get_pull": "allowed",
    "github_search_code": "allowed",
    "github_create_issue_comment": "review",
    # Brave Search（G2，联网 review）
    "brave_web_search": "review",
    "brave_news_search": "review",
}

# 权限档位覆盖（blocked 永不覆盖）
_TIER_OVERRIDES: dict[PermissionTier, dict[str, RiskLevel]] = {
    "conservative": {
        "use_skill": "review",
        "execute_command": "review",
        "write_file": "review",
        "edit_file": "review",
        "git_commit": "review",
    },
    "balanced": {},
    "permissive": {
        "use_skill": "allowed",
        "get_disk_usage": "allowed",
        "get_workspace_stats": "allowed",
        "get_env_info": "allowed",
    },
}

# 宽松档 Shell 额外白名单（仍受黑名单约束）
_PERMISSIVE_SHELL_EXTRA: tuple[str, ...] = (
    "wmic logicaldisk get",
    "powershell -command get-psdrive",
)

_COMMAND_BLOCKED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bgit push\b", "禁止 git push"),
    (r"\bgit reset\s+--hard\b", "禁止 git reset --hard"),
    (r"\brm\s", "禁止 rm 删除"),
    (r"\bdel\s", "禁止 del 删除"),
    (r"\bremove-item\b", "禁止 Remove-Item"),
)

# ── 资源限制常量（供各工具引用） ──
DEFAULT_SHELL_TIMEOUT = 30
MAX_READ_CHARS = 50_000
MAX_WRITE_BYTES = 512 * 1024
MAX_LIST_ENTRIES = 500
MAX_GREP_MATCHES = 50

# ── Shell 白名单前缀 ──
SHELL_PREFIX_WHITELIST: tuple[str, ...] = (
    "python",
    "python3",
    "py",
    "pip",
    "pytest",
    "node",
    "npm",
    "npx",
    "dir",
    "cd",
    "type",
    "echo",
    "where",
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "git add",
    "git commit",
)

# Shell 拦截片段（小写匹配）
_SHELL_BLOCK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bsudo\b", "禁止 sudo"),
    (r"chmod\s+777", "禁止 chmod 777"),
    (r":\(\)\s*\{", "禁止 fork bomb"),
    (r"^/[a-zA-Z]", "禁止 Unix 绝对路径"),
    (r"^[A-Za-z]:\\", "禁止 Windows 盘符绝对路径"),
    (r"^\\\\", "禁止 UNC 路径"),
    (r"\bcurl\b", "禁止 curl 外传"),
    (r"\bwget\b", "禁止 wget 外传"),
    (r"\binvoke-webrequest\b", "禁止 Invoke-WebRequest"),
    (r"\biwr\b", "禁止 iwr"),
    (r"\bnc\b", "禁止 nc"),
    (r"powershell\s+-enc", "禁止 powershell -enc"),
    (r"\bpython3?\s+-c\b", "禁止 python -c"),
    (r"\bnode\s+-e\b", "禁止 node -e"),
    (r"\brm\s", "禁止 rm 删除"),
    (r"\bdel\s", "禁止 del 删除"),
    (r"\bremove-item\b", "禁止 Remove-Item"),
    (r"\brd\s+/s\b", "禁止 rd /s"),
    (r"\brmdir\s+/s\b", "禁止 rmdir /s"),
)

_SENSITIVE_EXACT_NAMES = frozenset(
    {".env", ".env.local", ".env.production"}
)
_SENSITIVE_EXACT_BASENAMES = frozenset({"id_rsa", "id_ed25519"})
_SENSITIVE_NAME_SUBSTRINGS = ("credentials", "secret")
_SENSITIVE_PATH_MARKERS = (".git/config",)


def policy_error(error: str, policy: str) -> dict:
    return {"success": False, "error": error, "policy": policy}


def normalize_path_input(path: str) -> str:
    """Unicode NFKC 规范化，统一斜杠。"""
    return unicodedata.normalize("NFKC", path).replace("\\", "/")


def is_sensitive_path(rel_path: str) -> bool:
    """相对沙箱根路径是否命中敏感规则。"""
    normalized = normalize_path_input(rel_path).strip("/")
    if not normalized or normalized == ".":
        return False

    lower = normalized.lower()
    name = Path(normalized).name.lower()

    if name in _SENSITIVE_EXACT_NAMES:
        return True
    if name.endswith(".pem") or name.endswith(".key"):
        return True
    if name in _SENSITIVE_EXACT_BASENAMES:
        return True
    if any(s in name for s in _SENSITIVE_NAME_SUBSTRINGS):
        return True
    for marker in _SENSITIVE_PATH_MARKERS:
        if lower == marker or lower.endswith(f"/{marker}"):
            return True
    return False


class PathPolicy:
    """路径解析 + symlink + 沙箱边界。"""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def check(self, path: str, *, check_sensitive: bool = True) -> Path | dict:
        return check_path(path, self.root, check_sensitive=check_sensitive)

    def rel(self, resolved: Path) -> str:
        return str(resolved.relative_to(self.root))


def check_path(
    path: str,
    root: Path,
    *,
    check_sensitive: bool = True,
) -> Path | dict:
    """解析相对路径；失败返回 policy 错误 dict。"""
    root = root.resolve()
    raw = normalize_path_input(path).strip()

    if not raw or raw == ".":
        candidate = root
    else:
        if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
            return policy_error("路径必须为沙箱内相对路径", "path_blocked")

        rel = Path(raw)
        if ".." in rel.parts:
            return policy_error("路径不得包含 .. 穿越", "path_blocked")

        candidate = root
        for part in rel.parts:
            if part in ("", "."):
                continue
            if part == "..":
                return policy_error("路径不得包含 .. 穿越", "path_blocked")
            candidate = candidate / part
            if candidate.is_symlink():
                target = candidate.resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    return policy_error(
                        "符号链接指向沙箱外，已拒绝",
                        "symlink_escape",
                    )
                candidate = target

        try:
            candidate = candidate.resolve()
        except OSError as e:
            return policy_error(f"路径无效: {e}", "path_blocked")

        try:
            candidate.relative_to(root)
        except ValueError:
            return policy_error(
                f"路径越界，仅允许访问沙箱内: {root}",
                "path_blocked",
            )

    if check_sensitive:
        try:
            rel_str = str(candidate.relative_to(root))
        except ValueError:
            rel_str = raw
        if is_sensitive_path(rel_str):
            return policy_error(
                "敏感文件受策略保护，禁止访问",
                "sensitive_file",
            )

    return candidate


class ShellPolicy:
    """Shell 命令白名单 + 黑名单。"""

    def check(self, command: str) -> str | None:
        return check_shell(command)


def _matches_shell_prefix(lower: str, prefix: str) -> bool:
    if lower == prefix:
        return True
    return lower.startswith(prefix + " ") or lower.startswith(prefix + "\t")


def check_shell(command: str, *, tier: PermissionTier | None = None) -> str | None:
    """失败返回 error 字符串；通过返回 None。"""
    cmd = command.strip()
    if not cmd:
        return "命令不能为空"

    lower = cmd.lower()

    for pattern, reason in _SHELL_BLOCK_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return f"命令被安全策略拦截: {reason}"

    # 命令中嵌入的绝对路径
    if re.search(r"(?<!\w)/(?:etc|usr|var|tmp|home|root)/", lower):
        return "命令被安全策略拦截: 禁止引用系统绝对路径"
    if re.search(r"[A-Za-z]:\\(?:Windows|Users|Program Files)", cmd):
        return "命令被安全策略拦截: 禁止引用系统绝对路径"

    tier = tier or get_permission_tier()
    prefixes = list(SHELL_PREFIX_WHITELIST)
    if tier == "permissive":
        prefixes = list(prefixes) + list(_PERMISSIVE_SHELL_EXTRA)

    matched = any(_matches_shell_prefix(lower, prefix) for prefix in prefixes)
    if not matched:
        allowed = "、".join(SHELL_PREFIX_WHITELIST[:8]) + " 等"
        return (
            f"命令不在白名单内。允许的前缀: {allowed}。"
            f"完整列表见 ShellPolicy 文档。"
        )

    if _matches_shell_prefix(lower, "git") or lower == "git":
        git_prefixes = [p for p in SHELL_PREFIX_WHITELIST if p.startswith("git ")]
        git_ok = any(_matches_shell_prefix(lower, p) for p in git_prefixes)
        if not git_ok:
            return "git 仅允许 status/diff/log/branch/add/commit 子命令"

    return None


def get_tool_risk(tool_name: str, *, tier: PermissionTier | None = None) -> RiskLevel:
    tier = tier or get_permission_tier()
    base = TOOL_RISK.get(tool_name, "review")
    override = _TIER_OVERRIDES.get(tier, {}).get(tool_name)
    if override:
        return override
    return base


def effective_tool_risk(
    tool_name: str,
    args: dict[str, Any],
    *,
    tier: PermissionTier | None = None,
) -> RiskLevel:
    tier = tier or get_permission_tier()
    risk = get_tool_risk(tool_name, tier=tier)
    if tool_name == "execute_command":
        cmd_risk = get_command_risk(str(args.get("command", "")))
        if cmd_risk == "blocked":
            return "blocked"
    return risk


def blocked_tool_message(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name == "execute_command":
        cmd = str(args.get("command", ""))
        for pattern, reason in _COMMAND_BLOCKED_PATTERNS:
            if re.search(pattern, cmd.lower(), re.IGNORECASE):
                return f"命令被策略永久拒绝: {reason}"
    return f"工具 {tool_name} 被策略永久拒绝"


def get_command_risk(command: str) -> RiskLevel:
    """execute_command 专用：危险命令 → blocked，其余 → review。"""
    lower = command.strip().lower()
    if not lower:
        return "review"
    for pattern, _reason in _COMMAND_BLOCKED_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return "blocked"
    return "review"


def _command_severity(command: str) -> SeverityLevel:
    lower = command.strip().lower()
    if any(k in lower for k in ("git commit", "write", "pip install", "npm install")):
        return "high"
    if any(k in lower for k in ("python", "pytest", "node", "npm run")):
        return "medium"
    return "medium"


def build_confirmation_detail(
    tool: str,
    args: dict[str, Any],
    *,
    tier: PermissionTier | None = None,
) -> dict[str, Any]:
    """供 Web/CLI 展示：摘要 + 风险说明 + 影响 + 严重度。"""
    tier = tier or get_permission_tier()
    summary = build_confirmation_summary(tool, args)
    severity: SeverityLevel = "medium"
    explanation = "该操作可能改变项目状态，请确认是否继续。"
    impact = "允许后 Agent 将继续执行并可能基于结果采取后续行动。"

    if tool == "write_file":
        severity = "high"
        path = args.get("file_path", "?")
        n = len(str(args.get("content", "")))
        explanation = f"Agent 将创建或覆盖沙箱内文件 `{path}`（约 {n} 字符）。"
        impact = "原有内容可能被完全替换；建议先 read_file 确认当前内容。"
    elif tool == "edit_file":
        severity = "high"
        path = args.get("file_path", "?")
        explanation = f"Agent 将在 `{path}` 中搜索并替换指定文本片段。"
        impact = "若匹配不准确可能导致意外修改；请核对 old_string 预览。"
    elif tool == "execute_command":
        cmd = str(args.get("command", ""))
        severity = _command_severity(cmd)
        explanation = (
            f"将在<strong>沙箱项目目录</strong>内执行 Shell 命令（档位：{tier}）。"
            f"命令：<code>{cmd[:200]}</code>"
        )
        impact = (
            "命令可读写沙箱内文件、安装依赖或运行测试。"
            "系统级删除、网络外传、sudo 等已被策略永久禁止。"
        )
    elif tool == "git_commit":
        severity = "high"
        msg = args.get("message", "")
        explanation = f"将执行 Git 提交，说明：{msg!r}"
        impact = "会生成本地 commit；push 仍被策略禁止。"
    elif tool == "use_skill":
        severity = "low"
        name = args.get("skill_name", "?")
        explanation = f"加载技能 `{name}` 的完整说明到当前对话上下文。"
        impact = "仅增加 Agent 指引文本，不直接修改文件或执行命令。"
    elif tool == "fetch_url":
        severity = "medium"
        url = args.get("url", "?")
        explanation = f"将从互联网抓取 URL 内容（白名单域名）：{url}"
        impact = "仅返回文本预览，不会写入沙箱文件；请确认链接可信。"
    elif tool == "memory_note_save":
        severity = "low"
        explanation = f"保存记忆笔记：{args.get('title', '?')}"
        impact = "写入本地 runtime 目录，供后续 memory_note_search 检索。"
    elif tool.startswith("github_"):
        severity = "low" if tool != "github_create_issue_comment" else "medium"
        explanation = f"调用 GitHub API：{summary}"
        impact = "只读操作不会修改远端；写入评论需你明确允许。"
    elif tool.startswith("brave_"):
        severity = "medium"
        q = args.get("query", "?")
        explanation = f"通过 Brave Search 联网搜索：{q!r}"
        impact = "将把你的查询发送到 Brave API 并返回公开网页摘要。"
    else:
        severity = "medium"
        explanation = f"工具 `{tool}` 需要人工确认（权限档位：{tier}）。"

    return {
        "summary": summary,
        "explanation": explanation,
        "impact": impact,
        "severity": severity,
        "tier": tier,
    }


def build_confirmation_summary(tool: str, args: dict[str, Any]) -> str:
    if tool == "write_file":
        content = str(args.get("content", ""))
        path = args.get("file_path", "?")
        return f"写入文件 {path}（{len(content)} 字符）"
    if tool == "edit_file":
        return (
            f"编辑文件 {args.get('file_path', '?')}："
            f"替换 {len(str(args.get('old_string', '')))} 字符"
        )
    if tool == "execute_command":
        return f"执行命令: {args.get('command', '')}"
    if tool == "git_commit":
        return f"Git 提交: {args.get('message', '')}"
    if tool == "use_skill":
        return f"加载技能: {args.get('skill_name', '?')}"
    if tool == "brave_web_search":
        return f"Brave 搜索: {args.get('query', '')}"
    if tool == "brave_news_search":
        return f"Brave 新闻: {args.get('query', '')}"
    if tool == "github_search_issues":
        return f"GitHub Issues: {args.get('query', '')} @ {args.get('repo', '?')}"
    if tool == "github_get_issue":
        return f"GitHub Issue #{args.get('issue_number', '?')} @ {args.get('repo', '?')}"
    if tool == "github_list_pulls":
        return f"GitHub PR 列表 @ {args.get('repo', '?')}"
    if tool == "github_get_pull":
        return f"GitHub PR #{args.get('pull_number', '?')} @ {args.get('repo', '?')}"
    if tool == "github_search_code":
        return f"GitHub 代码搜索: {args.get('query', '')}"
    if tool == "github_create_issue_comment":
        return f"GitHub 评论 Issue #{args.get('issue_number', '?')}"
    return f"{tool}({json.dumps(args, ensure_ascii=False)[:120]})"


def sse_confirmation_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """SSE 用精简 args，避免 content 过大。"""
    if tool == "write_file":
        content = str(args.get("content", ""))
        return {
            "file_path": args.get("file_path"),
            "content_preview": content[:200],
            "content_length": len(content),
        }
    if tool == "edit_file":
        return {
            "file_path": args.get("file_path"),
            "old_string_preview": str(args.get("old_string", ""))[:200],
            "new_string_preview": str(args.get("new_string", ""))[:200],
        }
    if tool == "execute_command":
        return {"command": args.get("command")}
    if tool == "use_skill":
        return {"skill_name": args.get("skill_name")}
    return args
