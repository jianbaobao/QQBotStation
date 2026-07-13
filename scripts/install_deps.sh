#!/bin/bash
# QQBotStation Linux/Ubuntu安装脚本
set -e

echo "========================================"
echo " QQBotStation Linux 安装脚本"
echo "========================================"

# 检查Python
if ! command -v python3 &>/dev/null; then
    echo "[错误] 未检测到Python3，请安装: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[1/5] 安装系统依赖..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
        python3-pip python3-venv \
        libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
        libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 \
        libxkbcommon0 libxcb1 libx11-6 libxcomposite1 \
        libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 \
        fonts-wqy-zenhei fonts-wqy-microhei \
        xvfb
elif command -v yum &>/dev/null; then
    sudo yum install -y \
        python3-pip \
        cups-libs dbus-glib libXcomposite libXcursor \
        libXdamage libXext libXi libXrandr \
        pango cairo \
        wqy-zenhei-fonts wqy-microhei-fonts \
        xorg-x11-server-Xvfb
fi

echo "[2/5] 创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo "[3/5] 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/5] 安装Playwright浏览器..."
playwright install chromium

echo "[5/5] 安装完成！"
echo ""
echo "========================================"
echo " 使用方法:"
echo " 1. GUI模式（需桌面环境）:"
echo "    source venv/bin/activate && python main.py"
echo ""
echo " 2. 守护进程模式（无桌面）:"
echo "    source venv/bin/activate && python main.py --daemon"
echo ""
echo " 3. 一键命令: python main.py --daemon"
echo "========================================"
