# 后端部署 — Docker + Railway / Fly.io

## 架构

| 组件 | 选型 | 说明 |
|------|------|------|
| 运行时 | Docker | 项目根 `Dockerfile` |
| 平台 | **Railway** 或 **Fly.io** | 需长连接 SSE + 文件系统 |
| 数据 | SQLite + `runtime/` | 挂载 volume 持久化 |

**禁止：** Cloudflare Workers / AWS Lambda（无长连接 SSE、无持久 FS）。

## 1. 本地 Docker 冒烟测试

```powershell
cd D:\system\TEST\qwen-agent

docker build -t qwen-agent .

docker run --rm -p 8765:8765 `
  -e DASHSCOPE_API_KEY=sk-你的密钥 `
  -e CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 `
  -e HOST=0.0.0.0 `
  -e UVICORN_RELOAD=0 `
  qwen-agent

curl http://localhost:8765/health
# 期望: {"status":"ok"}
```

带数据持久化：

```powershell
docker run --rm -p 8765:8765 `
  -v ${PWD}/runtime:/app/runtime `
  -e DASHSCOPE_API_KEY=sk-... `
  -e CORS_ORIGINS=https://your-app.pages.dev `
  qwen-agent
```

## 2. 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | ✅ | 百炼 API Key |
| `CORS_ORIGINS` | 生产 ✅ | 逗号分隔，如 `https://app.xxx.com,https://xxx.pages.dev` |
| `HOST` | 可选 | 默认 `0.0.0.0`（Docker 已设） |
| `PORT` | 可选 | 平台注入，默认 `8765` |
| `UVICORN_RELOAD` | 可选 | 生产 `0`，开发 `1` |

`.env` 不入库；在 Railway/Fly 控制台配置。

## MCP（Model Context Protocol）配置

该项目支持两类 MCP 源：

- MCP-like HTTP 服务：后端会探测 `MCP_HTTP_URL` 或 `http://localhost:9000`，并通过 `/tools` 获取工具 schema、通过 `/call` 调用工具。
- MCP Python SDK：可将 `modelcontextprotocol/python-sdk` 安装到运行环境，或通过 `MCP_SDK_PATH` 指向本地源码以便导入调试。

推荐本地开发流程：

1. 本地快速测试（不依赖外网 SDK）：启动内置示例服务器 `mcp_servers/local_filesystem_mcp.py`：

```powershell
python -c "from mcp_servers.local_filesystem_mcp import run; run(9000)"
```

2. 启动后端（或运行集成测试），后端会在 lifespan 中探测并注册工具：

```powershell
python -m backend
```

使用 SDK（可选）：

```powershell
# 克隆 SDK（示例位置）
git clone https://github.com/modelcontextprotocol/python-sdk.git mcp_servers/python-sdk
cd mcp_servers/python-sdk
python -m venv .venv
.venv\Scripts\python -m pip install -e .[cli]

# 如果希望在主仓库直接导入 SDK 源，设置环境变量：
setx MCP_SDK_PATH "D:\\system\\TEST\\qwen-agent\\mcp_servers\\python-sdk\\src"
```

后端根据 `MCP_SDK_TRANSPORT`（可选）尝试传入 transport 参数初始化 SDK client（具体取决于 SDK 版本）。

环境变量小结（与上表补充）：

- `MCP_ENABLED`：开启 MCP 支持（可选）。
- `MCP_HTTP_URL`：HTTP MCP 服务地址，例如 `http://localhost:9000`。
- `MCP_SDK_PATH`：本地 SDK 源路径，用于调试 `modelcontextprotocol/python-sdk`。`
- `MCP_SDK_TRANSPORT`：传给 SDK 的 transport 名称（可选）。

注意：生产环境通常使用托管 MCP 服务或安全可信插件；在生产中启用外部插件前请确保安全审计与访问控制。

## 3. CORS

`backend/main.py` 从 `CORS_ORIGINS` 读取。未设置时仅允许本地 Vite：

- `http://127.0.0.1:5173`
- `http://localhost:5173`

生产必须显式配置前端 Pages 域名（HTTPS）。

## 4. Railway 部署

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. 选择 `qwen-agent` 仓库
3. Settings → 使用 Dockerfile 构建（根目录 `Dockerfile`）
4. Variables 添加上表环境变量
5. **Volume**（推荐）：
   - Mount path: `/app/runtime`
   - 持久化 SQLite、`workspaces/`、日志
6. Networking → Generate Domain → 得到 `https://xxx.up.railway.app`
7. 可选：Custom Domain `api.yourdomain.com`（CNAME 到 Railway）

`VITE_API_BASE` = `https://api.yourdomain.com/api`（或 Railway 域名 + `/api`）

## 5. Fly.io 部署

```powershell
fly launch --no-deploy
# 选择 Dockerfile，region 选近端

fly secrets set DASHSCOPE_API_KEY=sk-...
fly secrets set CORS_ORIGINS=https://your-app.pages.dev

# 持久化 volume
fly volumes create qwen_data --size 1 --region <your-region>
```

`fly.toml` 示例片段：

```toml
[http_service]
  internal_port = 8765
  force_https = true

[mounts]
  source = "qwen_data"
  destination = "/app/runtime"
```

```powershell
fly deploy
fly certs add api.yourdomain.com
```

## 6. 生产启动方式

容器内默认：

```
CMD ["python", "-m", "backend"]
```

等价于 `UVICORN_RELOAD=0`、`HOST=0.0.0.0`。本地开发仍用：

```powershell
python -m backend          # reload 默认开
UVICORN_RELOAD=0 python -m backend   # 生产模式本地试
```

## 7. 联调 checklist

- [ ] `curl https://api.xxx.com/health` → `ok`
- [ ] Pages 前端 `VITE_API_BASE` 指向 `https://api.xxx.com/api`
- [ ] 浏览器创建会话、SSE 流式聊天
- [ ] `confirmation_required` + `POST /api/chat/confirm` 跨域正常
- [ ] 刷新后会话历史仍在（volume 挂载 `runtime/`）
- [ ] 后端日志可见 `confirmation_required` / tool 事件

## 8. SSE / Cloudflare 注意

- `POST /api/chat` 响应头已有 `X-Accel-Buffering: no`
- 若 API 域名经 Cloudflare 代理，流式可能被缓冲；建议：
  - API 子域名 **灰云**（DNS only）直连 Railway/Fly，或
  - 使用平台原生 HTTPS 域名，前端 `VITE_API_BASE` 直连

## 9. 安全提醒

- 未做 JWT（S3）前不要公开推广
- `DASHSCOPE_API_KEY` 仅平台 Secrets，不进镜像
- 定期轮换 Key；限制 CORS 来源
- 可用 Cloudflare Access 保护 Pages 入口

## 10. 无 Volume 时

容器重建后 `runtime/` 清空：会话、SQLite、沙箱文件丢失。演示可用；生产务必挂卷。
