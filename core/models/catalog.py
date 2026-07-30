"""Agent 可用模型目录（DeepSeek + MiniMax 开放平台）。"""

from __future__ import annotations

from dataclasses import dataclass

AUTO_MODEL_ID = "auto"

# 普通用户默认可选模型（admin 不受限；可通过 USER_ALLOWED_MODELS 覆盖）
NEW_USER_FREE_QUOTA_TOKENS = 1_000_000
NEW_USER_FREE_QUOTA_DAYS = 30

# 普通用户默认可选模型（admin 不受限；可通过 USER_ALLOWED_MODELS 覆盖）。
#   - deepseek-chat:  低价 DeepSeek,所有人能用
#   - MiniMax-M2.7:    稳定版 MiniMax,普通用户也能用(免费配额 / 自带 Key 都行)
# MiniMax-M3 不在白名单内 — 旗舰新版默认仅管理员可用,由 model_policy 强制。
DEFAULT_USER_MODEL_IDS: tuple[str, ...] = (
    "deepseek-chat",
    "MiniMax-M2.7",
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


# DeepSeek + MiniMax 开放平台模型目录
# 普通用户的可见性由 DEFAULT_USER_MODEL_IDS 控制（白名单外对 user 返回 403），
# 管理员默认能看到全部条目。
AGENT_MODEL_CATALOG: tuple[AgentModelEntry, ...] = (
    AgentModelEntry(
        id="deepseek-chat",
        label="DeepSeek Chat",
        group="通用",
        tier="flash",
        max_tokens=64000,
        description="V3 通用编程，快速响应，适合日常开发任务",
        is_default=True,
    ),
    AgentModelEntry(
        id="deepseek-reasoner",
        label="DeepSeek Reasoner",
        group="DeepSeek",
        tier="plus",
        max_tokens=64000,
        description="R1 深度推理，长链思考与复杂问题",
    ),
    AgentModelEntry(
        id="MiniMax-M2.7",
        label="MiniMax M2.7",
        group="MiniMax",
        tier="max",
        max_tokens=8192,
        description="MiniMax 稳定版主力模型；工具调用 + 推理，普通用户默认可用",
        supports_tools=True,
        supports_vision=False,
    ),
    AgentModelEntry(
        id="MiniMax-M3",
        label="MiniMax M3",
        group="MiniMax",
        tier="max",
        max_tokens=8192,
        description="MiniMax 最新旗舰模型（admin-only）；深度推理 + 长上下文代码工作",
        supports_tools=True,
        supports_vision=False,
    ),
)

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
