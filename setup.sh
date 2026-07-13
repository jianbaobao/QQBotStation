#!/bin/bash
# ==========================================
# QQBotStation 一键安装脚本 (Linux/macOS)
# 用法: chmod +x setup.sh && ./setup.sh
# ==========================================
set -e

echo "============================================"
echo "  QQBotStation Linux/macOS 安装"
echo "============================================"
echo ""

# 检测 Python
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null && $cmd -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
        PYTHON=$(command -v $cmd)
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "[错误] 需要 Python 3.8+"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
    exit 1
fi
echo "[OK] $($PYTHON --version)"

# 虚拟环境
if [ ! -f "venv/bin/python" ]; then
    echo "[1/4] 创建虚拟环境..."
    $PYTHON -m venv venv
fi
source venv/bin/activate

# 安装依赖
echo "[2/4] 安装 Python 依赖..."
pip install --upgrade pip -q

# 尝试镜像
INSTALLED=0
for mirror in "https://pypi.tuna.tsinghua.edu.cn/simple" \
              "https://mirrors.aliyun.com/pypi/simple/" \
              "https://pypi.org/simple/"; do
    echo "  -> $mirror"
    if pip install -r requirements.txt -i "$mirror" --timeout 60 2>/dev/null; then
        INSTALLED=1
        break
    fi
done

if [ "$INSTALLED" = "0" ]; then
    echo "  逐个安装..."
    while IFS= read -r pkg; do
        [[ "$pkg" =~ ^[a-zA-Z] ]] && pip install "$pkg" --timeout 30 2>/dev/null || true
    done < requirements.txt
fi

# 安装 Playwright 浏览器
echo "[3/4] 安装 Playwright 浏览器..."
export PLAYWRIGHT_BROWSERS_PATH="$PWD/data/browser"
python -m playwright install chromium 2>/dev/null || {
    PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/" \
    python -m playwright install chromium 2>/dev/null || echo "  警告: 浏览器下载失败，可手动安装"
}

# 数据目录
echo "[4/4] 创建数据目录..."
mkdir -p data data/logs data/browser_data config

# 初始化数据库
python -c "from app.core.database import Database; Database().set_config('version','1.0.0'); print('  数据库已初始化')" 2>/dev/null || true

# Go 守护进程（可选）
if command -v go &>/dev/null; then
    echo "  编译 Go 守护进程..."
    cd daemon && go build -ldflags="-s -w" -o ../build/qqbot-daemon-linux-amd64 . 2>/dev/null && cd .. && echo "  Go 编译成功" || echo "  Go 编译跳过"
fi

chmod +x run.sh
echo ""
echo "============================================"
echo "  安装完成！"
echo ""
echo "  桌面:     ./run.sh"
echo "  Web管理:  venv/bin/python main.py --daemon --port 8580"
echo "  Go守护:   build/qqbot-daemon-linux-amd64 --port 8580 --db data/qqbot.db"
echo "  Docker:   docker compose up -d"
echo "============================================"
