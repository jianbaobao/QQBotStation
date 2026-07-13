@echo off
REM QQBotStation Windows依赖安装脚本
echo ========================================
echo  QQBotStation Windows依赖安装
echo ========================================

echo [1/4] 检查Python...
python --version
if errorlevel 1 (
    echo [错误] 请先安装Python 3.10+ (https://www.python.org/downloads/)
    pause
    exit /b 1
)

echo [2/4] 安装核心依赖...
pip install --upgrade pip
pip install -r requirements.txt

echo [3/4] 安装Playwright浏览器...
playwright install chromium

echo [4/4] 可选：安装OCR依赖（需要约1GB）...
echo 如需OCR功能，请执行: pip install paddlepaddle paddleocr
echo 或: pip install paddlepaddle-gpu paddleocr (GPU版)

echo.
echo ========================================
echo  安装完成！
echo.
echo  启动方式:
echo    python main.py
echo.
echo  命令行模式:
echo    python main.py --daemon
echo    python main.py --ocr-scan
echo ========================================
pause
