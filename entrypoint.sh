#!/bin/bash

set -e

# 使用 PUID/PGID/UMASK
PUID="${PUID:-0}"
PGID="${PGID:-0}"
UMASK="${UMASK:-022}"

# 调整目录权限
chown -R "${PUID}:${PGID}" /app 2>/dev/null || true

umask "${UMASK}"

# 若未提供命令，则使用默认启动命令
if [ $# -eq 0 ]; then
    set -- gunicorn -c gunicorn.conf.py -k gevent -w 1 -b 0.0.0.0:9527 app:app
fi

# 如果第一个参数是以 '-' 开头（仅传入了参数），自动补全 gunicorn
if [ "${1#-}" != "$1" ]; then
    set -- gunicorn "$@"
fi

exec gosu "${PUID}:${PGID}" "$@"

