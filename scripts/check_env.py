"""一键检查开发环境：依赖、密钥、百炼 API 连通性。"""

from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.agent.console import answer, out, step, warn
from core.config import BAILIAN_BASE_URL, MODEL_CODER, create_client


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "sk-****"
    return f"{key[:7]}...{key[-4:]}"


def check() -> int:
    step("环境检查", "验证依赖、API 密钥与百炼连接")
    errors = 0

    # 依赖
    for pkg in ("openai", "dotenv"):
        try:
            ver = importlib.metadata.version("python-dotenv" if pkg == "dotenv" else pkg)
            out(f"{pkg} {ver}", "依赖已安装")
        except importlib.metadata.PackageNotFoundError:
            warn(f"未安装 {pkg}", "请运行 uv sync --dev")
            errors += 1

    # 密钥
    env_path = ROOT / ".env"
    key = os.getenv("DASHSCOPE_API_KEY")
    if key:
        src = ".env 文件" if env_path.is_file() else "系统/终端环境变量"
        out(f"DASHSCOPE_API_KEY={_mask_key(key)}", f"密钥已加载（来源：{src}）")
    else:
        warn(
            "未找到 DASHSCOPE_API_KEY",
            "复制 .env.example 为 .env 并填入密钥，或设置环境变量",
        )
        errors += 1
        answer(f"检查未通过（{errors} 项）", "请先修复上述问题")
        return 1

    # API 连通
    step("连接百炼", f"endpoint={BAILIAN_BASE_URL}，model={MODEL_CODER}")
    try:
        client = create_client()
        resp = client.chat.completions.create(
            model=MODEL_CODER,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        preview = (resp.choices[0].message.content or "")[:30]
        out(f"API 响应: {preview!r}", "百炼 API 连通正常")
    except Exception as e:
        warn(str(e), "API 请求失败，请检查密钥、网络或模型是否已开通")
        errors += 1

    # 可选 MCP 密钥（仅提示，不计入 errors）
    step("可选 MCP", "GitHub / Brave 外部工具（阶段 G）")
    gh = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    brave = os.getenv("BRAVE_API_KEY")
    if gh:
        out(f"GITHUB_TOKEN={_mask_key(gh)}", "GitHub MCP 已配置")
    else:
        warn("未配置 GITHUB_TOKEN", "Issues/PR 工具不可用，见 .env.example")
    if brave:
        out(f"BRAVE_API_KEY={_mask_key(brave)}", "Brave Search 已配置")
    else:
        warn("未配置 BRAVE_API_KEY", "联网搜索工具不可用，见 .env.example")

    if errors:
        answer(f"检查未通过（{errors} 项）", "请根据上方提示修复")
        return 1

    answer("环境就绪", "可以运行 uv run python -m apps.cli 或 uv run python -m server")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
