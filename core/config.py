"""阿里云百炼（DashScope）按量付费 API 配置。"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 启动时自动加载项目根目录 .env（关终端后无需重设密钥）
from core.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

# 百炼国内控制台 Key 使用此 endpoint
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# ---------- 模型注册表 ----------

@dataclass(frozen=True)
class ModelConfig:
    """单个模型的配置。"""
    name: str
    max_tokens: int = 8192
    cost_input_per_1k: float = 0.0
    cost_output_per_1k: float = 0.0


# 三层模型：路由 → 简单任务 → 标准任务 → 复杂任务
MODEL_TIERS: dict[str, ModelConfig] = {
    "flash": ModelConfig("qwen3.6-flash", max_tokens=8192,
                         cost_input_per_1k=0.0003, cost_output_per_1k=0.0006),
    "plus":  ModelConfig("qwen3.7-plus", max_tokens=32768,
                         cost_input_per_1k=0.004, cost_output_per_1k=0.012),
    "max":   ModelConfig("qwen-max", max_tokens=32768,
                         cost_input_per_1k=0.04, cost_output_per_1k=0.12),
}

# 默认模型 tier（Agent 主模型，默认 qwen3.7-plus）
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


def create_client(api_key: str | None = None) -> OpenAI:
    key = api_key or os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY，或在代码中传入 api_key")
    return OpenAI(api_key=key, base_url=BAILIAN_BASE_URL)


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
