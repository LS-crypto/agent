"""LLM Provider 配置（DeepSeek 开放平台 + MiniMax 开放平台）。"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 启动时自动加载项目根目录 .env（关终端后无需重设密钥）
from core.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

# ---------- Provider 标识 ----------

# Provider 名称常量（与 server/repositories/user_secrets.py 同名常量子串保持一致）
PROVIDER_DEEPSEEK = "deepseek"
PROVIDER_MINIMAX = "minimax"

# DeepSeek 开放平台 OpenAI 兼容端点
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# MiniMax 开放平台 OpenAI 兼容端点（默认，可由环境变量 MINIMAX_BASE_URL 覆盖）
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.MiniMax.chat/v1")

# 端点 → API Key 环境变量名 的映射
_API_KEY_ENV: dict[str, str] = {
    PROVIDER_DEEPSEEK: "DEEPSEEK_API_KEY",
    PROVIDER_MINIMAX: "MINIMAX_API_KEY",
}


# ---------- 模型 → Provider 路由表 ----------

# 显式声明每个可调用模型属于哪个 Provider；未命中时按 fallback 处理。
# 注意：MiniMax-M2.7（稳定版，所有人可用）与 MiniMax-M3（新版，仅管理员）都走同一个
# MiniMax 端点，靠上层白名单（catalog.DEFAULT_USER_MODEL_IDS）区分可见性。
_MODEL_PROVIDER: dict[str, str] = {
    "deepseek-chat": PROVIDER_DEEPSEEK,
    "deepseek-reasoner": PROVIDER_DEEPSEEK,
    "MiniMax-M2.7": PROVIDER_MINIMAX,
    "MiniMax-M3": PROVIDER_MINIMAX,
}


def get_provider_for_model(model_id: str | None) -> str:
    """根据模型 id 解析所属 Provider；未命中则按 deepseek 处理。"""
    if model_id and model_id in _MODEL_PROVIDER:
        return _MODEL_PROVIDER[model_id]
    return PROVIDER_DEEPSEEK


def get_base_url_for_provider(provider: str) -> str:
    if provider == PROVIDER_MINIMAX:
        return MINIMAX_BASE_URL
    return DEEPSEEK_BASE_URL


def get_api_key_env_for_provider(provider: str) -> str:
    return _API_KEY_ENV.get(provider, "DEEPSEEK_API_KEY")


# ---------- 模型注册表 ----------

@dataclass(frozen=True)
class ModelConfig:
    """单个模型的配置。"""
    name: str
    max_tokens: int = 8192
    cost_input_per_1k: float = 0.0
    cost_output_per_1k: float = 0.0


# 三层模型：路由 → 简单任务 → 标准任务 → 复杂任务
# "max" 槽位保留给当前最强模型：MiniMax-M3（新接入、推理 + 工具调用能力强），
# 复杂任务默认走它。Flash / Plus 仍由 DeepSeek 提供以保持低成本。
MODEL_TIERS: dict[str, ModelConfig] = {
    "flash": ModelConfig("deepseek-chat", max_tokens=8192,
                         cost_input_per_1k=0.00014, cost_output_per_1k=0.00028),
    "plus":  ModelConfig("deepseek-chat", max_tokens=64000,
                         cost_input_per_1k=0.00014, cost_output_per_1k=0.00028),
    "max":   ModelConfig("MiniMax-M3", max_tokens=8192,
                         cost_input_per_1k=0.003, cost_output_per_1k=0.003),
}

# 默认模型 tier（Agent 主模型，默认 plus → deepseek-chat）
DEFAULT_TIER = os.getenv("DEFAULT_MODEL_TIER", "plus")


def get_model_name(tier: str) -> str:
    """根据 tier 名称获取模型名，不存在则 fallback 到 DEFAULT_TIER。"""
    cfg = MODEL_TIERS.get(tier)
    if cfg:
        return cfg.name
    fallback = MODEL_TIERS.get(DEFAULT_TIER)
    return fallback.name if fallback else MODEL_TIERS["plus"].name


# 兼容旧常量
MODEL_FLASH = MODEL_TIERS["flash"].name
MODEL_PLUS = MODEL_TIERS["plus"].name
MODEL_CODER = get_model_name(DEFAULT_TIER)


def create_client(
    api_key: str | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> OpenAI:
    """构建 OpenAI 兼容客户端。

    优先级解析：
    1) 显式 provider 参数
    2) 由 model 推断
    3) fallback deepseek
    api_key 缺省时读对应 Provider 的环境变量。
    """
    resolved = provider or get_provider_for_model(model)
    base_url = get_base_url_for_provider(resolved)
    env_name = get_api_key_env_for_provider(resolved)
    key = api_key or os.getenv(env_name)
    if not key:
        raise ValueError(
            f"请设置环境变量 {env_name}（provider={resolved}），或在代码中传入 api_key"
        )
    return OpenAI(api_key=key, base_url=base_url)


# ---------- MCP 配置 ----------

@dataclass(frozen=True)
class MCPConfig:
    enabled: bool = False
    http_url: str | None = None
    sdk_transport: str | None = None
    # 可选：当使用本地 clone 的 SDK 时，指定其路径（用于调试）
    sdk_path: str | None = None


def get_mcp_config() -> MCPConfig:
    enabled = os.getenv("MCP_ENABLED", "false").lower() in ("1", "true", "yes")
    http_url = os.getenv("MCP_HTTP_URL")
    sdk_transport = os.getenv("MCP_SDK_TRANSPORT")
    sdk_path = os.getenv("MCP_SDK_PATH")
    return MCPConfig(enabled=enabled, http_url=http_url, sdk_transport=sdk_transport, sdk_path=sdk_path)
