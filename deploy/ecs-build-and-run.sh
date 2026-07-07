#!/usr/bin/env bash
# ECS 上从源码构建镜像并启动（无需本机 Docker）
# 前置：/opt/sheldon-agent/source.tar + ecs-run.env
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/sheldon-agent}"
BUILD_DIR="${BUILD_DIR:-$DEPLOY_DIR/build}"
SOURCE_TAR="${SOURCE_TAR:-$DEPLOY_DIR/source.tar}"
IMAGE="${IMAGE:-sheldon-agent:1.0.0}"
CONTAINER="${CONTAINER:-sheldon-agent}"
HOST_PORT="${HOST_PORT:-8081}"
ENV_FILE="${ENV_FILE:-$DEPLOY_DIR/ecs-run.env}"

if [[ ! -f "$SOURCE_TAR" ]]; then
  echo "错误: 未找到 $SOURCE_TAR" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "错误: 未找到 $ENV_FILE（从 ecs-run.env.example 复制并填入密钥）" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

for v in DASHSCOPE_API_KEY JWT_SECRET MASTER_SECRET; do
  if [[ -z "${!v:-}" ]]; then
    echo "错误: ecs-run.env 缺少 $v" >&2
    exit 1
  fi
done

RUNTIME_HOST="${RUNTIME_HOST:-$DEPLOY_DIR/runtime}"
mkdir -p "$RUNTIME_HOST" "$BUILD_DIR"

echo ">>> 解压源码"
rm -rf "${BUILD_DIR:?}"/*
tar -xf "$SOURCE_TAR" -C "$BUILD_DIR"

echo ">>> 预拉基础镜像（走镜像加速，失败时见下方说明）"
if ! docker pull python:3.11-slim 2>/dev/null; then
  echo "提示: Docker Hub 超时。可配置镜像加速后重试："
  echo '  /etc/docker/daemon.json → {"registry-mirrors":["https://mirror.ccs.tencentyun.com"]}'
  echo "  systemctl restart docker"
  echo "或先执行: docker pull registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim"
  echo "         docker tag registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim python:3.11-slim"
fi

echo ">>> docker build"
docker build -f "$BUILD_DIR/deploy/Dockerfile" -t "$IMAGE" "$BUILD_DIR"

echo ">>> 停止旧容器"
docker stop "$CONTAINER" 2>/dev/null || true
docker rm "$CONTAINER" 2>/dev/null || true

CORS="${CORS_ORIGINS:-http://118.178.144.109,https://localhost,http://localhost}"

echo ">>> docker run"
RUN_ARGS=(
  -d
  -p "${HOST_PORT}:8765"
  --name "$CONTAINER"
  --restart unless-stopped
  -v "${RUNTIME_HOST}:/app/runtime"
  -e "DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}"
  -e "JWT_SECRET=${JWT_SECRET}"
  -e "MASTER_SECRET=${MASTER_SECRET}"
  -e "HOST=0.0.0.0"
  -e "PORT=8765"
  -e "UVICORN_RELOAD=0"
  -e "CORS_ORIGINS=${CORS}"
)

[[ -n "${GITHUB_TOKEN:-}" ]] && RUN_ARGS+=(-e "GITHUB_TOKEN=${GITHUB_TOKEN}")
[[ -n "${GITHUB_DEFAULT_REPO:-}" ]] && RUN_ARGS+=(-e "GITHUB_DEFAULT_REPO=${GITHUB_DEFAULT_REPO}")
[[ -n "${BRAVE_API_KEY:-}" ]] && RUN_ARGS+=(-e "BRAVE_API_KEY=${BRAVE_API_KEY}")
[[ -n "${ADMIN_EMAIL:-}" ]] && RUN_ARGS+=(-e "ADMIN_EMAIL=${ADMIN_EMAIL}")
[[ -n "${ADMIN_PASSWORD:-}" ]] && RUN_ARGS+=(-e "ADMIN_PASSWORD=${ADMIN_PASSWORD}")

docker run "${RUN_ARGS[@]}" "$IMAGE"

sleep 4
curl -sf "http://127.0.0.1:${HOST_PORT}/health" && echo
echo "[完成] API: http://118.178.144.109:${HOST_PORT}/health · Web: http://118.178.144.109/"
