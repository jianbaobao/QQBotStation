"""
主窗口 - 完整版
状态栏 + QQ检测 + 调度器状态 + 页面联动 + 系统托盘
"""
import os
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QApplication, QMessageBox, QSystemTrayIcon, QMenu,
    QLabel, QPushButton, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QIcon, QAction, QFont, QColor

from app.ui.title_bar import CustomTitleBar
from app.ui.sidebar import Sidebar
from app.ui.pages.qq_panel import QQPanel
from app.ui.pages.web_panel import WebPanel
from app.ui.pages.ocr_panel import OCRPanel
from app.ui.pages.log_panel import LogPanel
from app.ui.pages.settings_panel import SettingsPanel
from app.utils.logger import logger
from app.utils.config_manager import ConfigManager
from app.core.scheduler import TaskScheduler


class StatusBar(QWidget):
    """底部状态栏 - 显示系统状态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet("""
            QWidget {
                background-color: #141526;
                border-top: 1px solid #2a2b3e;
            }
            QLabel {
                color: #6a6a80;
                font-size: 11px;
                padding: 0 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        # QQ状态
        self.qq_status = QLabel("💬 QQ: ● 未检测")
        layout.addWidget(self.qq_status)

        # 分隔
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #2a2b3e;")
        layout.addWidget(sep1)

        # 调度器状态
        self.sched_status = QLabel("⏱ 调度器: ● 运行中")
        layout.addWidget(self.sched_status)

        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #2a2b3e;")
        layout.addWidget(sep2)

        # 任务数量
        self.task_count = QLabel("📋 任务: 0")
        layout.addWidget(self.task_count)

        layout.addStretch()

        # OCR状态
        self.ocr_status = QLabel("📷 OCR: ● 就绪")
        layout.addWidget(self.ocr_status)

        sep3 = QLabel("|")
        sep3.setStyleSheet("color: #2a2b3e;")
        layout.addWidget(sep3)

        # 时间
        self.time_label = QLabel()
        self._update_time()
        layout.addWidget(self.time_label)

        # 定时更新时间
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_time)
        self._timer.start(1000)

    def _update_time(self):
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def set_qq_status(self, running: bool):
        if running:
            self.qq_status.setText("💬 QQ: ✅ 运行中")
            self.qq_status.setStyleSheet("color: #4caf50; font-size: 11px; padding: 0 8px;")
        else:
            self.qq_status.setText("💬 QQ: ⏹ 未运行")
            self.qq_status.setStyleSheet("color: #ff9800; font-size: 11px; padding: 0 8px;")

    def set_scheduler_status(self, running: bool):
        self.sched_status.setText(f"⏱ 调度器: {'✅ 运行中' if running else '⏹ 已停止'}")

    def set_task_count(self, count: int):
        self.task_count.setText(f"📋 任务: {count}")

    def set_ocr_status(self, text: str, color: str = "#4caf50"):
        self.ocr_status.setText(f"📷 OCR: {text}")
        self.ocr_status.setStyleSheet(f"color: {color}; font-size: 11px; padding: 0 8px;")


class MainWindow(QMainWindow):
    """主窗口 - 完整版"""

    def __init__(self):
        super().__init__()
        self._config = ConfigManager()
        self._scheduler = TaskScheduler()
        self._init_ui()
        self._init_tray()
        self._init_connections()
        self._init_timers()
        self._load_config()
        self._start_scheduler()

    def _init_ui(self):
        self.setWindowTitle("QQBotStation")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # 中心部件
        central = QWidget()
        central.setObjectName("centralWidget")
        central.setStyleSheet("""
            QWidget#centralWidget {
                background-color: #1a1b2e;
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 标题栏
        self.title_bar = CustomTitleBar("QQBotStation · 全能自动化工作站", self)
        self.title_bar.closed.connect(self._on_close)
        self.title_bar.minimized.connect(self.showMinimized)
        main_layout.addWidget(self.title_bar)

        # 主体内容
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        body_layout.addWidget(self.sidebar)

        # 分隔线
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #2a2b3e;")
        body_layout.addWidget(separator)

        # 页面容器
        content_widget = QWidget()
        content_widget.setObjectName("contentArea")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #1a1b2e;")

        # 创建各页面
        self.qq_panel = QQPanel()
        self.web_panel = WebPanel()
        self.ocr_panel = OCRPanel()
        self.log_panel = LogPanel()
        self.settings_panel = SettingsPanel()

        self.stack.addWidget(self.qq_panel)
        self.stack.addWidget(self.web_panel)
        self.stack.addWidget(self.ocr_panel)
        self.stack.addWidget(self.log_panel)
        self.stack.addWidget(self.settings_panel)

        content_layout.addWidget(self.stack)
        body_layout.addWidget(content_widget, 1)

        main_layout.addWidget(body, 1)

        # 状态栏
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)

        # 居中
        self._center_window()

        # 初始检测
        self._detect_qq()

    def _center_window(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _init_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("QQBotStation · 全能自动化工作站")

        tray_menu = QMenu()
        show_action = QAction("🪟 显示窗口", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        # 快捷操作
        qq_action = QAction("💬 QQ面板", self)
        qq_action.triggered.connect(lambda: self._switch_page(0))
        tray_menu.addAction(qq_action)

        web_action = QAction("🌐 签到面板", self)
        web_action.triggered.connect(lambda: self._switch_page(1))
        tray_menu.addAction(web_action)

        tray_menu.addSeparator()

        quit_action = QAction("🚪 退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _init_connections(self):
        """初始化页面间的连接"""
        self.qq_panel.task_changed.connect(self._update_task_count)
        self.settings_panel.btn_save.clicked.connect(self._load_config)
        self.ocr_panel.ocr_result.textChanged.connect(self._on_ocr_result)

    def _init_timers(self):
        """初始化定时器"""
        # 每30秒检测QQ状态
        self._qq_timer = QTimer()
        self._qq_timer.timeout.connect(self._detect_qq)
        self._qq_timer.start(30000)

        # 每分钟更新任务计数
        self._task_timer = QTimer()
        self._task_timer.timeout.connect(self._update_task_count)
        self._task_timer.start(60000)

    def _switch_page(self, index: int):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        # 更新侧边栏高亮
        self.sidebar.set_active(index)

    def _start_scheduler(self):
        self._scheduler.start()
        self.status_bar.set_scheduler_status(True)
        logger.info("任务调度器已启动")

    def _load_config(self):
        """加载配置到各页面"""
        try:
            cfg = self._config.get_app_config('general', {})
            # 开机自启
            if cfg.get('auto_start', False):
                self._set_auto_start(True)
            # 窗口状态
            if cfg.get('start_minimized', False):
                QTimer.singleShot(100, self._on_close)
        except Exception as e:
            logger.debug(f"加载配置: {e}")

    def _set_auto_start(self, enable: bool):
        """设置开机自启（Windows注册表）"""
        if sys.platform != 'win32':
            return
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
            app_path = sys.argv[0] if sys.argv[0].endswith('.exe') else sys.executable
            if enable:
                winreg.SetValueEx(key, 'QQBotStation', 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, 'QQBotStation')
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.debug(f"开机自启设置失败: {e}")

    def _detect_qq(self):
        """检测QQ状态"""
        try:
            from app.core.qq_automation import QQAutomation
            qq = QQAutomation()
            running = qq.is_qq_running
            self.status_bar.set_qq_status(running)
            # 更新QQ面板的指示器
            if hasattr(self.qq_panel, 'status_indicator'):
                if running:
                    self.qq_panel.status_indicator.setText("● QQ运行中")
                    self.qq_panel.status_indicator.setStyleSheet(
                        "color: #4caf50; font-size: 12px; padding: 4px 12px;")
                else:
                    self.qq_panel.status_indicator.setText("● QQ未运行")
                    self.qq_panel.status_indicator.setStyleSheet(
                        "color: #ff9800; font-size: 12px; padding: 4px 12px;")
        except Exception as e:
            logger.debug(f"QQ检测失败: {e}")

    def _update_task_count(self):
        """更新任务计数"""
        tasks = self._scheduler.get_all_tasks()
        enabled = sum(1 for t in tasks if t.get('enabled', True))
        self.status_bar.set_task_count(f"{len(tasks)} (运行: {enabled})")

    def _on_ocr_result(self):
        text = self.ocr_panel.ocr_result.toPlainText()
        if '错误' in text or '失败' in text:
            self.status_bar.set_ocr_status("失败", "#f44336")
        elif text and '等待' not in text:
            lines = [l for l in text.split('\n') if l.strip()]
            self.status_bar.set_ocr_status(f"{len(lines)} 条", "#4caf50")
        else:
            self.status_bar.set_ocr_status("就绪")

    def _on_close(self):
        """关闭到托盘"""
        self.hide()
        self._tray.showMessage(
            "QQBotStation",
            "程序已最小化到系统托盘，双击图标恢复窗口",
            QSystemTrayIcon.Information,
            3000
        )

    def _quit_app(self):
        """退出应用"""
        logger.info("正在退出应用...")
        self._scheduler.stop()
        self._qq_timer.stop()
        self._task_timer.stop()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self._on_close()
