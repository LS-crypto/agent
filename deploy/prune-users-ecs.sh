#!/usr/bin/env bash
# ECS 宿主机直接清理测试用户（无需新 Docker 镜像）
# 用法：
#   source ecs-run.env
#   ./prune-users-ecs.sh
#   ./prune-users-ecs.sh --apply
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/sheldon-agent}"
RUNTIME="${RUNTIME:-$DEPLOY_DIR/runtime}"
SOURCE_TAR="${SOURCE_TAR:-$DEPLOY_DIR/source.tar}"
BUILD_DIR="${BUILD_DIR:-$DEPLOY_DIR/build-prune}"
APPLY="${1:-}"

if [[ -f "$DEPLOY_DIR/ecs-run.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$DEPLOY_DIR/ecs-run.env"
  set +a
fi

KEEP_EXTRA="${KEEP_EMAIL:-2575853136@qq.com}"

mkdir -p "$BUILD_DIR"
if [[ ! -f "$BUILD_DIR/scripts/prune_test_users.py" ]]; then
  echo ">>> 解压 source.tar"
  rm -rf "${BUILD_DIR:?}"/*
  tar -xf "$SOURCE_TAR" -C "$BUILD_DIR"
fi

if [[ ! -f "$RUNTIME/db/auth.sqlite" ]]; then
  echo "错误: 未找到 $RUNTIME/db/auth.sqlite" >&2
  exit 1
fi

cd "$BUILD_DIR"
ARGS=(python3 scripts/prune_test_users.py --runtime "$RUNTIME" --keep "$KEEP_EXTRA")
if [[ "$APPLY" == "--apply" ]]; then
  ARGS+=(--apply)
fi

echo ">>> ${ARGS[*]}"
"${ARGS[@]}"
