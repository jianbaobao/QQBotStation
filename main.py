"""
QQBotStation 入口文件
全能自动化工作站 - QQ群消息 + 网站签到 + OCR识别 + 屏幕扫描
支持三种部署方式：Windows桌面 / Linux服务 / Docker容器
"""
import sys
import os
import platform


def _init_app():
    """应用初始化：创建目录、默认配置、平台检查"""
    from pathlib import Path
    base = os.path.dirname(os.path.abspath(__file__))
    
    # 确保路径
    for d in ['data', 'data/logs', 'data/browser_data', 'config', 'resources/icons']:
        Path(os.path.join(base, d)).mkdir(parents=True, exist_ok=True)
    
    # 检查必要依赖
    missing = []
    try:
        import PySide6
    except ImportError:
        missing.append('PySide6')
    try:
        import playwright
    except ImportError:
        missing.append('playwright')
    
    if missing:
        print(f"[初始化] 缺少核心依赖: {', '.join(missing)}")
        print(f"[初始化] 请运行: pip install {' '.join(missing)}")
        if not any('--headless' in a for a in sys.argv):
            print("[初始化] 继续启动（部分功能可能不可用）...")


def main():
    """主入口 - 根据运行环境选择合适的启动方式"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    _init_app()

    headless = '--headless' in sys.argv or os.environ.get('QQBOT_HEADLESS') == '1'
    cli_mode = '--cli' in sys.argv or os.environ.get('QQBOT_CLI') == '1'

    has_display = os.environ.get('DISPLAY') is not None or platform.system() == 'Windows'
    if headless or cli_mode or (platform.system() == 'Linux' and not has_display):
        _run_cli()
    else:
        _run_gui()


def _run_gui():
    """启动GUI桌面应用"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        QApplication.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("QQBotStation")
    app.setOrganizationName("QQBotStation")

    # 加载样式表
    import_path = os.path.dirname(os.path.abspath(__file__))
    style_path = os.path.join(import_path, "resources", "styles", "main.qss")
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # 应用图标
    icon_path = os.path.join(import_path, "resources", "icons", "app.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from app.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _run_cli():
    """启动CLI命令行模式（服务模式）"""
    import argparse
    import time
    import json
    import signal

    parser = argparse.ArgumentParser(description="QQBotStation - 全能自动化工作站")
    parser.add_argument('--task', type=str, help='执行指定任务文件(JSON)')
    parser.add_argument('--qq-message', type=str, help='发送QQ消息')
    parser.add_argument('--qq-groups', type=str, nargs='+', help='目标QQ群列表')
    parser.add_argument('--web-checkin', type=str, help='执行网站签到(JSON路径)')
    parser.add_argument('--ocr-scan', action='store_true', help='OCR扫描屏幕')
    parser.add_argument('--daemon', action='store_true', help='守护进程模式')
    parser.add_argument('--port', type=int, default=8580, help='API端口(daemon)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='API绑定地址')

    args = parser.parse_args()

    from app.utils.logger import logger
    from app.core.scheduler import TaskScheduler

    scheduler = TaskScheduler()

    if args.daemon:
        _run_daemon(scheduler, args.port, args.host)
    elif args.task:
        _run_task_file(scheduler, args.task)
    elif args.qq_message and args.qq_groups:
        _run_qq_send(args.qq_message, args.qq_groups)
    elif args.web_checkin:
        _run_web_checkin(args.web_checkin)
    elif args.ocr_scan:
        _run_ocr_scan()
    else:
        parser.print_help()


def _run_daemon(scheduler, port, host):
    """守护进程模式：调度器 + API服务器"""
    from app.utils.logger import logger
    logger.info(f"启动守护进程模式 | API: http://{host}:{port}")
    
    scheduler.start()
    
    # 启动API服务器
    api_server = None
    try:
        from app.api.server import ApiServer
        api_server = ApiServer(host=host, port=port)
        api_server.start()
    except Exception as e:
        logger.warning(f"API服务器启动失败: {e}")
    
    # 信号处理
    running = True
    def handle_signal(sig, frame):
        nonlocal running
        logger.info("收到退出信号")
        running = False
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if api_server:
            api_server.stop()
        scheduler.stop()
        logger.info("守护进程已停止")


def _run_task_file(scheduler, task_path):
    """执行任务文件"""
    import json
    with open(task_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    tasks_list = tasks if isinstance(tasks, list) else [tasks]
    for t in tasks_list:
        scheduler.add_task(t)
    from app.utils.logger import logger
    logger.info(f"已加载 {len(tasks_list)} 个任务")


def _run_qq_send(message, groups):
    """发送QQ消息"""
    from app.core.qq_automation import QQAutomation
    from app.utils.logger import logger
    qq = QQAutomation()
    for group in groups:
        logger.info(f"向 {group} 发送消息...")
        qq.send_group_message(group, message)


def _run_web_checkin(config_path):
    """执行网站签到"""
    import asyncio
    import json
    from app.core.web_automation import WebAutomation
    from app.utils.logger import logger
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    async def run():
        web = WebAutomation(headless=True)
        if await web.start():
            result = await web.execute_checkin(config)
            logger.info(f"签到结果: {result['message']}")
            await web.stop()
    
    asyncio.run(run())


def _run_ocr_scan():
    """OCR屏幕扫描"""
    from app.core.ocr_engine import OCREngine
    from app.core.screen_scanner import ScreenScanner
    from app.utils.logger import logger
    
    ocr = OCREngine()
    scanner = ScreenScanner()
    
    logger.info("扫描屏幕窗口...")
    windows = scanner.scan_windows()
    logger.info(f"发现 {len(windows)} 个窗口")
    for w in windows[:10]:
        logger.info(f"  窗口: [{w.text}] ({w.x},{w.y}) {w.width}x{w.height}")
    
    logger.info("全屏OCR识别...")
    results = ocr.recognize_from_screen()
    if not results:
        logger.info("未识别到文字")
    for r in results[:20]:
        logger.info(f"  [{r['confidence']:.0%}] {r['text']}")


if __name__ == '__main__':
    main()
