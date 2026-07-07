"""热门 MCP Server 目录（GitHub 参考 + 内置实现对照）。"""

from __future__ import annotations

from typing import Any

# 参考 modelcontextprotocol/servers、github/github-mcp-server 及社区高星项目
MCP_SERVER_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "sheldon-builtin",
        "name": "Sheldon 内置 MCP",
        "repo": "本项目 core/mcp/builtin_server.py",
        "stars_hint": "内置",
        "description": "Time · Fetch · Memory · Calculate · 磁盘 · Skills",
        "transport": "http",
        "default_url": "http://127.0.0.1:9000",
        "builtin": True,
        "tools": [
            "get_current_time",
            "fetch_url",
            "memory_note_save",
            "memory_note_search",
            "calculate",
            "get_disk_usage",
            "list_skills",
        ],
    },
    {
        "id": "filesystem",
        "name": "MCP Filesystem",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        "stars_hint": "官方",
        "description": "受控目录内读写（Sheldon 已用沙箱工具替代）",
        "transport": "stdio",
        "tools_hint": ["read_file", "write_file", "list_directory"],
    },
    {
        "id": "fetch",
        "name": "MCP Fetch",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
        "stars_hint": "官方",
        "description": "URL 抓取；Sheldon 内置 fetch_url（域名白名单）",
        "transport": "stdio",
        "sheldon_compat": "fetch_url",
    },
    {
        "id": "memory",
        "name": "MCP Memory",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
        "stars_hint": "官方",
        "description": "知识图谱记忆；Sheldon 内置 memory_note_*",
        "transport": "stdio",
        "sheldon_compat": ["memory_note_save", "memory_note_search"],
    },
    {
        "id": "time",
        "name": "MCP Time",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/time",
        "stars_hint": "官方",
        "description": "时区与时间；Sheldon 内置 get_current_time",
        "transport": "stdio",
        "sheldon_compat": "get_current_time",
    },
    {
        "id": "github",
        "name": "GitHub MCP Server",
        "repo": "https://github.com/github/github-mcp-server",
        "stars_hint": "10k+",
        "description": "Issues、PR、代码搜索、仓库管理（需 GITHUB_TOKEN）",
        "transport": "stdio",
        "env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    },
    {
        "id": "brave-search",
        "name": "Brave Search MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
        "stars_hint": "官方",
        "description": "Web 搜索 API（需 BRAVE_API_KEY）",
        "transport": "stdio",
        "env": ["BRAVE_API_KEY"],
    },
    {
        "id": "sqlite",
        "name": "SQLite MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
        "stars_hint": "官方",
        "description": "只读 SQL 查询本地 SQLite 文件",
        "transport": "stdio",
    },
    {
        "id": "postgres",
        "name": "PostgreSQL MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
        "stars_hint": "官方",
        "description": "只读 PostgreSQL 查询",
        "transport": "stdio",
    },
    {
        "id": "slack",
        "name": "Slack MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
        "stars_hint": "官方",
        "description": "频道消息与搜索（需 Slack Bot Token）",
        "transport": "stdio",
    },
    {
        "id": "puppeteer",
        "name": "Puppeteer MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
        "stars_hint": "官方",
        "description": "无头浏览器截图与页面交互",
        "transport": "stdio",
    },
    {
        "id": "sequential-thinking",
        "name": "Sequential Thinking MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking",
        "stars_hint": "社区",
        "description": "分步推理链（适合 Max 档模型配合）",
        "transport": "stdio",
    },
    {
        "id": "everything",
        "name": "MCP Everything (Demo)",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/everything",
        "stars_hint": "官方示例",
        "description": "SDK 演示服务器，含 echo、采样等",
        "transport": "stdio",
    },
    {
        "id": "google-drive",
        "name": "Google Drive MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive",
        "stars_hint": "官方",
        "description": "Google 云端硬盘文件（需 OAuth）",
        "transport": "stdio",
    },
    {
        "id": "aws-kb",
        "name": "AWS Knowledge Base MCP",
        "repo": "https://github.com/modelcontextprotocol/servers/tree/main/src/aws-kb-retrieval-server",
        "stars_hint": "官方",
        "description": "AWS Bedrock 知识库检索",
        "transport": "stdio",
    },
)


def list_mcp_catalog() -> dict[str, Any]:
    builtin = [s for s in MCP_SERVER_CATALOG if s.get("builtin")]
    external = [s for s in MCP_SERVER_CATALOG if not s.get("builtin")]
    return {
        "servers": list(MCP_SERVER_CATALOG),
        "builtin_count": len(builtin),
        "external_count": len(external),
        "env_hint": (
            "内置 HTTP: MCP_BUILTIN=1 默认 :9000；"
            "外部 stdio 服务器需 MCP_ENABLED=1 与对应 Token"
        ),
    }
