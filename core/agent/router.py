"""任务复杂度路由：根据用户请求选择合适的模型 tier。"""

from __future__ import annotations

import json
import re
from typing import Any

from core.config import MODEL_TIERS, ModelConfig, create_client, get_model_name

# ---------- 复杂度定义 ----------

COMPLEXITY_SIMPLE = "simple"      # 搜索、格式化、简单问答
COMPLEXITY_STANDARD = "standard"  # 编码、重构、Bug 修复
COMPLEXITY_COMPLEX = "complex"    # 架构设计、多文件重构

# 复杂度 → 模型 tier 映射
_COMPLEXITY_TO_TIER: dict[str, str] = {
    COMPLEXITY_SIMPLE: "flash",
    COMPLEXITY_STANDARD: "plus",
    COMPLEXITY_COMPLEX: "max",
}

# ---------- 关键词快速路由（零成本，不调 LLM） ----------

_SIMPLE_PATTERNS = re.compile(
    r"^(列出|查看|显示|搜索|查找|grep|find|cat|head|tail|ls|什么|哪个|多少|在哪|解释一下|read|list|show|search|find|what|which|where|how many)",
    re.IGNORECASE,
)

_COMPLEX_PATTERNS = re.compile(
    r"(重构|架构|设计|迁移|全面|整体|性能优化|多文件|从零|redesign|refactor|architect|migrate|overhaul|multi.file)",
    re.IGNORECASE,
)


def _keyword_route(user_input: str) -> str | None:
    """基于关键词的快速路由，返回 complexity 或 None（无法确定时）。"""
    text = user_input.strip()
    if not text:
        return COMPLEXITY_SIMPLE

    # 短句 + 问号 → 大概率简单问答
    if len(text) < 30 and text.endswith("?") or text.endswith("？"):
        return COMPLEXITY_SIMPLE

    if _COMPLEX_PATTERNS.search(text):
        return COMPLEXITY_COMPLEX

    if _SIMPLE_PATTERNS.match(text):
        return COMPLEXITY_SIMPLE

    return None


# ---------- LLM 路由（用最便宜的模型分类） ----------

_ROUTE_PROMPT = """你是一个任务复杂度分类器。根据用户的请求，判断复杂度：

- simple: 搜索、查看、格式化、简单问答、单文件读取
- standard: 编码、修改代码、Bug 修复、单文件编辑、写函数
- complex: 架构设计、多文件重构、调试复杂问题、性能优化

只回答一个词：simple、standard 或 complex

用户请求：{input}"""


def _llm_route(user_input: str) -> str:
    """用最便宜的模型做复杂度分类。"""
    try:
        client = create_client()
        resp = client.chat.completions.create(
            model=MODEL_TIERS["flash"].name,
            messages=[{"role": "user", "content": _ROUTE_PROMPT.format(input=user_input)}],
            max_tokens=10,
            temperature=0.0,
        )
        text = resp.choices[0].message.content.strip().lower()
        if text in (COMPLEXITY_SIMPLE, COMPLEXITY_STANDARD, COMPLEXITY_COMPLEX):
            return text
        return COMPLEXITY_STANDARD  # 无法识别时走标准
    except Exception:
        return COMPLEXITY_STANDARD  # LLM 路由失败时走标准


# ---------- 公开接口 ----------

def route(user_input: str, *, use_llm: bool = True) -> tuple[str, str]:
    """根据用户输入路由到合适的模型。

    Returns:
        (complexity, model_name) 例如 ("standard", "qwen-plus")
    """
    # 1. 先尝试关键词路由（零成本）
    complexity = _keyword_route(user_input)

    # 2. 关键词无法确定时，用 LLM 路由（~0.1¢）
    if complexity is None and use_llm:
        complexity = _llm_route(user_input)

    # 3. 都无法确定时，默认标准
    if complexity is None:
        complexity = COMPLEXITY_STANDARD

    tier = _COMPLEXITY_TO_TIER[complexity]
    model_name = get_model_name(tier)
    return complexity, model_name


def route_by_tool_call(tool_name: str, fn_args: dict[str, Any]) -> str:
    """根据工具调用判断后续轮次应使用的模型 tier。

    已调用工具后的轮次通常需要更强的模型来理解工具结果并决策。
    """
    # 读操作 → 可以用 flash 继续理解
    READ_TOOLS = {"read_file", "list_dir", "grep", "glob_search"}
    # 写操作 → 需要 plus 来做编辑决策
    WRITE_TOOLS = {"write_file", "edit_file", "execute_command"}

    if tool_name in READ_TOOLS:
        return "flash"
    if tool_name in WRITE_TOOLS:
        return "plus"
    return "plus"  # 未知工具默认 plus
