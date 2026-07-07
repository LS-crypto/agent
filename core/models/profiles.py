"""各模型的特色能力与 Loop 调参（固定模型或 auto 路由时生效）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models.catalog import AUTO_MODEL_ID, get_catalog_entry

# 按 model id 定义；未命中则按 tier 回退
_TIER_DEFAULTS: dict[str, str] = {
    "flash": "flash-default",
    "plus": "plus-default",
    "coder": "coder-default",
    "max": "max-default",
    "long": "long-default",
    "deepseek": "deepseek-default",
    "glm": "glm-default",
    "vision": "vision-default",
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
        features=("按任务选 Flash/Plus/Max", "成本与质量平衡", "多轮工具协作"),
        extra_prompt="简单问题用轻量工具快速完成；复杂编码再深入读写与执行。",
    ),
    "flash-default": ModelProfile(
        tagline="闪电模式",
        features=("极速响应", "只读优先", "低延迟低成本"),
        max_iterations=8,
        temperature=0.1,
        prefer_tools=("read_file", "list_dir", "grep", "get_env_info"),
        extra_prompt="回答简洁；优先 list/read/grep，避免不必要的 write 与长命令。",
    ),
    "plus-default": ModelProfile(
        tagline="日常编程",
        features=("读写代码", "测试验证", "Git 只读"),
        skills=("karpathy-guidelines",),
        prefer_tools=("read_file", "edit_file", "execute_command", "pytest"),
        extra_prompt="平衡质量与效率：改代码后尽量 execute_command 验证。",
    ),
    "coder-default": ModelProfile(
        tagline="代码专家",
        features=("重构优化", "Diff 审查", "自动 code-review 技能"),
        skills=("code-review", "karpathy-guidelines"),
        max_iterations=18,
        temperature=0.15,
        prefer_tools=("read_file", "edit_file", "git_diff", "grep", "execute_command"),
        extra_prompt="专注代码质量：修改前 read_file/git_diff，改后 pytest 或运行脚本验证。",
    ),
    "max-default": ModelProfile(
        tagline="架构推理",
        features=("多步规划", "复杂重构", "深度推理", "分步思考可视化"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=20,
        temperature=0.25,
        sequential_thinking=True,
        prefer_tools=(
            "glob_search",
            "grep",
            "read_file",
            "list_dir",
            "github_search_issues",
            "brave_web_search",
        ),
        extra_prompt="复杂任务先列出步骤与风险，再分步执行；多文件改动分批确认。",
    ),
    "long-default": ModelProfile(
        tagline="长上下文",
        features=("大仓库扫描", "宽文件读取", "分批归纳"),
        max_iterations=18,
        max_read_chars=120_000,
        enable_compression=False,
        prefer_tools=("glob_search", "list_dir", "read_file", "grep"),
        extra_prompt="适合大型目录：先 glob/list 摸清结构，再分批 read；最后汇总结论。",
    ),
    "deepseek-default": ModelProfile(
        tagline="DeepSeek 推理",
        features=("编程数学", "深度思考", "百万上下文"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.2,
        sequential_thinking=True,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt="复杂问题先规划再动手；代码改动小步验证。",
    ),
    "glm-default": ModelProfile(
        tagline="GLM 长程",
        features=("1M 上下文", "长文档分析", "工具流式"),
        max_iterations=22,
        max_read_chars=120_000,
        temperature=0.2,
        sequential_thinking=True,
        prefer_tools=("glob_search", "read_file", "grep", "list_dir"),
        extra_prompt="充分利用长上下文：跨文件对照后再给结论。",
    ),
    "vision-default": ModelProfile(
        tagline="视觉 Agent",
        features=("界面/OCR 理解", "Visual Coding", "图文工具协作"),
        max_iterations=16,
        temperature=0.15,
        prefer_tools=("read_file", "write_file", "fetch_url", "grep"),
        extra_prompt="当前会话为纯文本；若用户描述 UI/截图场景，先 read 相关前端文件再建议。",
    ),
    # 单模型微调（覆盖 tier 默认）
    "qwen3.6-flash": ModelProfile(
        tagline="闪电问答",
        features=("毫秒级首 token", "FAQ/查文件", "省 Token"),
        max_iterations=6,
        temperature=0.05,
        prefer_tools=("read_file", "list_dir", "get_disk_usage"),
        extra_prompt="极短回答；能一句话说清不要展开。",
    ),
    "qwen3-coder-plus": ModelProfile(
        tagline="代码旗舰",
        features=("跨文件重构", "测试驱动", "Code Review 技能"),
        skills=("code-review", "safe-shell"),
        max_iterations=20,
        temperature=0.12,
        prefer_tools=("edit_file", "git_diff", "execute_command"),
        extra_prompt="像 Senior Engineer：小步提交式修改，每步可验证。",
    ),
    "qwen3-max": ModelProfile(
        tagline="旗舰推理",
        features=("系统设计", "权衡分析", "长链推理"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.3,
        extra_prompt="给出方案对比（优缺点）再动手；关键决策说明理由。",
    ),
    "qwen-long": ModelProfile(
        tagline="海量上下文",
        features=("整库浏览", "宽读取 120K 字符", "弱压缩保留细节"),
        max_iterations=20,
        max_read_chars=120_000,
        enable_compression=False,
        skills=("disk-storage",),
        extra_prompt="充分利用长上下文：多文件对照后再结论。",
    ),
    "qwen3.7-max": ModelProfile(
        tagline="3.7 旗舰",
        features=("Agent 全能", "内置工具", "深度推理"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.28,
        sequential_thinking=True,
        extra_prompt="优先给出可执行方案，再分步调用工具验证。",
    ),
    "deepseek-v4-pro": ModelProfile(
        tagline="DeepSeek 旗舰",
        features=("编程/数学", "思考模式", "Function Calling"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.2,
        sequential_thinking=True,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt="像 Staff Engineer：先理解需求与约束，再改代码并跑测试。",
    ),
    "deepseek-v4-flash": ModelProfile(
        tagline="DeepSeek 极速",
        features=("低延迟", "经济推理", "工具调用"),
        max_iterations=12,
        temperature=0.12,
        prefer_tools=("read_file", "list_dir", "grep"),
        extra_prompt="快速完成任务，避免过度展开。",
    ),
    "glm-5.2": ModelProfile(
        tagline="GLM 长程专家",
        features=("1M 上下文", "长文档/代码", "混合推理"),
        skills=("karpathy-guidelines",),
        max_iterations=22,
        max_read_chars=120_000,
        temperature=0.2,
        sequential_thinking=True,
        prefer_tools=("glob_search", "read_file", "grep", "edit_file"),
        extra_prompt="大仓库先列结构再逐文件分析。",
    ),
    "glm-5.1": ModelProfile(
        tagline="GLM 增强",
        features=("长上下文", "工具流式", "结构化输出"),
        max_iterations=18,
        temperature=0.18,
        prefer_tools=("read_file", "edit_file", "execute_command"),
        extra_prompt="修改代码后尽量本地验证。",
    ),
    "qwen3-vl-plus": ModelProfile(
        tagline="视觉旗舰",
        features=("图像/视频", "Visual Coding", "空间感知"),
        max_iterations=18,
        prefer_tools=("read_file", "write_file", "fetch_url"),
        extra_prompt="涉及 UI/截图时结合 read_file 查看前端源码。",
    ),
    "qwen3-vl-flash": ModelProfile(
        tagline="视觉闪电",
        features=("快速识图", "低成本", "工具调用"),
        max_iterations=10,
        temperature=0.1,
        prefer_tools=("read_file", "list_dir"),
        extra_prompt="简洁回答视觉相关问题。",
    ),
    "qwen-vl-max": ModelProfile(
        tagline="经典视觉 Max",
        features=("OCR", "图表", "多图理解"),
        max_iterations=16,
        prefer_tools=("read_file", "grep", "fetch_url"),
        extra_prompt="描述图像内容时结构化输出要点。",
    ),
    "qwen-vl-plus": ModelProfile(
        tagline="视觉 Plus",
        features=("均衡视觉", "文档理解", "工具协作"),
        max_iterations=14,
        prefer_tools=("read_file", "list_dir"),
        extra_prompt="图文混合任务先确认文件路径再读取。",
    ),
}

# model id → profile key（未列则用 tier-default）
_MODEL_KEYS: dict[str, str] = {
    AUTO_MODEL_ID: "auto-default",
    "qwen3.6-flash": "qwen3.6-flash",
    "qwen-turbo": "flash-default",
    "qwen3.7-plus": "plus-default",
    "qwen-plus": "plus-default",
    "qwen3-coder-plus": "qwen3-coder-plus",
    "qwen-coder-turbo": "coder-default",
    "qwen-max": "max-default",
    "qwen3-max": "qwen3-max",
    "qwen3.7-max": "qwen3.7-max",
    "qwen-long": "qwen-long",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek-v4-flash": "deepseek-v4-flash",
    "glm-5.2": "glm-5.2",
    "glm-5.1": "glm-5.1",
    "qwen3-vl-plus": "qwen3-vl-plus",
    "qwen3-vl-flash": "qwen3-vl-flash",
    "qwen-vl-max": "qwen-vl-max",
    "qwen-vl-plus": "qwen-vl-plus",
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
        tier_key = _TIER_DEFAULTS.get(entry.tier, "plus-default")
        return _PROFILES.get(tier_key, _PROFILES["plus-default"])
    return _PROFILES["plus-default"]


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
