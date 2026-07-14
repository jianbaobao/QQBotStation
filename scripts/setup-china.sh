#!/bin/bash
# ==========================================
# QQBotStation 中国服务器一键安装
# 使用 ghproxy 镜像解决 GitHub 连接问题
# ==========================================
set -e

echo "============================================"
echo "  QQBotStation 中国服务器安装"
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
    echo "  apt install python3 python3-pip python3-venv -y"
    exit 1
fi
echo "[OK] $($PYTHON --version)"

# 安装 python3-venv
if ! $PYTHON -m venv --help &>/dev/null 2>&1; then
    echo "[安装] python3-venv..."
    apt-get update -qq 2>/dev/null
    apt-get install -y -qq --fix-missing python3-venv 2>/dev/null || {
        apt-get update && apt-get install -y python3-venv
    }
fi

# 安装 unzip
if ! command -v unzip &>/dev/null; then
    apt-get install -y -qq unzip 2>/dev/null || true
fi

# 下载项目（从 ghproxy 镜像）
echo "[1/5] 下载项目代码..."
PROJECT_DIR="/root/QQBotStation"
if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/setup.sh" ]; then
    echo "  项目已存在，跳过下载"
    cd "$PROJECT_DIR"
else
    rm -rf "$PROJECT_DIR" /tmp/QQBotStation-main
    echo "  尝试多个镜像下载..."
    MIRRORS=(
        "https://ghproxy.net/https://github.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip"
        "https://ghproxy.com/https://github.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip"
        "https://githubfast.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip"
        "https://download.fastgit.org/jianbaobao/QQBotStation/archive/refs/heads/main.zip"
        "https://gh.api.99988866.xyz/https://github.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip"
        "https://github.com/jianbaobao/QQBotStation/archive/refs/heads/main.zip"
    )
    DOWNLOADED=0
    for url in "${MIRRORS[@]}"; do
        echo "  -> $url"
        if wget -q --timeout=30 "$url" -O /tmp/QQBotStation.zip 2>/dev/null; then
            echo "  OK"
            DOWNLOADED=1
            break
        fi
    done
    if [ "$DOWNLOADED" = "0" ]; then
        echo "[错误] 所有下载方式均失败"
        echo "  请手动执行以下命令安装依赖后上传项目:"
        echo "  apt update && apt install python3-venv unzip wget -y"
        exit 1
    fi
    unzip -q /tmp/QQBotStation.zip -d /tmp/
    mv /tmp/QQBotStation-main "$PROJECT_DIR"
    rm -f /tmp/QQBotStation.zip
    cd "$PROJECT_DIR"
    echo "  OK"
fi

# 检查 Python 包镜像
echo "[2/5] 安装 Python 依赖..."
if [ ! -f "venv/bin/python" ]; then
    $PYTHON -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q

# 尝试多个 pip 镜像
INSTALLED=0
for mirror in "https://pypi.tuna.tsinghua.edu.cn/simple" \
              "https://mirrors.aliyun.com/pypi/simple/" \
              "https://pypi.douban.com/simple/" \
              "https://pypi.org/simple/"; do
    echo "  -> $mirror"
    if pip install -r requirements.txt -i "$mirror" --timeout 60 2>/dev/null; then
        INSTALLED=1
        echo "  OK"
        break
    fi
done

if [ "$INSTALLED" = "0" ]; then
    echo "  镜像均失败，逐个安装核心包..."
    pip install PySide6 playwright pyautogui keyboard APScheduler Pillow numpy psutil requests opencv-python-headless --timeout 30 2>/dev/null || true
fi

# 安装 Playwright 浏览器
echo "[3/5] 安装 Playwright 浏览器..."
PLAYWRIGHT_BROWSERS_PATH="$PWD/data/browser" python -m playwright install chromium 2>/dev/null || {
    echo "  尝试镜像下载..."
    PLAYWRIGHT_BROWSERS_PATH="$PWD/data/browser" \
    PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/" \
    python -m playwright install chromium 2>/dev/null || echo "  警告: 浏览器下载失败，可手动安装"
}

# 初始化数据库
echo "[4/5] 初始化数据库..."
mkdir -p data data/logs data/browser_data config
python -c "from app.core.database import Database; Database().set_config('version','1.0.0'); print('  OK')" 2>/dev/null || true

# 启动
echo "[5/5] 启动 Web 管理..."
echo ""
echo "============================================"
echo "  安装完成！"
echo ""
echo "  启动命令:"
echo "    cd /root/QQBotStation"
echo "    source venv/bin/activate"
echo "    python main.py --daemon --port 8580"
echo ""
echo "  或使用 nohup 后台运行:"
echo "    cd /root/QQBotStation && nohup venv/bin/python main.py --daemon --port 8580 > qqbot.log 2>&1 &"
echo ""
echo "  浏览器打开: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8580"
echo "============================================"
echo ""

# 直接启动
source venv/bin/activate
python main.py --daemon --port 8580
