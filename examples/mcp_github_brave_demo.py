#!/usr/bin/env python3
"""演示 GitHub MCP + Brave Search 工具（Mock 友好，需配置 .env 才能真连）。"""

from __future__ import annotations

import json
import os
import sys

# 项目根
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp.status import list_mcp_status
from core.tools.brave_search import BraveSearchTools
from core.tools.github_mcp import GitHubMCPTools


def main() -> int:
    print("=== MCP 状态 ===")
    status = list_mcp_status(ping=False)
    print(json.dumps(status, ensure_ascii=False, indent=2))

    gh = GitHubMCPTools()
    br = BraveSearchTools()

    print("\n=== GitHub 搜索 Issue（需 GITHUB_TOKEN + GITHUB_DEFAULT_REPO）===")
    r1 = gh.github_search_issues("bug", limit=3)
    print(json.dumps(r1, ensure_ascii=False, indent=2)[:800])

    print("\n=== Brave Web 搜索（需 BRAVE_API_KEY）===")
    r2 = br.brave_web_search("Model Context Protocol", count=3)
    print(json.dumps(r2, ensure_ascii=False, indent=2)[:800])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
