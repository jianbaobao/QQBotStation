@echo off
chcp 65001 >nul
REM ==========================================
REM QQBotStation 离线包下载脚本
REM 在有网络的机器上运行，下载所有依赖
REM ==========================================
title QQBotStation 离线包下载

echo QQBotStation 离线依赖下载器
echo =============================
echo.

if not exist "vendor" mkdir vendor

echo 下载 Python 依赖到 vendor/ 目录...
echo 完成后可复制 vendor/ 到离线环境安装

pip download -r requirements.txt -d vendor --platform win_amd64 --only-binary=:all: 2>nul
if exist vendor\*.whl (
    echo [OK] 已下载到 vendor/ 目录
    dir vendor\*.whl /b
) else (
    echo [提示] 下载失败，请尝试: pip install -r requirements.txt
)

echo.
echo 完成后离线安装:
echo   pip install --no-index --find-links=vendor -r requirements.txt
echo.
pause
