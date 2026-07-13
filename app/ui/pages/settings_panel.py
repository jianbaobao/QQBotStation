"""
设置面板 - 完整图形化配置管理
支持：所有配置可视化编辑、真实读写ConfigManager、配置导入/导出、系统信息
"""
import os
import sys
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFormLayout, QCheckBox, QSpinBox,
    QComboBox, QMessageBox, QTabWidget, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class SettingsPanel(QWidget):
    """设置页面 - 完整图形化配置"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = None
        self._init_ui()
        self._load_config()

    def _get_config(self):
        if self._config is None:
            try:
                from app.utils.config_manager import ConfigManager
                self._config = ConfigManager()
            except Exception:
                pass
        return self._config

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        header = QHBoxLayout()
        title = QLabel("⚙️ 系统设置")
        title.setObjectName("titleLabel")
        subtitle = QLabel("所有配置都在图形界面中完成，点击「保存设置」生效")
        subtitle.setObjectName("subtitleLabel")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(subtitle)
        layout.addLayout(header)

        # 选项卡
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #1a1b2e;
                border: 1px solid #2a2b3e;
                border-radius: 8px;
                padding: 16px;
            }
            QTabBar::tab {
                background-color: #1e1f32; color: #8888a0;
                padding: 10px 24px;
                border: 1px solid #2a2b3e; border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                margin-right: 2px; font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #3a3b5e; color: #e0e0e0;
                border-bottom: 2px solid #5c5cf0;
            }
            QTabBar::tab:hover { background-color: #2a2b3e; }
        """)

        tabs.addTab(self._create_basic_tab(), "📌 基本设置")
        tabs.addTab(self._create_qq_tab(), "💬 QQ 配置")
        tabs.addTab(self._create_browser_tab(), "🌐 浏览器配置")
        tabs.addTab(self._create_system_tab(), "🔧 系统")

        layout.addWidget(tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QPushButton("💾 保存设置")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setFixedWidth(120)
        self.btn_save.setStyleSheet("""
            QPushButton#btnPrimary {
                background-color: #5c5cf0; color: white;
                border: none; border-radius: 8px; padding: 8px 20px;
                font-size: 13px; font-weight: 500;
            }
            QPushButton#btnPrimary:hover { background-color: #6c6cf0; }
        """)
        self.btn_save.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save)

        self.btn_reset = QPushButton("🔄 恢复默认")
        self.btn_reset.setFixedWidth(100)
        self.btn_reset.clicked.connect(self._reset_config)
        btn_layout.addWidget(self.btn_reset)

        layout.addLayout(btn_layout)

    def _create_basic_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 常规设置
        general_group = QGroupBox("常规")
        general_group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1f32; border: 1px solid #2a2b3e;
                border-radius: 8px; margin-top: 16px; padding: 12px; padding-top: 28px;
                font-weight: 600; color: #9c9cb0;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 4px 10px;
            }
        """)
        general_layout = QFormLayout(general_group)
        general_layout.setSpacing(10)

        self.start_minimized = QCheckBox("启动时最小化到系统托盘")
        general_layout.addRow("", self.start_minimized)

        self.auto_start = QCheckBox("开机自动启动（创建快捷方式到启动目录）")
        general_layout.addRow("", self.auto_start)

        self.enable_tray = QCheckBox("启用系统托盘图标")
        self.enable_tray.setChecked(True)
        general_layout.addRow("", self.enable_tray)

        # 语言选择
        lang_layout = QHBoxLayout()
        self.lang_combo = QComboBox()
        try:
            from app.utils.i18n import available_langs
            for code, name in available_langs():
                self.lang_combo.addItem(name, code)
        except Exception:
            self.lang_combo.addItem("简体中文", "zh-CN")
            self.lang_combo.addItem("English", "en-US")
        lang_layout.addWidget(self.lang_combo)
        general_layout.addRow("界面语言:", lang_layout)

        layout.addWidget(general_group)

        # 任务设置
        task_group = QGroupBox("任务默认设置")
        task_group.setStyleSheet(general_group.styleSheet())
        task_layout = QFormLayout(task_group)
        task_layout.setSpacing(10)

        self.default_interval = QSpinBox()
        self.default_interval.setRange(10, 1440)
        self.default_interval.setValue(60)
        self.default_interval.setSuffix(" 分钟")
        task_layout.addRow("默认检查间隔:", self.default_interval)

        self.retry_count = QSpinBox()
        self.retry_count.setRange(0, 10)
        self.retry_count.setValue(3)
        task_layout.addRow("失败重试次数:", self.retry_count)

        self.concurrent_tasks = QSpinBox()
        self.concurrent_tasks.setRange(1, 10)
        self.concurrent_tasks.setValue(3)
        task_layout.addRow("最大并发任务数:", self.concurrent_tasks)

        layout.addWidget(task_group)
        layout.addStretch()
        return tab

    def _create_qq_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        group_style = """
            QGroupBox {
                background-color: #1e1f32; border: 1px solid #2a2b3e;
                border-radius: 8px; margin-top: 16px; padding: 12px; padding-top: 28px;
                font-weight: 600; color: #9c9cb0;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 4px 10px;
            }
        """

        # QQ路径
        path_group = QGroupBox("QQ客户端路径")
        path_group.setStyleSheet(group_style)
        path_layout = QHBoxLayout(path_group)
        self.qq_path = QLineEdit()
        self.qq_path.setPlaceholderText("自动检测(留空则自动查找)...")
        path_layout.addWidget(self.qq_path)

        btn_browse = QPushButton("浏览...")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(lambda: self._browse_file(self.qq_path, "选择QQ.exe"))
        path_layout.addWidget(btn_browse)

        btn_auto = QPushButton("自动检测")
        btn_auto.setFixedWidth(80)
        btn_auto.clicked.connect(self._auto_detect_qq)
        path_layout.addWidget(btn_auto)

        layout.addWidget(path_group)

        # 发送设置
        send_group = QGroupBox("消息发送设置")
        send_group.setStyleSheet(group_style)
        send_layout = QFormLayout(send_group)
        send_layout.setSpacing(10)

        self.typing_speed = QComboBox()
        self.typing_speed.addItems(["极慢 (更像人类)", "慢", "正常", "快"])
        self.typing_speed.setCurrentIndex(2)
        send_layout.addRow("打字速度:", self.typing_speed)

        self.send_delay = QSpinBox()
        self.send_delay.setRange(1, 60)
        self.send_delay.setValue(5)
        self.send_delay.setSuffix(" 秒")
        send_layout.addRow("群间发送延迟:", self.send_delay)

        self.enable_ocr_search = QCheckBox("启用OCR搜索群聊（当直接查找失败时）")
        self.enable_ocr_search.setChecked(True)
        send_layout.addRow("", self.enable_ocr_search)

        layout.addWidget(send_group)

        # 安全设置
        safety_group = QGroupBox("安全设置")
        safety_group.setStyleSheet(group_style)
        safety_layout = QFormLayout(safety_group)
        safety_layout.setSpacing(10)

        self.max_messages = QSpinBox()
        self.max_messages.setRange(1, 100)
        self.max_messages.setValue(20)
        safety_layout.addRow("单次最大发送群数:", self.max_messages)

        self.global_switch = QCheckBox("✅ 全局QQ消息发送已启用 (取消勾选则暂停所有QQ任务)")
        self.global_switch.setChecked(True)
        safety_layout.addRow("", self.global_switch)

        layout.addWidget(safety_group)
        layout.addStretch()
        return tab

    def _create_browser_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        group_style = """
            QGroupBox {
                background-color: #1e1f32; border: 1px solid #2a2b3e;
                border-radius: 8px; margin-top: 16px; padding: 12px; padding-top: 28px;
                font-weight: 600; color: #9c9cb0;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 4px 10px;
            }
        """

        chrome_group = QGroupBox("Playwright 浏览器设置")
        chrome_group.setStyleSheet(group_style)
        chrome_layout = QFormLayout(chrome_group)
        chrome_layout.setSpacing(10)

        self.headless_mode = QCheckBox("无头模式（不显示浏览器窗口，推荐服务器使用）")
        chrome_layout.addRow("", self.headless_mode)

        self.browser_lang = QComboBox()
        self.browser_lang.addItems(["zh-CN (简体中文)", "en-US (English)", "ja-JP (日本語)"])
        chrome_layout.addRow("浏览器语言:", self.browser_lang)

        self.page_load_timeout = QSpinBox()
        self.page_load_timeout.setRange(10, 120)
        self.page_load_timeout.setValue(30)
        self.page_load_timeout.setSuffix(" 秒")
        chrome_layout.addRow("页面加载超时:", self.page_load_timeout)

        self.screenshot_before = QCheckBox("签到前截图保存")
        chrome_layout.addRow("", self.screenshot_before)

        self.screenshot_after = QCheckBox("签到后截图保存（便于确认结果）")
        self.screenshot_after.setChecked(True)
        chrome_layout.addRow("", self.screenshot_after)

        layout.addWidget(chrome_group)

        # 数据目录
        data_group = QGroupBox("浏览器数据目录")
        data_group.setStyleSheet(group_style)
        data_layout = QHBoxLayout(data_group)
        self.data_dir = QLineEdit()
        self.data_dir.setPlaceholderText("默认: ./data/browser_data")
        btn_browse_data = QPushButton("浏览...")
        btn_browse_data.setFixedWidth(80)
        btn_browse_data.clicked.connect(lambda: self._browse_dir(self.data_dir))
        data_layout.addWidget(self.data_dir)
        data_layout.addWidget(btn_browse_data)
        layout.addWidget(data_group)

        # 浏览器状态
        status_group = QGroupBox("浏览器引擎状态")
        status_group.setStyleSheet(group_style)
        status_layout = QVBoxLayout(status_group)
        self.browser_status = QLabel("● 未检测")
        self.browser_status.setStyleSheet("color: #8888a0; font-size: 13px;")
        status_layout.addWidget(self.browser_status)
        btn_check = QPushButton("🔍 检测Playwright")
        btn_check.setFixedWidth(120)
        btn_check.clicked.connect(self._check_playwright)
        status_layout.addWidget(btn_check)
        layout.addWidget(status_group)

        layout.addStretch()
        return tab

    def _create_system_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        group_style = """
            QGroupBox {
                background-color: #1e1f32; border: 1px solid #2a2b3e;
                border-radius: 8px; margin-top: 16px; padding: 12px; padding-top: 28px;
                font-weight: 600; color: #9c9cb0;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 4px 10px;
            }
        """

        # 系统信息
        info_group = QGroupBox("系统信息")
        info_group.setStyleSheet(group_style)
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(6)

        info_layout.addRow("应用版本:", QLabel("QQBotStation v1.0.0"))
        info_layout.addRow("Python版本:", QLabel(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))
        info_layout.addRow("运行平台:", QLabel(sys.platform))
        info_layout.addRow("UI框架:", QLabel("PySide6"))
        info_layout.addRow("OCR引擎:", QLabel(self._get_ocr_status()))
        info_layout.addRow("浏览器引擎:", QLabel(self._get_browser_status()))

        layout.addWidget(info_group)

        # 数据管理
        data_group = QGroupBox("数据管理")
        data_group.setStyleSheet(group_style)
        data_layout = QVBoxLayout(data_group)
        data_layout.setSpacing(8)

        btn_row1 = QHBoxLayout()
        self.btn_export_config = QPushButton("📤 导出全部配置")
        self.btn_export_config.setFixedWidth(130)
        self.btn_export_config.clicked.connect(self._export_config)
        btn_row1.addWidget(self.btn_export_config)

        self.btn_import_config = QPushButton("📥 导入配置")
        self.btn_import_config.setFixedWidth(100)
        self.btn_import_config.clicked.connect(self._import_config)
        btn_row1.addWidget(self.btn_import_config)

        btn_row1.addStretch()
        data_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.btn_clear_data = QPushButton("🗑 清除所有数据")
        self.btn_clear_data.setFixedWidth(130)
        self.btn_clear_data.setStyleSheet("""
            QPushButton { background-color: #d94a4a; color: white;
                border: none; border-radius: 6px; padding: 6px 16px;
            }
            QPushButton:hover { background-color: #e95a5a; }
        """)
        self.btn_clear_data.clicked.connect(self._clear_all_data)
        btn_row2.addWidget(self.btn_clear_data)

        btn_row2.addStretch()
        data_layout.addLayout(btn_row2)

        label = QLabel("⚠️ 清除数据将删除所有任务配置和登录状态，此操作不可撤销。建议先导出备份。")
        label.setWordWrap(True)
        label.setStyleSheet("color: #ff9800; font-size: 11px; padding: 4px 0;")
        data_layout.addWidget(label)

        layout.addWidget(data_group)
        layout.addStretch()
        return tab

    def _load_config(self):
        """加载配置到界面"""
        config = self._get_config()
        if config is None:
            return

        # 基本设置
        general = config.get_app_config('general', {})
        self.start_minimized.setChecked(general.get('start_minimized', False))
        self.auto_start.setChecked(general.get('auto_start', False))
        self.enable_tray.setChecked(general.get('enable_tray', True))

        # 语言设置
        lang_code = general.get('language', 'zh-CN')
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == lang_code:
                self.lang_combo.setCurrentIndex(i)
                break

        # 任务设置
        task_defaults = config.get_app_config('task_defaults', {})
        self.default_interval.setValue(task_defaults.get('check_interval_minutes', 60))
        self.retry_count.setValue(task_defaults.get('retry_count', 3))
        self.concurrent_tasks.setValue(task_defaults.get('max_concurrent', 3))

        # QQ设置
        qq_cfg = config.get_app_config('qq', {})
        self.qq_path.setText(qq_cfg.get('path', ''))
        speed_map = {'极慢 (更像人类)': 0, '慢': 1, '正常': 2, '快': 3}
        speed = qq_cfg.get('typing_speed', '正常')
        self.typing_speed.setCurrentIndex(speed_map.get(speed, 2))
        self.send_delay.setValue(qq_cfg.get('inter_group_delay_seconds', 5))
        self.enable_ocr_search.setChecked(qq_cfg.get('enable_ocr_search', True))
        self.max_messages.setValue(qq_cfg.get('max_groups_per_batch', 20))
        self.global_switch.setChecked(qq_cfg.get('enabled', True))

        # 浏览器设置
        web_cfg = config.get_app_config('web', {})
        self.headless_mode.setChecked(web_cfg.get('headless', False))
        lang_map = {'zh-CN': 0, 'en-US': 1, 'ja-JP': 2}
        self.browser_lang.setCurrentIndex(lang_map.get(web_cfg.get('language', 'zh-CN'), 0))
        self.page_load_timeout.setValue(web_cfg.get('page_load_timeout_seconds', 30))
        self.screenshot_before.setChecked(web_cfg.get('screenshot_before_checkin', False))
        self.screenshot_after.setChecked(web_cfg.get('screenshot_after_checkin', True))
        self.data_dir.setText(web_cfg.get('data_dir', ''))

    def _save_config(self):
        """保存配置到ConfigManager"""
        config = self._get_config()
        if config is None:
            QMessageBox.warning(self, "错误", "配置管理器不可用")
            return

        try:
            # 基本设置
            config.set_app_config('general', {
                'start_minimized': self.start_minimized.isChecked(),
                'auto_start': self.auto_start.isChecked(),
                'enable_tray': self.enable_tray.isChecked(),
                'language': self.lang_combo.currentData() or 'zh-CN',
            })

            # 切换语言
            try:
                from app.utils.i18n import set_language
                set_language(self.lang_combo.currentData() or 'zh-CN')
            except Exception:
                pass

            # 任务设置
            config.set_app_config('task_defaults', {
                'check_interval_minutes': self.default_interval.value(),
                'retry_count': self.retry_count.value(),
                'max_concurrent': self.concurrent_tasks.value(),
            })

            # QQ设置
            speed_map = {0: '极慢 (更像人类)', 1: '慢', 2: '正常', 3: '快'}
            config.set_app_config('qq', {
                'path': self.qq_path.text().strip(),
                'typing_speed': speed_map.get(self.typing_speed.currentIndex(), '正常'),
                'inter_group_delay_seconds': self.send_delay.value(),
                'enable_ocr_search': self.enable_ocr_search.isChecked(),
                'max_groups_per_batch': self.max_messages.value(),
                'enabled': self.global_switch.isChecked(),
            })

            # 浏览器设置
            lang_map = {0: 'zh-CN', 1: 'en-US', 2: 'ja-JP'}
            config.set_app_config('web', {
                'headless': self.headless_mode.isChecked(),
                'language': lang_map.get(self.browser_lang.currentIndex(), 'zh-CN'),
                'page_load_timeout_seconds': self.page_load_timeout.value(),
                'screenshot_before_checkin': self.screenshot_before.isChecked(),
                'screenshot_after_checkin': self.screenshot_after.isChecked(),
                'data_dir': self.data_dir.text().strip(),
            })

            config.save_all()
            QMessageBox.information(self, "成功", "设置已保存并生效")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {str(e)}")

    def _reset_config(self):
        """恢复默认配置"""
        reply = QMessageBox.question(self, "确认",
            "确定要恢复所有设置为默认值吗？\n此操作不会删除任务数据。",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 重置UI控件
            self.start_minimized.setChecked(False)
            self.auto_start.setChecked(False)
            self.enable_tray.setChecked(True)
            self.default_interval.setValue(60)
            self.retry_count.setValue(3)
            self.concurrent_tasks.setValue(3)
            self.qq_path.clear()
            self.typing_speed.setCurrentIndex(2)
            self.send_delay.setValue(5)
            self.enable_ocr_search.setChecked(True)
            self.max_messages.setValue(20)
            self.global_switch.setChecked(True)
            self.headless_mode.setChecked(False)
            self.browser_lang.setCurrentIndex(0)
            self.page_load_timeout.setValue(30)
            self.screenshot_before.setChecked(False)
            self.screenshot_after.setChecked(True)
            self.data_dir.clear()

            QMessageBox.information(self, "成功", "已恢复默认设置\n点击「保存设置」使更改生效")

    def _export_config(self):
        """导出配置到文件"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", f"qqbot_config_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.json",
            "JSON文件 (*.json)")
        if path:
            config = self._get_config()
            if config:
                try:
                    data = {
                        'general': config.get_app_config('general', {}),
                        'task_defaults': config.get_app_config('task_defaults', {}),
                        'qq': config.get_app_config('qq', {}),
                        'web': config.get_app_config('web', {}),
                    }
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    QMessageBox.information(self, "成功", f"配置已导出到:\n{path}")
                except Exception as e:
                    QMessageBox.warning(self, "失败", str(e))

    def _import_config(self):
        """从文件导入配置"""
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON文件 (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                config = self._get_config()
                if config:
                    for key, value in data.items():
                        if isinstance(value, dict):
                            config.set(key, value, persist=False)
                    config.save_all()
                    self._load_config()
                    QMessageBox.information(self, "成功", "配置已导入并加载")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"导入失败: {str(e)}")

    def _clear_all_data(self):
        """清除所有数据"""
        reply = QMessageBox.question(self, "⚠️ 危险操作",
            "⚠️ 确定要清除所有数据吗？\n\n"
            "这将删除:\n"
            "• 所有QQ任务配置\n"
            "• 所有网站签到配置\n"
            "• 浏览器登录状态\n"
            "• 所有设置\n\n"
            "此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 二次确认
            reply2 = QMessageBox.question(self, "再次确认",
                "请输入「yes」确认清除所有数据",
                QMessageBox.Yes | QMessageBox.No)
            if reply2 == QMessageBox.Yes:
                config = self._get_config()
                if config:
                    import shutil
                    import glob
                    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
                    for f in glob.glob(os.path.join(data_dir, "*.json")):
                        try:
                            os.remove(f)
                        except Exception:
                            pass
                QMessageBox.information(self, "已清除", "所有数据已清除，应用将重启后生效")

    def _browse_file(self, line_edit: QLineEdit, title: str):
        path, _ = QFileDialog.getOpenFileName(self, title, line_edit.text() or "")
        if path:
            line_edit.setText(path)

    def _browse_dir(self, line_edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "选择目录", line_edit.text() or "")
        if path:
            line_edit.setText(path)

    def _auto_detect_qq(self):
        """自动检测QQ路径"""
        common_paths = [
            r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
            r"C:\Program Files\Tencent\QQ\Bin\QQ.exe",
            r"C:\Program Files (x86)\Tencent\TIM\Bin\TIM.exe",
            r"D:\Program Files\Tencent\QQ\Bin\QQ.exe",
            r"D:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                self.qq_path.setText(path)
                QMessageBox.information(self, "已找到", f"QQ路径: {path}")
                return
        QMessageBox.information(self, "未找到", "未在常见位置找到QQ，请手动选择")

    def _check_playwright(self):
        """检测Playwright安装状态"""
        try:
            import playwright
            ver = getattr(playwright, '__version__', '已安装')
            self.browser_status.setText(f"● Playwright {ver}")
            self.browser_status.setStyleSheet("color: #4caf50; font-size: 13px;")
            QMessageBox.information(self, "检测结果", f"Playwright {ver} 已就绪")
        except ImportError:
            self.browser_status.setText("● Playwright 未安装")
            self.browser_status.setStyleSheet("color: #f44336; font-size: 13px;")
            reply = QMessageBox.question(self, "未安装",
                "Playwright 未安装，是否现在安装？\n\n安装命令:\npip install playwright\nplaywright install chromium",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                QMessageBox.information(self, "安装提示",
                    "请打开终端执行:\n\npip install playwright\nplaywright install chromium")

    def _get_ocr_status(self) -> str:
        """获取OCR引擎状态文本"""
        try:
            import paddleocr
            return "✅ PaddleOCR 已就绪"
        except ImportError:
            try:
                import pytesseract
                return "✅ Tesseract 已就绪"
            except ImportError:
                return "⚠️ OCR引擎未安装"

    def _get_browser_status(self) -> str:
        """获取浏览器引擎状态"""
        try:
            import playwright
            return "✅ Playwright 已安装"
        except ImportError:
            return "⚠️ Playwright 未安装"
