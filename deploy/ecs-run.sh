#!/usr/bin/env bash
# ECS 上加载镜像并启动 Sheldon Agent
# 用法：将本脚本与 sheldon-agent.tar 放在同一目录（默认 /opt/sheldon-agent/）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-$SCRIPT_DIR}"
IMAGE="${IMAGE:-sheldon-agent:1.0.0}"
TAR="${TAR:-sheldon-agent.tar}"
CONTAINER="${CONTAINER:-sheldon-agent}"
HOST_PORT="${HOST_PORT:-8081}"

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  echo "错误: 请 export DASHSCOPE_API_KEY=sk-..." >&2
  exit 1
fi

cd "$DEPLOY_DIR"

if [[ ! -f "$TAR" ]]; then
  echo "错误: 未找到 $DEPLOY_DIR/$TAR，请先上传" >&2
  exit 1
fi

echo ">>> docker load"
docker load -i "$TAR"

echo ">>> 停止旧容器"
docker stop "$CONTAINER" 2>/dev/null || true
docker rm "$CONTAINER" 2>/dev/null || true

CORS="${CORS_ORIGINS:-http://118.178.144.109:${HOST_PORT}}"

echo ">>> docker run (宿主机 ${HOST_PORT} -> 容器 8765, restart=unless-stopped)"
RUN_ARGS=(
  -d
  -p "${HOST_PORT}:8765"
  --name "$CONTAINER"
  --restart unless-stopped
  -e "DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}"
  -e "HOST=0.0.0.0"
  -e "PORT=8765"
  -e "UVICORN_RELOAD=0"
  -e "CORS_ORIGINS=${CORS}"
)

if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  RUN_ARGS+=(-e "GITHUB_TOKEN=${GITHUB_TOKEN}")
  echo "    + GITHUB_TOKEN 已注入"
fi
if [[ -n "${GITHUB_DEFAULT_REPO:-}" ]]; then
  RUN_ARGS+=(-e "GITHUB_DEFAULT_REPO=${GITHUB_DEFAULT_REPO}")
  echo "    + GITHUB_DEFAULT_REPO=${GITHUB_DEFAULT_REPO}"
fi
if [[ -n "${BRAVE_API_KEY:-}" ]]; then
  RUN_ARGS+=(-e "BRAVE_API_KEY=${BRAVE_API_KEY}")
fi

docker run "${RUN_ARGS[@]}" "$IMAGE"

sleep 4
echo ">>> health"
curl -sf "http://127.0.0.1:${HOST_PORT}/health" && echo
echo "[完成] 外网: http://118.178.144.109:${HOST_PORT}/health"
