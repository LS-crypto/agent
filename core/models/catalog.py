"""Agent 可用模型目录（B 为主：择优静态清单）。"""

from __future__ import annotations

from dataclasses import dataclass

AUTO_MODEL_ID = "auto"

# 普通用户默认可选模型（admin 不受限；可通过 USER_ALLOWED_MODELS 覆盖）
NEW_USER_FREE_QUOTA_TOKENS = 1_000_000
NEW_USER_FREE_QUOTA_DAYS = 90

DEFAULT_USER_MODEL_IDS: tuple[str, ...] = (
    "qwen3.6-flash",
    "qwen3.7-plus",
    "qwen3-coder-plus",
    "qwen3.7-max",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "glm-5.2",
    "glm-5.1",
    "qwen3-vl-plus",
    "qwen3-vl-flash",
    "qwen-vl-max",
    "qwen-vl-plus",
)


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
    supports_vision: bool = False
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
        id="qwen3.7-max",
        label="Qwen3.7 Max",
        group="旗舰",
        tier="max",
        max_tokens=32768,
        description="千问 3.7 全能旗舰，复杂 Agent 任务",
    ),
    AgentModelEntry(
        id="qwen-long",
        label="Qwen Long",
        group="长文本",
        tier="long",
        max_tokens=32768,
        description="超长上下文，适合大仓库分析",
    ),
    # --- 百炼第三方对话模型（支持 Function Calling）---
    AgentModelEntry(
        id="deepseek-v4-pro",
        label="DeepSeek V4 Pro",
        group="第三方",
        tier="deepseek",
        max_tokens=8192,
        description="编程/数学/推理旗舰，百万上下文，支持思考模式",
    ),
    AgentModelEntry(
        id="deepseek-v4-flash",
        label="DeepSeek V4 Flash",
        group="第三方",
        tier="deepseek",
        max_tokens=8192,
        description="DeepSeek V4 快速经济版",
    ),
    AgentModelEntry(
        id="glm-5.2",
        label="GLM-5.2",
        group="第三方",
        tier="glm",
        max_tokens=8192,
        description="智谱 1M 上下文，长文档与代码分析",
    ),
    AgentModelEntry(
        id="glm-5.1",
        label="GLM-5.1",
        group="第三方",
        tier="glm",
        max_tokens=8192,
        description="智谱混合推理，支持工具流式返回",
    ),
    # --- 视觉理解（支持 Function Calling；图片输入待 Web 上传能力）---
    AgentModelEntry(
        id="qwen3-vl-plus",
        label="Qwen3 VL Plus",
        group="视觉",
        tier="vision",
        max_tokens=32768,
        description="图像/视频理解 + 工具调用，Visual Coding",
        supports_vision=True,
    ),
    AgentModelEntry(
        id="qwen3-vl-flash",
        label="Qwen3 VL Flash",
        group="视觉",
        tier="vision",
        max_tokens=8192,
        description="轻量视觉理解，低成本",
        supports_vision=True,
    ),
    AgentModelEntry(
        id="qwen-vl-max",
        label="Qwen VL Max",
        group="视觉",
        tier="vision",
        max_tokens=32768,
        description="经典视觉旗舰，OCR/图表/界面理解",
        supports_vision=True,
    ),
    AgentModelEntry(
        id="qwen-vl-plus",
        label="Qwen VL Plus",
        group="视觉",
        tier="vision",
        max_tokens=8192,
        description="视觉理解均衡版",
        supports_vision=True,
    ),
)

# 百炼新人免费额度：中国内地各 Agent 模型独立 100 万 Token（开通后 90 天）
MODELS_WITH_NEW_USER_FREE_QUOTA: frozenset[str] = frozenset(m.id for m in AGENT_MODEL_CATALOG)

_CATALOG_BY_ID = {m.id: m for m in AGENT_MODEL_CATALOG}


def get_default_model_id() -> str:
    for m in AGENT_MODEL_CATALOG:
        if m.is_default:
            return m.id
    return AGENT_MODEL_CATALOG[0].id


def get_catalog_entry(model_id: str) -> AgentModelEntry | None:
    return _CATALOG_BY_ID.get(model_id)


def get_new_user_free_quota(model_id: str) -> int | None:
    """新人免费 Token 额度；无则 None。"""
    if model_id in MODELS_WITH_NEW_USER_FREE_QUOTA:
        return NEW_USER_FREE_QUOTA_TOKENS
    return None


def is_user_whitelist_model(model_id: str) -> bool:
    return model_id in DEFAULT_USER_MODEL_IDS


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
