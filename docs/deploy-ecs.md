# 阿里云 ECS 部署（Docker + uv）

> 遵循工作区 [12-AI编程工具部署引导.md](../../12-AI编程工具部署引导.md)

## 环境

| 项 | 值 |
|----|-----|
| ECS | Ubuntu 22.04 · `118.178.144.109` |
| 目录 | `/opt/sheldon-agent/` |
| 宿主机端口 | **8081** → 容器 **8765** |

## 本机构建

```powershell
cd D:\system\Sheldon-Shuo-Agent\sheldon-agent

# 确保 uv.lock 最新
uv lock

# 构建镜像（上下文为项目根，Dockerfile 在 deploy/）
docker build -f deploy/Dockerfile -t sheldon-agent:1.0.0 .

docker save -o sheldon-agent.tar sheldon-agent:1.0.0
```

Workbench 上传 `sheldon-agent.tar` 到 ECS `/opt/sheldon-agent/`。

## ECS 运行

```bash
cd /opt/sheldon-agent
docker load -i sheldon-agent.tar
docker stop sheldon-agent 2>/dev/null; docker rm sheldon-agent 2>/dev/null

docker run -d \
  -p 8081:8765 \
  --name sheldon-agent \
  --restart unless-stopped \
  -e DASHSCOPE_API_KEY=sk-你的密钥 \
  -e CORS_ORIGINS=http://118.178.144.109:8081 \
  sheldon-agent:1.0.0

curl http://localhost:8081/health
```

## 前端

Web 静态资源在 `apps/web/`：

```powershell
cd apps/web
npm run build
```

可将 `apps/web/dist/` 托管到 Cloudflare Pages，或通过 Nginx 与 API 同域部署；设置 `VITE_API_BASE` 指向 ECS API。
