#!/bin/bash
# QQBotStation 启动脚本 (Linux/macOS)
cd "$(dirname "$0")"

PYTHON="python3"
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
fi

exec $PYTHON main.py "$@"
