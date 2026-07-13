#!/bin/bash
# QQBotStation Go Daemon 构建脚本
# 跨平台编译为单二进制文件

set -e
cd "$(dirname "$0")"

echo "QQBotStation Go Daemon 构建"
echo "=========================="

# 检测 Go
if ! command -v go &>/dev/null; then
    echo "[错误] 请安装 Go 1.21+: https://go.dev/dl/"
    exit 1
fi

# 下载依赖
echo "[1/4] 下载依赖..."
go mod tidy

# Linux amd64
echo "[2/4] 编译 Linux amd64..."
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o ../build/qqbot-daemon-linux-amd64 .
echo "  -> build/qqbot-daemon-linux-amd64"

# Linux arm64
echo "[3/4] 编译 Linux arm64..."
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o ../build/qqbot-daemon-linux-arm64 .
echo "  -> build/qqbot-daemon-linux-arm64"

# Windows amd64
echo "[4/4] 编译 Windows amd64..."
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w -H=windowsgui" -o ../build/qqbot-daemon.exe .
echo "  -> build/qqbot-daemon.exe"

echo ""
echo "完成！全部二进制文件在 build/ 目录："
ls -lh ../build/ 2>/dev/null || echo "(build目录为空)"
