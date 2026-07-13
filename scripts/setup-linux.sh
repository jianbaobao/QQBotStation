#!/bin/bash
# ==========================================
# QQBotStation Linux 一键安装脚本
# 支持: Ubuntu/Debian/CentOS/Fedora/Arch
# ==========================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================"
echo "  QQBotStation Linux 一键安装"
echo "============================================"
echo ""

# 检测 Linux 发行版
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command -v lsb_release &>/dev/null; then
        lsb_release -is | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}
DISTRO=$(detect_distro)
info "发行版: $DISTRO"

# 检测 Python
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        PYTHON=$(command -v $cmd)
        break
    fi
done

if [ -z "$PYTHON" ]; then
    error "未检测到 Python 3.8+"
    echo "  安装: sudo apt install python3 python3-pip python3-venv (Debian/Ubuntu)"
    echo "  或:   sudo yum install python3 python3-pip (CentOS/Fedora)"
    exit 1
fi
info "Python: $($PYTHON --version)"

# 系统依赖
info "安装系统依赖..."
case "$DISTRO" in
    ubuntu|debian|linuxmint|pop)
        sudo apt-get update -qq
        sudo apt-get install -y -qq \
            python3-pip python3-venv python3-dev \
            libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
            libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 \
            libxkbcommon0 libxcb1 libx11-6 libxcomposite1 \
            libxdamage1 libxfixes3 libxrandr2 libgbm1 \
            libpango-1.0-0 libcairo2 libasound2 \
            fonts-wqy-zenhei fonts-wqy-microhei \
            xvfb x11-utils 2>/dev/null || true
        ;;
    fedora|centos|rhel)
        sudo yum install -y python3-pip python3-devel \
            cups-libs dbus-glib libXcomposite libXcursor \
            libXdamage libXext libXi libXrandr pango cairo \
            wqy-zenhei-fonts wqy-microhei-fonts \
            xorg-x11-server-Xvfb 2>/dev/null || true
        ;;
    arch|manjaro)
        sudo pacman -S --noconfirm python python-pip \
            libxcomposite libxdamage libxrandr libxkbcommon \
            wqy-zenhei wqy-microhei xorg-server-xvfb 2>/dev/null || true
        ;;
    *)
        warn "未知发行版，尝试通用安装..."
        ;;
esac

# 创建虚拟环境
if [ ! -f "venv/bin/python" ]; then
    info "创建虚拟环境..."
    $PYTHON -m venv venv
fi
source venv/bin/activate

# 升级 pip
info "安装 Python 依赖..."
pip install --upgrade pip -q

# 使用镜像安装
for mirror in "https://pypi.tuna.tsinghua.edu.cn/simple" \
              "https://mirrors.aliyun.com/pypi/simple/" \
              "https://pypi.org/simple/"; do
    info "尝试镜像: $mirror"
    if pip install -r requirements.txt -i "$mirror" --timeout 60 2>/dev/null; then
        info "依赖安装成功"
        break
    fi
done

# 如果全部镜像失败，逐个安装核心包
pip install PySide6 playwright pyautogui keyboard APScheduler \
    Pillow numpy psutil requests opencv-python-headless \
    --timeout 60 2>/dev/null || {
    warn "部分包安装失败，尝试逐个安装..."
    while IFS= read -r pkg; do
        [[ "$pkg" =~ ^# ]] && continue
        pip install "$pkg" --timeout 30 2>/dev/null || true
    done < requirements.txt
}

# 安装 Playwright 浏览器
info "安装 Playwright Chromium 浏览器..."
PLAYWRIGHT_BROWSERS_PATH="$PWD/data/browser" python -m playwright install chromium 2>/dev/null || {
    info "尝试镜像下载..."
    PLAYWRIGHT_BROWSERS_PATH="$PWD/data/browser" \
    PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/" \
    python -m playwright install chromium 2>/dev/null || {
        warn "Playwright 浏览器下载失败"
        warn "可手动运行: PLAYWRIGHT_BROWSERS_PATH=data/browser python -m playwright install chromium"
    }
}

# 数据目录
info "创建数据目录..."
mkdir -p data data/logs data/browser_data config

# 初始化数据库
info "初始化数据库..."
python -c "
from app.core.database import Database
db = Database()
db.set_config('version', '1.0.0')
print('数据库已初始化')
" 2>/dev/null || true

# 编译 Go 守护进程（如果 Go 可用）
if command -v go &>/dev/null; then
    info "编译 Go 守护进程..."
    cd daemon
    go build -ldflags="-s -w" -o ../build/qqbot-daemon-linux-amd64 . 2>/dev/null && info "Go 编译成功" || warn "Go 编译失败"
    cd ..
fi

# 设置执行权限
chmod +x run.sh setup.sh 2>/dev/null || true

echo ""
echo "============================================"
echo "  安装完成！"
echo ""
echo "  桌面模式（需显示器）:"
echo "    source venv/bin/activate && python main.py"
echo "    ./run.sh"
echo ""
echo "  Web 管理模式（远程访问）:"
echo "    source venv/bin/activate && python main.py --daemon --port 8580"
echo "    浏览器打开 http://服务器IP:8580"
echo ""
echo "  Go 高性能守护进程（无需 Python）:"
echo "    chmod +x build/qqbot-daemon-linux-amd64"
echo "    ./build/qqbot-daemon-linux-amd64 --port 8580 --db data/qqbot.db"
echo ""
echo "  Docker: docker compose up -d"
echo "============================================"
