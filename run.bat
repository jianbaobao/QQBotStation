@echo off
chcp 65001 >nul
title QQBotStation

REM 自动检测虚拟环境并运行
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe main.py %*
) else (
    python main.py %*
)

if errorlevel 1 (
    echo.
    echo [错误] 运行失败。请先运行 setup.bat 安装依赖。
    pause
)
