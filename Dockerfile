# QQBotStation Docker 镜像
# 构建: docker build -t qqbotstation .
# 运行: docker run -d --name qqbotstation -p 8580:8580 qqbotstation
# 带 Go 守护进程: docker build -t qqbotstation:go --build-arg INCLUDE_GO=1 .

FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 libx11-6 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libegl1 \
    fonts-wqy-zenhei fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器（不含系统依赖，已在上面安装）
RUN pip install --no-cache-dir playwright && \
    PLAYWRIGHT_BROWSERS_PATH=/app/data/browser python -m playwright install chromium

# 复制项目源码
COPY . .

# 创建数据目录
RUN mkdir -p data logs config browser_data

# 可选：复制 Go 守护进程
ARG INCLUDE_GO=0
COPY build/qqbot-daemon-linux-amd64 /usr/local/bin/qqbot-daemon 2>/dev/null || true

# 暴露端口
EXPOSE 8580

# 默认以守护进程模式运行（无头）
ENV QQBOT_HEADLESS=1
ENV PLAYWRIGHT_BROWSERS_PATH=/app/data/browser
CMD ["python", "main.py", "--daemon", "--port", "8580"]
