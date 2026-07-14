#!/bin/bash
# ==========================================
# QQBotStation WSL 一键修复 + 安装脚本
# ==========================================
set -e

echo "============================================"
echo "  QQBotStation WSL 修复安装"
echo "============================================"
echo ""

# 步骤 1：修复 Git 连接
echo "[1/6] 修复 Git 连接..."
git config --global http.postBuffer 524288000 2>/dev/null
git config --global http.lowSpeedLimit 0 2>/dev/null
git config --global http.lowSpeedTime 999999 2>/dev/null

# 尝试用 SSH 方式（如已配置）
if [ ! -d "QQBotStation" ]; then
    echo "  克隆仓库..."
    git clone https://github.com/jianbaobao/QQBotStation.git 2>/dev/null || {
        echo "  HTTPS 失败，尝试用代理..."
        git clone https://ghproxy.com/https://github.com/jianbaobao/QQBotStation.git 2>/dev/null || {
            echo "  下载 ZIP..."
            wget -q https://github.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip -O QQBotStation.zip 2>/dev/null || curl -sL https://github.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip -o QQBotStation.zip
            unzip -q QQBotStation.zip && mv QQBotStation-main QQBotStation && rm QQBotStation.zip
        }
    }
fi
cd QQBotStation

# 步骤 2：拉取最新代码
echo "[2/6] 拉取最新代码..."
git pull 2>/dev/null || echo "  已是最新或非 Git 目录"

# 步骤 3：清理旧的损坏 venv
echo "[3/6] 清理旧的虚拟环境..."
rm -rf venv

# 步骤 4：安装 python3-venv
echo "[4/6] 安装 python3-venv..."
if ! python3 -m venv --help &>/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3-venv
fi
echo "  OK"

# 步骤 5：运行 setup.sh
echo "[5/6] 安装项目依赖..."
bash setup.sh

# 步骤 6：启动
echo "[6/6] 启动 Web 管理..."
source venv/bin/activate
python main.py --daemon --port 8580 &
sleep 2
echo ""
echo "============================================"
echo "  启动完成！"
echo "  浏览器打开: http://localhost:8580"
echo "  或: http://$(hostname -I | awk '{print $1}'):8580"
echo "============================================"
