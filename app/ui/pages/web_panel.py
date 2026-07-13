"""
网页签到面板 - 完整图形化站点管理
支持：站点添加/编辑/删除、预设模板一键应用、真实Playwright执行、签到记录查看
"""
import uuid
import json
import os
import asyncio
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTextEdit, QGroupBox, QFormLayout, QComboBox, QCheckBox,
    QMessageBox, QSplitter, QTabWidget, QAbstractItemView,
    QDialog, QDialogButtonBox, QProgressDialog, QFrame, QListWidget,
    QListWidgetItem, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor


# ========== 预设模板数据库 ==========
SITE_TEMPLATES = {
    "百度贴吧": {
        "url": "https://tieba.baidu.com",
        "checkin_selector": "#signin_btn, .sign_btn, a[title='签到']",
        "success_indicator": "签到成功",
        "steps": [{"selector": ".sign_btn, a[title='签到']", "wait": 2}],
        "need_login": True,
    },
    "哔哩哔哩": {
        "url": "https://www.bilibili.com",
        "checkin_selector": ".bili-checkin, .checkin-btn, .daily-task",
        "success_indicator": "已签到",
        "steps": [{"selector": ".bili-checkin", "wait": 2}],
        "need_login": True,
    },
    "CSDN": {
        "url": "https://www.csdn.net",
        "checkin_selector": "#toolbar-signin-btn, .signin-btn, .btn-checkin",
        "success_indicator": "已签到",
        "steps": [{"selector": "#toolbar-signin-btn", "wait": 2}],
        "need_login": True,
    },
    "V2EX": {
        "url": "https://www.v2ex.com",
        "checkin_selector": "input[value='签到'], .btn-checkin, a[href='/mission/daily']",
        "success_indicator": "已签到",
        "steps": [{"selector": "a[href='/mission/daily']", "wait": 2},
                  {"selector": "input[value='领取X']", "wait": 1}],
        "need_login": True,
    },
    "Hostloc": {
        "url": "https://hostloc.com",
        "checkin_selector": "#checkin, a[href='checkin'], .checkin-btn",
        "success_indicator": "签到",
        "steps": [{"selector": "#checkin", "wait": 2}],
        "need_login": True,
    },
    "52pojie (吾爱破解)": {
        "url": "https://www.52pojie.cn",
        "checkin_selector": "#checkin, .checkin-btn, a[href='k_misign-sign.html']",
        "success_indicator": "已签到",
        "steps": [{"selector": "a[href='k_misign-sign.html']", "wait": 2}],
        "need_login": True,
    },
    "Nga": {
        "url": "https://nga.cn",
        "checkin_selector": "#checkin, .checkin-btn, .signin-btn",
        "success_indicator": "签到成功",
        "steps": [{"selector": ".signin-btn", "wait": 2}],
        "need_login": True,
    },
    "知乎": {
        "url": "https://www.zhihu.com",
        "checkin_selector": ".SignIn-btn, .checkin-btn, .daily-checkin",
        "success_indicator": "已签到",
        "steps": [],
        "need_login": True,
    },
}


class SiteDialog(QDialog):
    """站点编辑对话框"""
    def __init__(self, site_data: dict = None, templates: dict = None, parent=None):
        super().__init__(parent)
        self.site_data = site_data or {}
        self.templates = templates or SITE_TEMPLATES
        self._init_ui()
        if site_data:
            self._load_data()

    def _init_ui(self):
        self.setWindowTitle("编辑站点" if self.site_data else "添加签到站点")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1a1b2e; }
            QLabel { color: #c8c8d4; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background-color: #141526;
                border: 1px solid #2a2b3e;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e0e0e0;
            }
            QGroupBox {
                background-color: #1e1f32;
                border: 1px solid #2a2b3e;
                border-radius: 8px;
                margin-top: 16px;
                padding: 12px; padding-top: 28px;
                font-weight: 600; color: #9c9cb0;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 4px 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 从模板快速选择
        if not self.site_data:
            template_group = QGroupBox("快速选择模板")
            tg_layout = QVBoxLayout(template_group)
            self.template_combo = QComboBox()
            self.template_combo.addItem("-- 手动填写 --", "")
            for name in self.templates:
                self.template_combo.addItem(f"📦 {name}", name)
            self.template_combo.currentIndexChanged.connect(self._on_template_selected)
            tg_layout.addWidget(self.template_combo)
            layout.addWidget(template_group)

        # 基本信息
        basic_group = QGroupBox("站点信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(8)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("例如: 百度贴吧")
        basic_layout.addRow("站点名称:", self.edit_name)

        self.edit_url = QLineEdit()
        self.edit_url.setPlaceholderText("https://...")
        basic_layout.addRow("签到URL:", self.edit_url)

        self.edit_selector = QLineEdit()
        self.edit_selector.setPlaceholderText("CSS选择器，如 #signin_btn")
        basic_layout.addRow("签到按钮:", self.edit_selector)

        self.edit_indicator = QLineEdit("签到成功")
        self.edit_indicator.setPlaceholderText("签到成功后的页面特征文本")
        basic_layout.addRow("成功标识:", self.edit_indicator)

        self.need_login = QCheckBox("需要登录（需填写账号密码）")
        basic_layout.addRow("", self.need_login)

        layout.addWidget(basic_group)

        # 登录信息（可选）
        login_group = QGroupBox("登录信息（可选）")
        login_layout = QFormLayout(login_group)
        login_layout.setSpacing(8)

        self.edit_username_sel = QLineEdit()
        self.edit_username_sel.setPlaceholderText("用户名输入框CSS选择器")
        login_layout.addRow("用户选择器:", self.edit_username_sel)

        self.edit_password_sel = QLineEdit()
        self.edit_password_sel.setPlaceholderText("密码输入框CSS选择器")
        login_layout.addRow("密码选择器:", self.edit_password_sel)

        self.edit_username = QLineEdit()
        self.edit_username.setPlaceholderText("登录用户名/手机号/邮箱")
        login_layout.addRow("用户名:", self.edit_username)

        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        self.edit_password.setPlaceholderText("登录密码")
        login_layout.addRow("密码:", self.edit_password)

        self.edit_login_btn = QLineEdit()
        self.edit_login_btn.setPlaceholderText("登录按钮CSS选择器")
        login_layout.addRow("登录按钮:", self.edit_login_btn)

        layout.addWidget(login_group)

        # 高级设置
        adv_group = QGroupBox("高级设置")
        adv_layout = QFormLayout(adv_group)
        self.edit_wait = QSpinBox()
        self.edit_wait.setRange(1, 30)
        self.edit_wait.setValue(3)
        self.edit_wait.setSuffix(" 秒")
        adv_layout.addRow("执行后等待:", self.edit_wait)
        layout.addWidget(adv_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("💾 保存站点")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.setFixedWidth(110)
        self.btn_save.setStyleSheet("""
            QPushButton#btnPrimary {
                background-color: #5c5cf0; color: white;
                border: none; border-radius: 8px; padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton#btnPrimary:hover { background-color: #6c6cf0; }
        """)
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #3a3b5e; color: #e0e0e0;
                border: none; border-radius: 8px; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #4a4b6e; }
        """)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _on_template_selected(self, idx):
        """选择模板时自动填充"""
        name = self.template_combo.currentData()
        if not name or name not in self.templates:
            return
        tmpl = self.templates[name]
        self.edit_name.setText(name)
        self.edit_url.setText(tmpl.get('url', ''))
        self.edit_selector.setText(tmpl.get('checkin_selector', ''))
        self.edit_indicator.setText(tmpl.get('success_indicator', '签到成功'))
        self.need_login.setChecked(tmpl.get('need_login', True))

    def _load_data(self):
        self.edit_name.setText(self.site_data.get('name', ''))
        self.edit_url.setText(self.site_data.get('url', ''))
        self.edit_selector.setText(self.site_data.get('checkin_selector', ''))
        self.edit_indicator.setText(self.site_data.get('success_indicator', '签到成功'))
        self.need_login.setChecked(self.site_data.get('need_login', False))
        self.edit_username_sel.setText(self.site_data.get('username_selector', ''))
        self.edit_password_sel.setText(self.site_data.get('password_selector', ''))
        self.edit_username.setText(self.site_data.get('username', ''))
        self.edit_password.setText(self.site_data.get('password', ''))
        self.edit_login_btn.setText(self.site_data.get('login_selector', ''))

    def get_site_data(self) -> dict:
        return {
            'name': self.edit_name.text().strip(),
            'url': self.edit_url.text().strip(),
            'checkin_selector': self.edit_selector.text().strip(),
            'success_indicator': self.edit_indicator.text().strip(),
            'need_login': self.need_login.isChecked(),
            'username_selector': self.edit_username_sel.text().strip(),
            'password_selector': self.edit_password_sel.text().strip(),
            'username': self.edit_username.text().strip(),
            'password': self.edit_password.text(),
            'login_selector': self.edit_login_btn.text().strip(),
            'wait_after': self.edit_wait.value(),
        }


class WebPanel(QWidget):
    """网页签到管理页面 - 完整图形化操作"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sites = []
        self._logs = []
        self._init_ui()
        self._load_sites()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        header = QHBoxLayout()
        title = QLabel("🌐 网站签到管理")
        title.setObjectName("titleLabel")
        subtitle = QLabel("配置并自动执行各网站签到和积分领取，所有操作在图形界面中完成")
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

        tabs.addTab(self._create_site_tab(), "📋 站点管理")
        tabs.addTab(self._create_log_tab(), "📝 签到记录")
        tabs.addTab(self._create_template_tab(), "📦 预设模板")

        layout.addWidget(tabs)

    def _create_site_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 工具栏
        toolbar = QHBoxLayout()

        self.btn_add_site = QPushButton("＋ 添加站点")
        self.btn_add_site.setObjectName("btnPrimary")
        self.btn_add_site.setFixedWidth(100)
        self.btn_add_site.clicked.connect(self._add_site)
        toolbar.addWidget(self.btn_add_site)

        self.btn_edit_site = QPushButton("✏️ 编辑")
        self.btn_edit_site.setFixedWidth(70)
        self.btn_edit_site.clicked.connect(self._edit_site)
        toolbar.addWidget(self.btn_edit_site)

        self.btn_delete_site = QPushButton("🗑 删除")
        self.btn_delete_site.setFixedWidth(70)
        self.btn_delete_site.clicked.connect(self._delete_site)
        toolbar.addWidget(self.btn_delete_site)

        self.btn_import = QPushButton("📥 导入")
        self.btn_import.setFixedWidth(60)
        self.btn_import.clicked.connect(self._batch_import)
        toolbar.addWidget(self.btn_import)

        toolbar.addStretch()

        self.btn_sched = QPushButton("⏱ 定时签到")
        self.btn_sched.setObjectName("btnPrimary")
        self.btn_sched.setFixedWidth(100)
        self.btn_sched.clicked.connect(self._create_sched_task)
        toolbar.addWidget(self.btn_sched)

        self.btn_run_selected = QPushButton("▶ 签到选中")
        self.btn_run_selected.setObjectName("btnPrimary")
        self.btn_run_selected.setFixedWidth(100)
        self.btn_run_selected.clicked.connect(self._run_selected)
        toolbar.addWidget(self.btn_run_selected)

        self.btn_run_all = QPushButton("▶▶ 全部签到")
        self.btn_run_all.setObjectName("btnPrimary")
        self.btn_run_all.setFixedWidth(100)
        self.btn_run_all.clicked.connect(self._run_all)
        toolbar.addWidget(self.btn_run_all)

        layout.addLayout(toolbar)

        # 站点表格
        self.site_table = QTableWidget()
        self.site_table.setColumnCount(7)
        self.site_table.setHorizontalHeaderLabels([
            "站点名称", "URL", "签到方式", "需要登录", "状态", "上次签到", "操作"
        ])
        self.site_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.site_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.site_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.site_table.setAlternatingRowColors(True)
        self.site_table.verticalHeader().setVisible(False)
        self.site_table.itemDoubleClicked.connect(lambda: self._edit_site())
        layout.addWidget(self.site_table)

        return tab

    def _create_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self.btn_clear_logs = QPushButton("🗑 清空记录")
        self.btn_clear_logs.setFixedWidth(100)
        self.btn_clear_logs.clicked.connect(lambda: self.log_table.setRowCount(0))
        toolbar.addWidget(self.btn_clear_logs)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(5)
        self.log_table.setHorizontalHeaderLabels(["时间", "站点", "状态", "详情", ""])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.verticalHeader().setVisible(False)
        layout.addWidget(self.log_table)
        return tab

    def _create_template_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QLabel(
            "📦 预设模板包含常见网站的签到配置。选择一个模板点击「应用」即可自动填充站点信息，"
            "你只需补充账号密码即可开始使用。\n")
        info.setWordWrap(True)
        info.setStyleSheet("color: #8888a0; padding: 8px 0; font-size: 13px;")
        layout.addWidget(info)

        # 模板列表
        self.template_list = QTableWidget()
        self.template_list.setColumnCount(4)
        self.template_list.setHorizontalHeaderLabels(["模板名称", "网站URL", "签到方式", "操作"])
        self.template_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.template_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.template_list.setAlternatingRowColors(True)
        self.template_list.verticalHeader().setVisible(False)

        self.template_list.setRowCount(len(SITE_TEMPLATES))
        for i, (name, tmpl) in enumerate(SITE_TEMPLATES.items()):
            self.template_list.setItem(i, 0, QTableWidgetItem(name))
            self.template_list.setItem(i, 1, QTableWidgetItem(tmpl.get('url', '')))
            method = "点击签到" if tmpl.get('checkin_selector') else "页面操作"
            self.template_list.setItem(i, 2, QTableWidgetItem(method))

            btn_apply = QPushButton("📥 应用模板")
            btn_apply.clicked.connect(lambda checked, n=name: self._apply_template(n))
            self.template_list.setCellWidget(i, 3, btn_apply)

        layout.addWidget(self.template_list)

        # 底部说明
        tip = QLabel(
            "💡 提示：点击「应用模板」会自动打开添加站点对话框并填入对应的选择器配置。\n"
            "如果没有你想要的站点，可以手动添加——在站点管理页点击「添加站点」。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #5a5a70; font-size: 11px; padding: 8px 0;")
        layout.addWidget(tip)

        return tab

    def _load_sites(self):
        """加载已保存的站点（从数据库）"""
        try:
            from app.core.database import Database
            self._sites = Database().get_all_sites()
        except Exception:
            self._sites = []
        self._refresh_site_table()

    def _save_sites(self):
        """保存站点列表到数据库"""
        try:
            from app.core.database import Database
            db = Database()
            for site in self._sites:
                db.save_site(site)
        except Exception:
            pass

    def _refresh_site_table(self):
        self.site_table.setRowCount(len(self._sites))
        for i, site in enumerate(self._sites):
            self.site_table.setItem(i, 0, QTableWidgetItem(site.get('name', '')))
            self.site_table.setItem(i, 1, QTableWidgetItem(site.get('url', '')))
            selector = site.get('checkin_selector', '')
            self.site_table.setItem(i, 2, QTableWidgetItem(
                "自动签到" if selector else "待配置"))
            self.site_table.setItem(i, 3, QTableWidgetItem(
                "✅ 需要" if site.get('need_login') else "❌ 不需要"))
            self.site_table.setItem(i, 4, QTableWidgetItem(
                "✅ 已配置" if selector else "⚠️ 未完成"))
            self.site_table.setItem(i, 5, QTableWidgetItem(
                site.get('_last_checkin', '-')))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            btn_check = QPushButton("▶ 签到")
            btn_check.setFixedWidth(50)
            btn_check.clicked.connect(lambda checked, idx=i: self._checkin_site(idx))
            btn_layout.addWidget(btn_check)

            btn_del = QPushButton("✕")
            btn_del.setFixedWidth(24)
            btn_del.clicked.connect(lambda checked, idx=i: self._delete_site_at(idx))
            btn_del.setStyleSheet("QPushButton { color: #f44336; }")
            btn_layout.addWidget(btn_del)

            btn_layout.addStretch()
            self.site_table.setCellWidget(i, 6, btn_widget)

    def _add_site(self):
        dialog = SiteDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_site_data()
            if not data.get('name'):
                QMessageBox.warning(self, "提示", "请输入站点名称")
                return
            data['_last_checkin'] = '-'
            self._sites.append(data)
            self._save_sites()
            self._refresh_site_table()
            QMessageBox.information(self, "成功", f"站点「{data['name']}」已添加")

    def _edit_site(self):
        row = self.site_table.currentRow()
        if row < 0 or row >= len(self._sites):
            QMessageBox.information(self, "提示", "请先选择一个站点")
            return
        dialog = SiteDialog(site_data=self._sites[row].copy(), parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._sites[row].update(dialog.get_site_data())
            self._save_sites()
            self._refresh_site_table()
            QMessageBox.information(self, "成功", "站点已更新")

    def _delete_site(self):
        row = self.site_table.currentRow()
        if row < 0 or row >= len(self._sites):
            QMessageBox.information(self, "提示", "请先选择一个站点")
            return
        self._delete_site_at(row)

    def _delete_site_at(self, idx):
        if 0 <= idx < len(self._sites):
            name = self._sites[idx].get('name', '')
            reply = QMessageBox.question(self, "确认", f"确定删除站点「{name}」？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self._sites[idx]
                self._save_sites()
                self._refresh_site_table()

    def _apply_template(self, name: str):
        """应用预设模板"""
        if name not in SITE_TEMPLATES:
            return
        tmpl = SITE_TEMPLATES[name]
        # 检查是否已存在
        for s in self._sites:
            if s.get('name') == name:
                reply = QMessageBox.question(self, "提示",
                    f"站点「{name}」已存在，是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    s.update({
                        'url': tmpl.get('url', ''),
                        'checkin_selector': tmpl.get('checkin_selector', ''),
                        'success_indicator': tmpl.get('success_indicator', '签到成功'),
                        'need_login': tmpl.get('need_login', True),
                        'steps': tmpl.get('steps', []),
                    })
                    self._save_sites()
                    self._refresh_site_table()
                    QMessageBox.information(self, "成功", f"站点「{name}」已更新")
                return

        # 新建
        dialog = SiteDialog(site_data={
            'name': name,
            'url': tmpl.get('url', ''),
            'checkin_selector': tmpl.get('checkin_selector', ''),
            'success_indicator': tmpl.get('success_indicator', '签到成功'),
            'need_login': tmpl.get('need_login', True),
        }, parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_site_data()
            data['_last_checkin'] = '-'
            self._sites.append(data)
            self._save_sites()
            self._refresh_site_table()
            QMessageBox.information(self, "成功", f"模板「{name}」已应用")

    def _add_log(self, site_name: str, status: str, detail: str = ''):
        """添加签到日志"""
        now = datetime.now().strftime('%m-%d %H:%M:%S')
        self.log_table.insertRow(0)
        self.log_table.setItem(0, 0, QTableWidgetItem(now))
        self.log_table.setItem(0, 1, QTableWidgetItem(site_name))
        status_color = QColor('#4caf50') if '成功' in status else QColor('#f44336')
        item = QTableWidgetItem(status)
        item.setForeground(status_color)
        self.log_table.setItem(0, 2, item)
        self.log_table.setItem(0, 3, QTableWidgetItem(detail[:100]))
        # 限制记录数
        while self.log_table.rowCount() > 500:
            self.log_table.removeRow(self.log_table.rowCount() - 1)

    def _checkin_site(self, idx: int):
        """签到单个站点（真实执行）"""
        if idx < 0 or idx >= len(self._sites):
            return
        site = self._sites[idx]
        name = site.get('name', '未知')

        # 检查Playwright是否可用
        try:
            import playwright
        except ImportError:
            QMessageBox.warning(self, "缺少依赖",
                "未安装Playwright。请运行:\npip install playwright && playwright install chromium")
            return

        # 异步执行
        progress = QProgressDialog(f"正在签到 {name}...", "取消", 0, 0, self)
        progress.setWindowTitle("执行签到")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        try:
            from app.core.web_automation import WebAutomation
            async def do_checkin():
                web = WebAutomation(headless=True)
                if await web.start():
                    result = await web.execute_checkin(site)
                    await web.stop()
                    return result
                return {'success': False, 'message': '浏览器启动失败'}

            result = asyncio.run(do_checkin())
            progress.close()

            site['_last_checkin'] = datetime.now().strftime('%m-%d %H:%M')
            self._save_sites()
            self._refresh_site_table()
            self._add_log(name, "✅ 成功" if result.get('success') else "❌ 失败",
                          result.get('message', ''))

            if result.get('success'):
                QMessageBox.information(self, "签到完成", f"{name}: {result.get('message', '')}")
            else:
                QMessageBox.warning(self, "签到结果", f"{name}: {result.get('message', '')}")

        except Exception as e:
            progress.close()
            self._add_log(name, "❌ 错误", str(e))
            QMessageBox.critical(self, "执行失败", f"签到 {name} 失败:\n{str(e)}")

    def _run_selected(self):
        """签到选中的站点"""
        rows = set()
        for item in self.site_table.selectedItems():
            rows.add(item.row())
        if not rows:
            QMessageBox.information(self, "提示", "请先选择要签到的站点")
            return
        for row in rows:
            self._checkin_site(row)

    def _run_all(self):
        """签到所有已配置的站点"""
        configured = [(i, s) for i, s in enumerate(self._sites) if s.get('checkin_selector')]
        if not configured:
            QMessageBox.information(self, "提示", "没有已配置的站点，请先添加或应用模板")
            return

        reply = QMessageBox.question(self, "确认",
            f"将依次签到 {len(configured)} 个站点，确定继续？",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        for idx, site in configured:
            self._checkin_site(idx)
            import time
            time.sleep(2)

    def _batch_import(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "导入站点配置", "",
            "JSON文件 (*.json);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            count = 0
            for item in data:
                if item.get('name'):
                    item['_last_checkin'] = '-'
                    if not any(s.get('name') == item.get('name') for s in self._sites):
                        self._sites.append(item)
                        count += 1
            self._save_sites()
            self._refresh_site_table()
            QMessageBox.information(self, "导入完成",
                f"成功导入 {count} 个站点" +
                (f"，跳过 {len(data)-count} 个重复" if count < len(data) else ""))
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))

    def _create_sched_task(self):
        configured = [(i, s) for i, s in enumerate(self._sites) if s.get('checkin_selector')]
        if not configured:
            QMessageBox.information(self, "提示", "没有已配置的站点")
            return
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTimeEdit
        from PySide6.QtCore import QTime
        dialog = QDialog(self)
        dialog.setWindowTitle("创建定时签到任务")
        dialog.setFixedSize(350, 180)
        dialog.setStyleSheet("QDialog { background-color: #1a1b2e; } QLabel { color: #c8c8d4; }")
        dl = QVBoxLayout(dialog)
        dl.addWidget(QLabel(f"将每天定时签到 {len(configured)} 个站点:"))
        for _, s in configured[:5]:
            dl.addWidget(QLabel(f"  • {s.get('name', '?')}"))
        te = QTimeEdit()
        te.setDisplayFormat("HH:mm")
        te.setTime(QTime(9, 0))
        dl.addWidget(te)
        br = QHBoxLayout()
        ok_btn = QPushButton("创建")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        br.addStretch()
        br.addWidget(ok_btn)
        br.addWidget(cancel_btn)
        dl.addLayout(br)
        if dialog.exec() != QDialog.Accepted:
            return
        t = te.time()
        task = {
            'name': f'定时签到({len(configured)}站)',
            'type': 'web',
            'sites': [s for _, s in configured],
            'schedule': {'type': 'daily', 'time': f'{t.hour():02d}:{t.minute():02d}'},
            'headless': True, 'enabled': True,
        }
        try:
            from app.core.scheduler import TaskScheduler
            TaskScheduler().add_task(task)
            QMessageBox.information(self, "成功",
                f"每天 {t.hour():02d}:{t.minute():02d} 自动签到 {len(configured)} 个站点")
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
