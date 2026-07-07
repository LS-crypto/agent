"""外部 MCP / API 密钥配置（GitHub · Brave）。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from core.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

GITHUB_API_BASE = "https://api.github.com"
BRAVE_API_BASE = "https://api.search.brave.com/res/v1"


@dataclass(frozen=True)
class GitHubMCPConfig:
    token: str | None
    default_repo: str | None
    api_version: str = "2022-11-28"

    @property
    def configured(self) -> bool:
        return bool(self.token and self.token.strip())


@dataclass(frozen=True)
class BraveMCPConfig:
    api_key: str | None
    default_count: int = 5

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())


def get_github_config() -> GitHubMCPConfig:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    repo = os.getenv("GITHUB_DEFAULT_REPO")
    return GitHubMCPConfig(token=token, default_repo=repo)


def get_brave_config() -> BraveMCPConfig:
    key = os.getenv("BRAVE_API_KEY")
    count_raw = os.getenv("BRAVE_SEARCH_COUNT", "5")
    try:
        count = max(1, min(int(count_raw), 20))
    except ValueError:
        count = 5
    return BraveMCPConfig(api_key=key, default_count=count)


def get_builtin_mcp_url() -> str:
    host = os.getenv("MCP_BUILTIN_HOST", "127.0.0.1")
    port = os.getenv("MCP_BUILTIN_PORT", "9000")
    return f"http://{host}:{port}"
