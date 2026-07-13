@echo off
REM QQBotStation Windows构建脚本
REM 打包为独立的exe可执行文件
REM 需要先安装: pip install -r requirements.txt
REM 需要先安装: pip install pyinstaller

echo ========================================
echo  QQBotStation Windows构建脚本
echo ========================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo [1/4] 安装依赖...
pip install -r requirements.txt
pip install pyinstaller

echo [2/4] 安装Playwright浏览器...
playwright install chromium

echo [3/4] 构建可执行文件...
pyinstaller ^
    --name "QQBotStation" ^
    --onefile ^
    --windowed ^
    --icon resources\icons\app.ico ^
    --add-data "resources;resources" ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtGui ^
    --hidden-import plyer ^
    --collect-all paddleocr ^
    --collect-all paddlepaddle ^
    main.py

echo [4/4] 构建完成！
echo 输出文件: dist\QQBotStation.exe
echo.
echo 提示: 如果希望减小体积，可以运行:
echo   pyinstaller --onefile --windowed --exclude-module paddleocr --exclude-module paddlepaddle main.py
echo   但这将禁用OCR功能。
echo.
pause
