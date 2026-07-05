#!/usr/bin/env bash
# ECS 上安装 Nginx 并部署 Sheldon Web 静态资源
# 前置：/opt/sheldon-agent/web-dist.tar 或 web/ 目录已上传
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/sheldon-agent}"
WEB_DIR="${WEB_DIR:-$DEPLOY_DIR/web}"
NGINX_CONF_SRC="${NGINX_CONF_SRC:-$DEPLOY_DIR/nginx-sheldon.conf}"
WEB_TAR="${WEB_TAR:-$DEPLOY_DIR/web-dist.tar}"

echo ">>> 安装 nginx"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx

mkdir -p "$WEB_DIR"

if [[ -f "$WEB_TAR" ]]; then
  echo ">>> 解压 web-dist.tar"
  rm -rf "${WEB_DIR:?}"/*
  tar -xf "$WEB_TAR" -C "$WEB_DIR"
elif [[ ! -f "$WEB_DIR/index.html" ]]; then
  echo "错误: 未找到 $WEB_TAR 且 $WEB_DIR/index.html 不存在" >&2
  echo "请在本机运行 scripts/deploy-web.ps1 并上传 web-dist.tar" >&2
  exit 1
fi

echo ">>> 配置 nginx"
if [[ ! -f "$NGINX_CONF_SRC" ]]; then
  echo "错误: 未找到 $NGINX_CONF_SRC，请一并上传 deploy/nginx-sheldon.conf" >&2
  exit 1
fi

cp "$NGINX_CONF_SRC" /etc/nginx/sites-available/sheldon-agent
ln -sf /etc/nginx/sites-available/sheldon-agent /etc/nginx/sites-enabled/sheldon-agent
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx
systemctl reload nginx

echo ">>> 检查"
curl -sf "http://127.0.0.1/health" && echo
echo "[完成] 外网访问: http://118.178.144.109/"
echo "提示: 若 80 无法访问，请在安全组放行 TCP 80"
