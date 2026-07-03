"""本地快速检查 MCP 工具注册与状态 API。"""

from __future__ import annotations

from core.tools.build import build_coding_registry
from fastapi.testclient import TestClient

from server.main import app


def main() -> None:
    registry = build_coding_registry("dev", register_mcp=False)
    names = [schema["function"]["name"] for schema in registry.get_schemas()]
    github = [name for name in names if name.startswith("github_")]
    brave = [name for name in names if name.startswith("brave_")]
    print("github tools ->", github)
    print("brave tools ->", brave)

    with TestClient(app) as client:
        response = client.get("/api/mcp/status?ping=false")
        print("status ->", response.status_code, response.json())


if __name__ == "__main__":
    main()
