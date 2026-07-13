@echo off
REM ==========================================
REM QQBotStation 一键安装脚本 (Windows)
REM 自动创建虚拟环境 + 安装依赖 + 安装浏览器
REM ==========================================
chcp 65001 >nul
title QQBotStation 安装程序

echo ╔══════════════════════════════════════════╗
echo ║     QQBotStation · 一键安装             ║
echo ╚══════════════════════════════════════════╝
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo 请先安装 Python 3.10+: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set pyver=%%i
echo [OK] Python %pyver%

REM 创建虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [1/4] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [失败] 虚拟环境创建失败
        pause
        exit /b 1
    )
) else (
    echo [1/4] 虚拟环境已存在
)

REM 升级 pip
echo [2/4] 安装依赖...
venv\Scripts\python.exe -m pip install --upgrade pip -q

REM 尝试多个镜像源安装
set MIRRORS=https://pypi.org/simple/ https://pypi.tuna.tsinghua.edu.cn/simple https://mirrors.aliyun.com/pypi/simple/
set INSTALLED=0

for %%m in (%MIRRORS%) do (
    if !INSTALLED!==0 (
        echo   尝试镜像: %%m
        venv\Scripts\pip install -r requirements.txt -i %%m --timeout 60 2>nul
        if !errorlevel!==0 set INSTALLED=1
    )
)

REM 逐个安装（如果批量失败）
if !INSTALLED!==0 (
    echo   逐个安装依赖...
    for /f "tokens=1 delims=;=#" %%p in (requirements.txt) do (
        if not "%%p"=="" (
            venv\Scripts\pip install %%p --timeout 60 2>nul
        )
    )
)

REM 安装 Playwright 浏览器
echo [3/4] 安装 Playwright 浏览器...
venv\Scripts\playwright install chromium 2>nul

REM 创建数据目录
echo [4/4] 创建数据目录...
if not exist data mkdir data
if not exist data\logs mkdir data\logs
if not exist data\browser_data mkdir data\browser_data
if not exist config mkdir config

echo.
echo ╔══════════════════════════════════════════╗
echo ║     安装完成！                           ║
echo ║                                          ║
echo ║  启动桌面: 双击 run.bat                  ║
echo ║  或运行:   python main.py               ║
echo ║                                          ║
echo ║  Web管理:  python main.py --daemon       ║
echo ║           浏览器打开 http://localhost:8580║
echo ╚══════════════════════════════════════════╝
echo.
pause
