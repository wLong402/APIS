#!/bin/sh
set -e

mkdir -p /app/logs /app/tokens

if [ ! -f "${CONFIG_PATH:-config/config.yaml}" ]; then
  echo "错误: 配置文件不存在: ${CONFIG_PATH:-config/config.yaml}"
  echo "请挂载 config 目录，或复制 config/config.docker.example.yaml 为 config/config.yaml 后填写。"
  exit 1
fi

if [ -n "${REDIS_HOST:-}" ]; then
  redis_port="${REDIS_PORT:-6379}"
  echo "等待 Redis: ${REDIS_HOST}:${redis_port} ..."
  until python - <<'PY'
import os
import socket

host = os.environ.get("REDIS_HOST", "redis")
port = int(os.environ.get("REDIS_PORT", "6379"))
s = socket.socket()
s.settimeout(1)
s.connect((host, port))
s.close()
PY
  do
    sleep 1
  done
  echo "Redis 已就绪。"
fi

exec "$@"
