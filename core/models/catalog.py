"""Agent 可用模型目录（B 为主：择优静态清单）。"""

from __future__ import annotations

from dataclasses import dataclass

AUTO_MODEL_ID = "auto"


@dataclass(frozen=True)
class AgentModelEntry:
    """仅收录可作为编程 Agent（对话 + 工具调用）的模型。"""

    id: str
    label: str
    group: str
    tier: str
    max_tokens: int
    description: str
    supports_tools: bool = True
    is_default: bool = False


# 择优静态目录：非 Agent 能力模型（纯 embedding、图像、语音等）不收录
AGENT_MODEL_CATALOG: tuple[AgentModelEntry, ...] = (
    AgentModelEntry(
        id="qwen3.6-flash",
        label="Qwen3.6 Flash",
        group="极速",
        tier="flash",
        max_tokens=8192,
        description="低成本、低延迟，适合简单问答与读文件",
    ),
    AgentModelEntry(
        id="qwen-turbo",
        label="Qwen Turbo",
        group="极速",
        tier="flash",
        max_tokens=8192,
        description="通用快速模型",
    ),
    AgentModelEntry(
        id="qwen3.7-plus",
        label="Qwen3.7 Plus",
        group="主力",
        tier="plus",
        max_tokens=32768,
        description="日常编程推荐，平衡质量与成本",
        is_default=True,
    ),
    AgentModelEntry(
        id="qwen-plus",
        label="Qwen Plus",
        group="主力",
        tier="plus",
        max_tokens=32768,
        description="通用增强模型",
    ),
    AgentModelEntry(
        id="qwen3-coder-plus",
        label="Qwen3 Coder Plus",
        group="代码",
        tier="coder",
        max_tokens=32768,
        description="代码生成与重构优化",
    ),
    AgentModelEntry(
        id="qwen-coder-turbo",
        label="Qwen Coder Turbo",
        group="代码",
        tier="coder",
        max_tokens=8192,
        description="快速代码补全与脚本编写",
    ),
    AgentModelEntry(
        id="qwen-max",
        label="Qwen Max",
        group="旗舰",
        tier="max",
        max_tokens=32768,
        description="复杂推理与架构设计",
    ),
    AgentModelEntry(
        id="qwen3-max",
        label="Qwen3 Max",
        group="旗舰",
        tier="max",
        max_tokens=32768,
        description="旗舰级推理能力",
    ),
    AgentModelEntry(
        id="qwen-long",
        label="Qwen Long",
        group="长文本",
        tier="long",
        max_tokens=32768,
        description="超长上下文，适合大仓库分析",
    ),
)

_CATALOG_BY_ID = {m.id: m for m in AGENT_MODEL_CATALOG}


def get_default_model_id() -> str:
    for m in AGENT_MODEL_CATALOG:
        if m.is_default:
            return m.id
    return AGENT_MODEL_CATALOG[0].id


def get_catalog_entry(model_id: str) -> AgentModelEntry | None:
    return _CATALOG_BY_ID.get(model_id)


def is_agent_model(model_id: str) -> bool:
    entry = get_catalog_entry(model_id)
    return entry is not None and entry.supports_tools


def resolve_model_choice(model: str | None) -> tuple[str | None, bool]:
    """解析用户选择 → (固定 API model_id 或 None, 是否启用自动路由)。"""
    if not model or model == AUTO_MODEL_ID:
        return None, True
    entry = get_catalog_entry(model)
    if entry is None or not entry.supports_tools:
        raise ValueError(f"不可用作 Agent 的模型: {model}")
    return entry.id, False
