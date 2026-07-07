# Sheldon Agent — ECS 完整部署指南

> **服务器：** Ubuntu · `118.178.144.109`  
> **部署目录：** `/opt/sheldon-agent/`（与旧 `/opt/test-system/` 分开）  
> **端口：** 宿主机 **8081** → 容器 **8765**

---

## 架构一览

```text
本机 Windows                         阿里云 ECS
─────────────                        ────────────
deploy/Dockerfile  ──build──►  sheldon-agent:1.0.0
       │                              docker load
       └── docker save ──upload──►  sheldon-agent.tar
                                     docker run -d -p 8081:8765
                                     --restart unless-stopped
```

---

## 一、Dockerfile（已有，无需重写）

路径：`deploy/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8765 UVICORN_RELOAD=0

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY core/ core/
COPY server/ server/
COPY apps/cli/ apps/cli/
COPY apps/__init__.py apps/__init__.py
COPY scripts/ scripts/
RUN mkdir -p runtime

EXPOSE 8765
CMD [".venv/bin/python", "-m", "server"]
```

要点：

- 基于 **Python 3.11-slim** + **uv** 安装依赖（无 `requirements.txt`）
- 监听 **0.0.0.0:8765**（容器内）
- **不**把 `.env` 打进镜像（密钥通过 `docker run -e` 注入）

---

## 二、本机构建镜像（Windows）

```powershell
cd D:\system\Sheldon-Shuo-Agent

# 一键：uv lock + build + 导出 tar
.\scripts\deploy-build.ps1
```

或分步：

```powershell
uv lock
docker build -f deploy/Dockerfile -t sheldon-agent:1.0.0 .
docker save -o sheldon-agent.tar sheldon-agent:1.0.0
```

本地验证（可选）：

```powershell
uv run pytest tests/test_docker_health.py -q
```

产物：`sheldon-agent.tar`（约 78 MB）

---

## 三、上传到 ECS

Workbench → `/opt/sheldon-agent/`（**新建目录**，勿与 `/opt/test-system/` 混用）

| 文件 | 说明 |
|------|------|
| `sheldon-agent.tar` | 镜像包 |
| `ecs-run.sh` | 来自 `deploy/ecs-run.sh` |

---

## 四、ECS 上运行容器（后台持久）

```bash
# 确认 Docker 已启动
sudo systemctl status docker

mkdir -p /opt/sheldon-agent
cd /opt/sheldon-agent
chmod +x ecs-run.sh

# 必填：百炼 API Key
export DASHSCOPE_API_KEY=sk-你的密钥

# 可选
export GITHUB_TOKEN=ghp_xxx
export GITHUB_DEFAULT_REPO=LS-crypto/agent
export BRAVE_API_KEY=BSA_xxx
export CORS_ORIGINS=http://118.178.144.109:8081

./ecs-run.sh
```

### 等价的手动命令

```bash
cd /opt/sheldon-agent
docker load -i sheldon-agent.tar

docker stop sheldon-agent 2>/dev/null; docker rm sheldon-agent 2>/dev/null

docker run -d \
  --name sheldon-agent \
  --restart unless-stopped \
  -p 8081:8765 \
  -e DASHSCOPE_API_KEY=sk-你的密钥 \
  -e HOST=0.0.0.0 \
  -e PORT=8765 \
  -e UVICORN_RELOAD=0 \
  -e CORS_ORIGINS=http://118.178.144.109:8081 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_DEFAULT_REPO=LS-crypto/agent \
  sheldon-agent:1.0.0
```

**持久运行说明：**

| 参数 | 作用 |
|------|------|
| `-d` | 后台运行 |
| `--restart unless-stopped` | 开机自启；手动 stop 后不自动拉起 |
| `-p 8081:8765` | 外网 8081 → 容器内 8765 |

---

## 五、验证

```bash
# ECS 本机
curl http://127.0.0.1:8081/health
# 期望: {"status":"ok"}

docker ps --filter name=sheldon-agent
docker logs sheldon-agent --tail 30
```

**外网**（需安全组放行 **8081/TCP**）：

```text
http://118.178.144.109:8081/health
```

---

## 六、常用运维

```bash
# 查看日志
docker logs -f sheldon-agent

# 重启
docker restart sheldon-agent

# 停止并删除
docker stop sheldon-agent && docker rm sheldon-agent

# 更新版本：本机重新 build/save → 上传新 tar → 再执行 ecs-run.sh
```

---

## 七、让别人通过浏览器使用（Nginx + Web 前端）

后端 `:8081` 只有 API；要让别人用聊天界面，需部署 Web 并走 **80 端口**（安全组已放行 80）。

### 本机构建前端包

```powershell
cd D:\system\Sheldon-Shuo-Agent
.\scripts\deploy-web.ps1
```

产物：`deploy/web-dist.tar`（约 0.6 MB）

### 上传到 ECS `/opt/sheldon-agent/`

| 文件 | 说明 |
|------|------|
| `web-dist.tar` | 前端静态资源 |
| `nginx-sheldon.conf` | Nginx 配置 |
| `setup-nginx.sh` | 一键安装脚本 |

### ECS 执行

```bash
cd /opt/sheldon-agent
sed -i 's/\r$//' setup-nginx.sh
chmod +x setup-nginx.sh
./setup-nginx.sh
```

### 访问地址

```text
http://118.178.144.109/
```

Nginx 会把 `/api` 反代到本机 `8081`（含 SSE 流式），无需单独配置 `VITE_API_BASE`。

### 更新 CORS（可选，直连 8081 调试时）

```bash
export CORS_ORIGINS=http://118.178.144.109,http://118.178.144.109:8081
./ecs-run.sh
```

---

## 八、前端（独立托管，可选）

当前镜像**仅含后端 API**。Web UI 需单独部署：

```powershell
cd apps/web
npm run build
# 将 dist/ 托管到 Cloudflare Pages 或 Nginx，VITE_API_BASE=http://118.178.144.109:8081/api
```

---

## 八、故障排查

| 现象 | 处理 |
|------|------|
| `curl` 连接拒绝 | `docker ps` 看容器是否 Up；`docker logs sheldon-agent` |
| 外网不通、本机通 | 阿里云安全组 → 入方向放行 **8081** |
| 8081 被占用 | `export HOST_PORT=8082` 后重跑 `ecs-run.sh` |
| API 401/500 | 检查 `DASHSCOPE_API_KEY` 是否正确传入 |

---

## 环境变量一览

| 变量 | 必填 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 是 | 百炼 API Key |
| `CORS_ORIGINS` | 建议 | 前端域名，逗号分隔 |
| `GITHUB_TOKEN` | 否 | GitHub MCP |
| `GITHUB_DEFAULT_REPO` | 否 | 默认 `owner/repo` |
| `BRAVE_API_KEY` | 否 | Brave 搜索 |
| `HOST` | 否 | 默认 `0.0.0.0`（Dockerfile 已设） |
| `PORT` | 否 | 默认 `8765` |
