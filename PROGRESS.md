# 工作进度与改动记录

> **文档定位：** 记录「做了什么、改了什么」。每完成一小步就在下方追加一条。  
> 总蓝图见 [PLAN.md](./PLAN.md)，快速上手见 [README.md](./README.md)。

**当前阶段：** 阶段 D1 已完成 → 下一步：S2 日志脱敏 / D2 MCP

---

## 如何使用

每完成一项工作，在 **[进度日志](#进度日志)** 最上方（最新在前）追加：

```markdown
### YYYY-MM-DD · 简短标题

- **完成：** 做了什么（1～3 条）
- **涉及文件：** `path/to/file.py` …
- **备注：** 可选（问题、待办、验收方式）
```

阶段大项完成后，同步勾选 **[阶段清单](#阶段清单)**。

---

## 阶段清单

| 阶段 | 状态 | 说明 |
|------|------|------|
| 0 地基 | ✅ | API、示例、目录、环境 |
| A CLI Agent | ✅ | Loop、工具、CLI、日志 |
| B 后端 API | ✅ | FastAPI + SSE + SQLite |
| C Web 前端 | ✅ | MVP + C-2 polish |
| S0 工具安全 | ✅ | policy.py、Shell 白名单、敏感文件 |
| S1 用户确认 | ✅ | Human-in-the-Loop + 速率限制 |
| D1 部署 | ✅ | Docker + Pages 文档 + CORS |
| D 可选功能 | ⬜ | Git、MCP、子 Agent 等 |

---

## 进度日志

<!-- 新的记录写在最上面 -->

### 2026-06-22 · 阶段 D1 完成（部署上线）

- **完成：** Dockerfile、.dockerignore、CORS_ORIGINS、`backend/run.py` 生产模式、`frontend/public/_redirects`、`docs/deploy-frontend.md`、`docs/deploy-backend.md`
- **涉及文件：** `Dockerfile`、`backend/cors.py`、`frontend/src/config.ts`、`.env.example`
- **验收：** `docker build` + `curl /health`；`npm run build` 通过

---

- **完成：** 工具风险分级；Loop confirm_handler；ConfirmationManager + POST /api/chat/confirm；Web ConfirmDialog；CLI `--yes`；速率限制 30/min 100/h
- **涉及文件：** `tools/policy.py`、`agent/loop.py`、`agent/tool_gate.py`、`agent/confirmation.py`、`agent/rate_limit.py`、`backend/`、`frontend/`、`cli.py`、`tests/test_confirmation.py`
- **验收：** `pytest tests/test_confirmation.py -v` 11 项全绿；Web 写文件弹窗确认

---

- **完成：** `tools/policy.py` 统一策略；Shell 白/黑名单；NFKC + symlink 防护；敏感文件拦截；资源限制；pytest 23 项
- **涉及文件：** `tools/policy.py`、`tools/sandbox.py`、`tools/shell.py`、`tools/filesystem.py`、`tools/search.py`、`tests/test_security_policy.py`、`requirements.txt`
- **验收：** `pytest tests/test_security_policy.py -v` 全绿；`read_file(".env")` 返回 `policy: sensitive_file`

---

- **完成：** Reset 按钮、会话重命名 UI（双击内联编辑）、样式 polish、文档同步
- **涉及文件：** `frontend/src/App.tsx`、`api/client.ts`、`components/*`、`PROGRESS.md`、`PLAN.md`、`README.md`
- **验收：** reset / rename 手动测通；`npm run build` 通过

---

### 2026-06-22 · 模型切换 qwen3.6-flash

- **涉及文件：** `config.py`（`MODEL_FLASH` / `MODEL_CODER` → `qwen3.6-flash`）

---

- **完成：**
  - 三栏 Cursor 式布局：左窄侧栏（品牌 + 新对话 + 历史）/ 中栏居中对话 / 右栏可折叠 Agent 时间线
  - 消息改为头像 + 块级排版（非气泡）；底部圆角 Composer + 模型 hint
  - 深色主题 CSS 变量、细滚动条、响应式窄屏侧栏
- **涉及文件：** `frontend/src/App.tsx`、`App.css`、`index.css`、`components/*`
- **验收：** `npm run dev` 浏览器查看布局

---

- **完成：**
  - 关闭 Uvicorn 默认英文 access log，改由中间件输出 `路径 → 状态  --中文说明`
  - Uvicorn 启动/关闭行追加中文说明；推荐 `python -m backend` 启动
- **涉及文件：** `backend/access_log.py`、`backend/middleware/`、`backend/logging_config.py`、`backend/run.py`、`agent/console.py`
- **示例：** `127.0.0.1 GET /api/sessions?user_id=default → 200 (3ms)  --获取会话列表`

---

- **完成：**
  - `frontend/` Vite + React + TS 三栏布局（会话列表 / 聊天 / 工具面板）
  - `fetch` + `ReadableStream` 消费 POST SSE，实时展示 `assistant_reply` 与工具事件
  - Vite proxy `/api` → `127.0.0.1:8765`；进入页自动拉会话，无则创建
  - 切换会话加载 SQLite 历史（user/assistant messages）
- **涉及文件：** `frontend/`、`.gitignore`
- **验收：**
  ```powershell
  python backend/run.py
  cd frontend && npm install && npm run dev
  ```

---

- **完成：**
  - FastAPI 骨架 `backend/main.py`（CORS、lifespan 初始化 SQLite）
  - POST `/api/chat` SSE 流式输出（loop_round / tool_call / assistant_reply / done）
  - 会话 CRUD `/api/sessions`（SQLite 存于 `runtime/db/sessions.sqlite`）
  - `backend/services/agent_service.py` 封装 `CodingAgent`，线程 + 队列推 SSE
  - `ActivityLogger.on_event` 钩子；`Session.persist_json=False` 供 API 模式
- **涉及文件：** `backend/`、`agent/activity.py`、`agent/memory.py`、`agent/coding_agent.py`、`user/paths.py`、`requirements.txt`
- **验收：**
  ```powershell
  python backend/run.py
  curl http://127.0.0.1:8765/health
  # POST /api/sessions 创建会话 → POST /api/chat 流式对话
  ```

---

- **完成：**
  - CLI 默认只显示 `You>` / `Agent>`，过程不再刷屏
  - 工具调用、Loop 轮次、完整 tool 返回值写入 `runtime/logs/`
  - 新增 `--verbose` 可在终端看详细过程
  - 大总管 `view_activity.py` 支持新日志事件类型
- **涉及文件：** `cli.py`、`agent/loop.py`、`agent/activity.py`、`user/admin/view_activity.py`、`.cursor/rules/terminal-output-zh.mdc`
- **备注：** 查过程用 `python user/admin/view_activity.py -u default`

---

### 2026-06-22 · 阶段 A 完成（CLI 编程 Agent）

- **完成：**
  - 系统提示词 `agent/prompts.py`
  - 搜索工具 `grep` / `glob_search`（`tools/search.py`）
  - 命令执行 `execute_command`（`tools/shell.py`）
  - 多轮会话 `agent/memory.py`（可持久化到 runtime/sessions）
  - 编程 Agent 组装 `agent/coding_agent.py`
  - CLI 入口 `cli.py`（多轮 REPL，exit / /reset）
  - 工具统一注册 `tools/build.py`、沙箱共用 `tools/sandbox.py`
- **涉及文件：** `agent/`、`tools/`、`cli.py`
- **验收：** `python cli.py` 可在沙箱内读写文件、跑命令

---

### 2026-06-22 · Agent 核心 Loop + 文件工具

- **完成：**
  - 通用 Agentic Loop `agent/loop.py`
  - 工具注册表 `tools/registry.py`
  - 文件工具 read / write / edit / list_dir（`tools/filesystem.py`）
  - 演示 `examples/filesystem_agent.py`
- **涉及文件：** `agent/loop.py`、`tools/filesystem.py`、`tools/registry.py`
- **验收：** demo 可在沙箱内创建 `hello.py`

---

### 2026-06-22 · runtime/ 运行时目录

- **完成：**
  - 新建 `runtime/` 存放测试/运行生成物（沙箱、日志、汇总）
  - `user/` 只保留大总管脚本等源码
  - 更新 `user/paths.py` 路径指向 runtime
- **涉及文件：** `runtime/`、`user/paths.py`、`.gitignore`
- **备注：** 生成物不入库，可随时清空 runtime（保留 `.gitkeep`）

---

### 2026-06-22 · 用户系统 + 活动日志

- **完成：**
  - `user/` 大总管脚本、`ActivityLogger`（`agent/activity.py`）
  - JSONL 活动日志、`view_activity.py` 查看
  - 演示 `examples/demo_activity.py`
- **涉及文件：** `user/`、`agent/activity.py`

---

### 2026-06-22 · 环境与配置

- **完成：**
  - 百炼 Qwen API 配置（`config.py`）
  - `.env` 持久化密钥、`scripts/check_env.py` 一键检查
  - `requirements.txt`（openai、python-dotenv）
- **涉及文件：** `config.py`、`.env.example`、`scripts/check_env.py`

---

### 2026-06-22 · 项目初始化

- **完成：**
  - 工作区整理，删除无关教程 HTML
  - 最小 Agent 示例 `examples/weather_agent.py`（天气 + Function Calling）
  - 终端输出工具 `agent/console.py`
  - 总规划文档 `PLAN.md`
- **涉及文件：** 项目骨架、`PLAN.md`、`README.md`

---

## 下一步（待做）

- [ ] S2：日志脱敏
- [ ] D2：MCP 集成（可选）
- [ ] S3：JWT 多用户（可选）

---

## 相关文档

| 文档 | 用途 |
|------|------|
| [PLAN.md](./PLAN.md) | 架构与阶段总规划 |
| [README.md](./README.md) | 安装、运行命令 |
| [user/README.md](./user/README.md) | 用户系统与日志说明 |
