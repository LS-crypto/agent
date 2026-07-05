# Sheldon Agent

基于阿里云百炼 Qwen API 的全栈编程 Agent。

## 目录结构

```
sheldon-agent/
├── pyproject.toml      # uv 项目配置
├── uv.lock             # 依赖锁文件
├── .env.example        # 环境变量模板
│
├── apps/               # 应用层（面向用户的入口）
│   ├── cli/            # 命令行版
│   └── web/            # Web 前端（React + Vite）
│
├── server/             # Web 后端（FastAPI + SSE）
├── core/               # 共享核心（Agent、工具、Skills）
│   ├── agent/
│   ├── tools/
│   ├── skills/
│   ├── user/
│   └── config.py
│
├── tests/              # 测试（与业务代码分离）
├── deploy/             # Docker 与部署文件
├── docs/               # 文档
├── scripts/            # 开发脚本
├── examples/           # 可运行示例
└── runtime/            # 运行时数据（沙箱、日志，不入库）
```

工作区根目录另有 [开发日志.md](../开发日志.md)、[任务清单.md](../任务清单.md)。

## 环境（uv）

```powershell
cd D:\system\Sheldon-Shuo-Agent\sheldon-agent
uv sync --dev
copy .env.example .env          # 填入 DASHSCOPE_API_KEY
uv run python scripts/check_env.py
```

若 `uv sync` 因网络/DNS 失败，可暂用系统 Python（需已安装依赖）：

```powershell
pip install openai python-dotenv fastapi "uvicorn[standard]" pydantic pytest
python -m pytest tests/ -q
python -m apps.cli --help
```

## 运行

```powershell
# 命令行版
uv run python -m apps.cli

# Web 后端
uv run python -m server

# Web 前端（另开终端）
cd apps/web
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。

**公网使用说明（已部署）：** 见 [docs/用户使用说明.md](docs/用户使用说明.md) · 访问 http://118.178.144.109/

## 模型切换

采用 **B 为主（静态择优目录）+ A 为辅（远程可用性校验）**：

| 入口 | 用法 |
|------|------|
| Web | Composer 左下角下拉：「自动路由」或固定模型（按会话持久化） |
| CLI | `--model qwen3.7-plus` 固定模型；默认 `auto` 启用复杂度路由 |
| API | `GET /api/models?check_remote=true` 获取目录；`PATCH /api/sessions/{id}/model` 切换 |

```powershell
# 列出可用模型
uv run python -m apps.cli --list-models

# 固定使用 Plus
uv run python -m apps.cli --model qwen3.7-plus

# 自动路由（按任务选 Flash / Plus / Max）
uv run python -m apps.cli
```

目录定义见 `core/models/catalog.py`（仅收录对话 + 工具调用模型，不含 embedding/图像等）。

## 外部 MCP 工具（GitHub · Brave）

在 `.env` 配置 Token 后，Agent 可调用 GitHub / Brave 工具；状态探测：`GET /api/mcp/status?ping=true`。

| 变量 | 说明 |
|------|------|
| `GITHUB_TOKEN` | GitHub PAT（Issues/PR/代码搜索只读） |
| `GITHUB_DEFAULT_REPO` | 可选，默认 `owner/repo` |
| `BRAVE_API_KEY` | Brave Search API Key |
| `BRAVE_SEARCH_COUNT` | 默认返回条数（1–20） |

| 工具 | 风险 | 说明 |
|------|------|------|
| `github_search_issues` | allowed | 按 repo + 关键词搜 Issue |
| `github_get_issue` | allowed | Issue 详情 + 评论摘要 |
| `github_list_pulls` / `github_get_pull` | allowed | PR 列表 / 详情 |
| `github_search_code` | allowed | 仓库内代码搜索（限流严） |
| `brave_web_search` | review | 联网 Web 搜索 |
| `brave_news_search` | review | 联网新闻搜索 |

演示脚本：`uv run python examples/mcp_github_brave_demo.py`

Max 模型（`qwen-max` / `qwen3-max` / auto 路由）会通过 SSE 发送 `thinking_step` 事件（分步推理）；前端 ThinkingPanel 待后续 UI 阶段接入。

## 测试

```powershell
uv run pytest tests/ -v
uv run python scripts/smoke_local.py    # 本地 API 联调冒烟
powershell -File scripts/ci.ps1         # CI：pytest + Web build + Docker health
```

## Docker 部署（阿里云 ECS）

```powershell
docker build -f deploy/Dockerfile -t sheldon-agent:1.0.0 .
```

详见 [docs/deploy-ecs.md](./docs/deploy-ecs.md) 与工作区 [12-AI编程工具部署引导.md](../12-AI编程工具部署引导.md)。

## 后续规划

| 端 | 目录 | 状态 |
|----|------|------|
| CLI | `apps/cli` | ✅ |
| Web | `apps/web` + `server` | ✅ |
| 桌面 | 待定（Tauri 等） | 见 [任务清单.md](../任务清单.md) |
| 小程序 | 待定 | 见 [任务清单.md](../任务清单.md) |
