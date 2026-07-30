"""各模型的特色能力与 Loop 调参（DeepSeek 开放平台）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models.catalog import AUTO_MODEL_ID, get_catalog_entry

# 按 model id 定义；未命中则按 tier 回退
_TIER_DEFAULTS: dict[str, str] = {
    "flash": "flash-default",
    "max": "max-default",
    "auto": "auto-default",
}


@dataclass(frozen=True)
class ModelProfile:
    """模型特色：展示用 features + 运行时行为。"""

    tagline: str
    features: tuple[str, ...]
    skills: tuple[str, ...] = ()
    max_iterations: int = 15
    temperature: float = 0.2
    enable_compression: bool = True
    max_read_chars: int | None = None  # None = 用全局默认
    extra_prompt: str = ""
    prefer_tools: tuple[str, ...] = ()  # 提示 Agent 优先使用的工具
    sequential_thinking: bool = False


_PROFILES: dict[str, ModelProfile] = {
    "auto-default": ModelProfile(
        tagline="智能路由",
        features=("按任务选 Chat/Reasoner", "成本与质量平衡", "多轮工具协作"),
        extra_prompt="简单问题用 deepseek-chat 快速完成；复杂推理再切换到 deepseek-reasoner。",
    ),
    "flash-default": ModelProfile(
        tagline="快速响应",
        features=("低延迟", "日常编程", "高性价比"),
        max_iterations=12,
        temperature=0.2,
        prefer_tools=("read_file", "list_dir", "grep", "get_env_info"),
        extra_prompt="回答简洁高效；优先 read/grep 快速定位问题。",
    ),
    "max-default": ModelProfile(
        tagline="深度推理",
        features=("复杂推理", "架构设计", "分步思考"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.25,
        sequential_thinking=True,
        prefer_tools=(
            "glob_search",
            "grep",
            "read_file",
            "list_dir",
            "brave_web_search",
        ),
        extra_prompt="复杂任务先列出步骤与风险，再分步执行；多文件改动分批确认。",
    ),
    # DeepSeek Chat 专属微调
    "deepseek-chat": ModelProfile(
        tagline="DeepSeek Chat",
        features=("通用编程", "快速响应", "工具调用"),
        max_iterations=15,
        temperature=0.2,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt="平衡质量与效率：改代码后尽量 execute_command 验证。",
    ),
    # DeepSeek Reasoner 专属微调
    "deepseek-reasoner": ModelProfile(
        tagline="DeepSeek Reasoner",
        features=("深度推理", "链式思考", "复杂问题"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.2,
        sequential_thinking=True,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt="像 Staff Engineer：先理解需求与约束，深度思考后再改代码并跑测试。",
    ),
    # MiniMax M2.7 稳定版画像 — 普通用户也能用,max tier
    "MiniMax-M2.7": ModelProfile(
        tagline="MiniMax M2.7",
        features=("工具调用", "代码工程", "稳定主力"),
        skills=("karpathy-guidelines",),
        max_iterations=18,
        temperature=0.25,
        sequential_thinking=True,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt=(
            "你是一位经验丰富的工程师。先理解需求与约束,改完用 execute_command 验证。"
        ),
    ),
    # MiniMax M3 旗舰画像（max tier、admin-only）
    "MiniMax-M3": ModelProfile(
        tagline="MiniMax M3",
        features=("深度推理", "长上下文", "工具调用", "代码工程"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=24,
        temperature=0.3,
        sequential_thinking=True,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep", "glob_search"),
        extra_prompt=(
            "你是一位资深工程师。涉及多文件改动时先列计划再分步执行，"
            "改完用 execute_command 跑测试验证。如需拆解任务，使用 sequential_thinking。"
        ),
    ),
}

# model id → profile key（未列则用 tier-default）
_MODEL_KEYS: dict[str, str] = {
    AUTO_MODEL_ID: "auto-default",
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
    "MiniMax-M2.7": "MiniMax-M2.7",
    "MiniMax-M3": "MiniMax-M3",
}


def get_model_profile(model_id: str | None) -> ModelProfile:
    """解析模型特色配置。"""
    mid = model_id or AUTO_MODEL_ID
    if mid in _PROFILES:
        return _PROFILES[mid]
    key = _MODEL_KEYS.get(mid)
    if key and key in _PROFILES:
        return _PROFILES[key]
    entry = get_catalog_entry(mid)
    if entry:
        tier_key = _TIER_DEFAULTS.get(entry.tier, "flash-default")
        return _PROFILES.get(tier_key, _PROFILES["flash-default"])
    return _PROFILES["flash-default"]


def profile_to_api(model_id: str) -> dict:
    p = get_model_profile(model_id)
    entry = get_catalog_entry(model_id)
    out = {
        "tagline": p.tagline,
        "features": list(p.features),
        "skills": list(p.skills),
        "prefer_tools": list(p.prefer_tools),
        "max_iterations": p.max_iterations,
    }
    if entry is not None:
        out["supports_vision"] = entry.supports_vision
    return out
