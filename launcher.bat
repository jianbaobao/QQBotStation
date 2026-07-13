@echo off
chcp 65001 >nul
title QQBotStation Launcher
REM ==========================================
REM QQBotStation 多功能启动器
REM 用法: 双击运行桌面模式
REM       drag-drop: 拖入参数文件
REM ==========================================

:check_venv
if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
) else (
    set PY=python
)

:parse_args
if "%1"=="--daemon" goto :daemon
if "%1"=="--build" goto :build
if "%1"=="--help" goto :help
goto :gui

:gui
echo [QQBotStation] 启动桌面模式...
start "QQBotStation" "%PY%" main.py
goto :end

:daemon
echo [QQBotStation] 启动 Web 管理服务器...
echo   http://localhost:8580
"%PY%" main.py --daemon --port 8580
goto :end

:build
echo [QQBotStation] 打包为 exe (需要 PyInstaller)...
if not exist "venv\Scripts\pyinstaller.exe" (
    "%PY%" -m pip install pyinstaller
)
"%PY%" -m PyInstaller qqbotstation.spec --clean
echo 输出: dist\QQBotStation.exe
goto :end

:help
echo QQBotStation Launcher
echo.
echo 用法: run.bat [选项]
echo.
echo 选项:
echo   (无)    启动桌面 GUI 模式
echo   --daemon 启动 Web 管理服务器 (端口 8580)
echo   --build  打包为独立 exe
echo   --help   显示此帮助
goto :end

:end
pause
