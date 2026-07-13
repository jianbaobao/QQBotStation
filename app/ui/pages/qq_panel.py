"""
QQ群管理面板 - 完整图形化任务管理
支持：新建/编辑/删除任务、定时调度、测试发送、周期设置、启用/禁用
"""
import uuid
import json
import os
from datetime import datetime, time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTextEdit, QComboBox, QGroupBox, QFormLayout, QTimeEdit,
    QSpinBox, QCheckBox, QMessageBox, QSplitter, QFrame,
    QAbstractItemView, QDialog, QDialogButtonBox, QTabWidget,
    QDateEdit, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QTime, QDate, Signal
from PySide6.QtGui import QFont, QColor


class QQTaskDialog(QDialog):
    """QQ任务编辑对话框"""
    def __init__(self, task_data: dict = None, parent=None):
        super().__init__(parent)
        self.task_data = task_data or {}
        self._init_ui()
        if task_data:
            self._load_data()

    def _init_ui(self):
        self.setWindowTitle("编辑QQ群发任务" if self.task_data else "新建QQ群发任务")
        self.setMinimumSize(550, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1a1b2e; }
            QLabel { color: #c8c8d4; }
            QLineEdit, QTextEdit, QTimeEdit, QSpinBox, QComboBox {
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
                padding: 12px;
                padding-top: 28px;
                font-weight: 600;
                color: #9c9cb0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(8)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("例如: 早安群发")
        basic_layout.addRow("任务名称:", self.edit_name)

        self.edit_message = QTextEdit()
        self.edit_message.setPlaceholderText("输入要发送的消息内容...\n支持多行文本")
        self.edit_message.setMinimumHeight(80)
        basic_layout.addRow("消息内容:", self.edit_message)

        self.edit_groups = QTextEdit()
        self.edit_groups.setPlaceholderText("每行一个QQ群名或群号\n例如:\n班级通知群\n学习交流群\n12345678")
        self.edit_groups.setMaximumHeight(70)
        basic_layout.addRow("目标群组:", self.edit_groups)

        layout.addWidget(basic_group)

        # 调度设置
        sched_group = QGroupBox("调度设置")
        sched_layout = QVBoxLayout(sched_group)

        self.sched_type_group = QButtonGroup(self)
        rb_daily = QRadioButton("每日定时")
        rb_interval = QRadioButton("间隔执行")
        rb_cron = QRadioButton("Cron表达式")
        rb_daily.setChecked(True)

        self.sched_type_group.addButton(rb_daily, 0)
        self.sched_type_group.addButton(rb_interval, 1)
        self.sched_type_group.addButton(rb_cron, 2)

        radio_row = QHBoxLayout()
        radio_row.addWidget(rb_daily)
        radio_row.addWidget(rb_interval)
        radio_row.addWidget(rb_cron)
        radio_row.addStretch()
        sched_layout.addLayout(radio_row)

        # 每日定时
        self.daily_widget = QWidget()
        dw_layout = QHBoxLayout(self.daily_widget)
        dw_layout.setContentsMargins(0, 0, 0, 0)
        dw_layout.addWidget(QLabel("每天"))
        self.edit_time = QTimeEdit(QTime(9, 0))
        self.edit_time.setDisplayFormat("HH:mm")
        dw_layout.addWidget(self.edit_time)
        dw_layout.addWidget(QLabel("执行"))
        dw_layout.addStretch()
        sched_layout.addWidget(self.daily_widget)

        # 间隔执行
        self.interval_widget = QWidget()
        iw_layout = QHBoxLayout(self.interval_widget)
        iw_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_interval = QSpinBox()
        self.edit_interval.setRange(1, 1440)
        self.edit_interval.setValue(60)
        self.edit_interval.setSuffix(" 分钟")
        iw_layout.addWidget(QLabel("每"))
        iw_layout.addWidget(self.edit_interval)
        iw_layout.addWidget(QLabel("执行一次"))
        iw_layout.addStretch()
        sched_layout.addWidget(self.interval_widget)

        # Cron
        self.cron_widget = QWidget()
        cw_layout = QHBoxLayout(self.cron_widget)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_cron = QLineEdit("0 9 * * *")
        self.edit_cron.setPlaceholderText("分 时 日 月 周")
        cw_layout.addWidget(QLabel("表达式:"))
        cw_layout.addWidget(self.edit_cron)
        cw_layout.addStretch()
        sched_layout.addWidget(self.cron_widget)

        # 默认隐藏间隔和cron
        self.interval_widget.setVisible(False)
        self.cron_widget.setVisible(False)
        self.sched_type_group.buttonClicked.connect(self._on_sched_type_changed)

        # 发送延迟
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("群间发送延迟:"))
        self.edit_delay = QSpinBox()
        self.edit_delay.setRange(1, 120)
        self.edit_delay.setValue(5)
        self.edit_delay.setSuffix(" 秒")
        delay_layout.addWidget(self.edit_delay)
        delay_layout.addStretch()
        sched_layout.addLayout(delay_layout)

        layout.addWidget(sched_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("💾 保存任务")
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

    def _on_sched_type_changed(self, btn):
        self.daily_widget.setVisible(btn == self.sched_type_group.button(0))
        self.interval_widget.setVisible(btn == self.sched_type_group.button(1))
        self.cron_widget.setVisible(btn == self.sched_type_group.button(2))

    def _load_data(self):
        """加载已有数据"""
        self.edit_name.setText(self.task_data.get('name', ''))
        self.edit_message.setText(self.task_data.get('message', ''))
        groups = self.task_data.get('groups', [])
        self.edit_groups.setText('\n'.join(groups) if isinstance(groups, list) else '')

        sched = self.task_data.get('schedule', {})
        stype = sched.get('type', 'daily')
        if stype == 'daily':
            t = sched.get('time', '09:00')
            h, m = map(int, t.split(':'))
            self.edit_time.setTime(QTime(h, m))
            self.sched_type_group.button(0).setChecked(True)
            self._on_sched_type_changed(self.sched_type_group.button(0))
        elif stype == 'interval':
            self.edit_interval.setValue(sched.get('interval_minutes', 60))
            self.sched_type_group.button(1).setChecked(True)
            self._on_sched_type_changed(self.sched_type_group.button(1))
        elif stype == 'cron':
            self.edit_cron.setText(sched.get('cron_expression', '0 9 * * *'))
            self.sched_type_group.button(2).setChecked(True)
            self._on_sched_type_changed(self.sched_type_group.button(2))

        self.edit_delay.setValue(self.task_data.get('send_delay', 5))

    def get_task_data(self) -> dict:
        """获取编辑后的任务数据"""
        sched_type = self.sched_type_group.checkedId()
        schedule = {}
        if sched_type == 0:  # daily
            t = self.edit_time.time()
            schedule = {'type': 'daily', 'time': f'{t.hour():02d}:{t.minute():02d}'}
        elif sched_type == 1:  # interval
            schedule = {'type': 'interval', 'interval_minutes': self.edit_interval.value()}
        elif sched_type == 2:  # cron
            schedule = {'type': 'cron', 'cron_expression': self.edit_cron.text()}

        groups_text = self.edit_groups.toPlainText().strip()
        groups = [g.strip() for g in groups_text.split('\n') if g.strip()]

        data = {
            'name': self.edit_name.text().strip(),
            'type': 'qq',
            'message': self.edit_message.toPlainText().strip(),
            'groups': groups,
            'schedule': schedule,
            'send_delay': self.edit_delay.value(),
            'enabled': self.task_data.get('enabled', True),
        }
        if self.task_data and 'id' in self.task_data:
            data['id'] = self.task_data['id']
        return data


class QQPanel(QWidget):
    """QQ群管理页面 - 完整图形化操作"""

    task_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = []
        self._scheduler = None
        self._init_ui()
        self._load_tasks()

    def _get_scheduler(self):
        """获取调度器实例"""
        if self._scheduler is None:
            try:
                from app.core.scheduler import TaskScheduler
                self._scheduler = TaskScheduler()
            except ImportError:
                pass  # scheduler module may not be importable yet
        return self._scheduler

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题区域
        header = QHBoxLayout()
        title = QLabel("💬 QQ 群消息管理")
        title.setObjectName("titleLabel")
        subtitle = QLabel("定时向指定QQ群发送消息，所有操作在图形界面中完成")
        subtitle.setObjectName("subtitleLabel")
        header.addWidget(title)
        header.addStretch()

        # QQ状态指示
        self.status_indicator = QLabel("● 未检测")
        self.status_indicator.setStyleSheet("color: #f44336; font-size: 12px; padding: 4px 12px;")
        header.addWidget(self.status_indicator)

        self.btn_detect_qq = QPushButton("检测QQ")
        self.btn_detect_qq.setFixedWidth(80)
        self.btn_detect_qq.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #3a3b5e;
                border-radius: 6px; color: #8888a0; padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover { border-color: #5c5cf0; color: #e0e0e0; }
        """)
        self.btn_detect_qq.clicked.connect(self._detect_qq)
        header.addWidget(self.btn_detect_qq)

        layout.addLayout(header)

        # 工具栏
        toolbar = QHBoxLayout()

        self.btn_add = QPushButton("＋ 新建任务")
        self.btn_add.setObjectName("btnPrimary")
        self.btn_add.setFixedWidth(110)
        self.btn_add.clicked.connect(self._add_task)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ 编辑")
        self.btn_edit.setFixedWidth(80)
        self.btn_edit.clicked.connect(self._edit_task)
        toolbar.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("🗑 删除")
        self.btn_delete.setObjectName("btnDanger")
        self.btn_delete.setFixedWidth(80)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #d94a4a; color: white;
                border: none; border-radius: 6px; padding: 6px 16px;
            }
            QPushButton:hover { background-color: #e95a5a; }
        """)
        self.btn_delete.clicked.connect(self._delete_task)
        toolbar.addWidget(self.btn_delete)

        toolbar.addStretch()

        self.btn_test = QPushButton("▶ 测试发送")
        self.btn_test.setFixedWidth(100)
        self.btn_test.clicked.connect(self._test_send)
        toolbar.addWidget(self.btn_test)

        self.btn_run_all = QPushButton("▶▶ 执行全部")
        self.btn_run_all.setObjectName("btnPrimary")
        self.btn_run_all.setFixedWidth(100)
        self.btn_run_all.clicked.connect(self._run_all)
        toolbar.addWidget(self.btn_run_all)

        layout.addLayout(toolbar)

        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(9)
        self.task_table.setHorizontalHeaderLabels([
            "任务名称", "目标群组", "内容预览", "执行时间", "周期", "状态", "上次执行", "下次执行", "操作"
        ])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setMinimumHeight(250)
        self.task_table.itemDoubleClicked.connect(lambda: self._edit_task())
        self.task_table.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.task_table)

        # 批量操作提示
        hint = QLabel("💡 提示：双击任务可编辑 · 选中多行可批量删除 · 右键群组列可复制")
        hint.setStyleSheet("color: #5a5a70; font-size: 11px; padding: 4px 0;")
        layout.addWidget(hint)

    def _detect_qq(self):
        """检测QQ客户端状态"""
        try:
            from app.core.qq_automation import QQAutomation
            qq = QQAutomation()
            if qq.is_qq_running:
                self.status_indicator.setText("● QQ运行中")
                self.status_indicator.setStyleSheet("color: #4caf50; font-size: 12px; padding: 4px 12px;")
            else:
                self.status_indicator.setText("● QQ未运行")
                self.status_indicator.setStyleSheet("color: #ff9800; font-size: 12px; padding: 4px 12px;")
        except Exception:
            self.status_indicator.setText("● 检测失败")
            self.status_indicator.setStyleSheet("color: #f44336; font-size: 12px; padding: 4px 12px;")

    def _load_tasks(self):
        """从调度器加载任务列表"""
        scheduler = self._get_scheduler()
        if scheduler:
            self._tasks = scheduler.get_all_tasks('qq')
        self._refresh_table()

    def _refresh_table(self):
        """刷新表格显示"""
        self.task_table.setRowCount(len(self._tasks))
        for i, task in enumerate(self._tasks):
            groups = task.get('groups', [])
            groups_text = ', '.join(groups[:3])
            if len(groups) > 3:
                groups_text += f'... (+{len(groups)-3})'

            msg = task.get('message', '')
            msg_preview = msg[:30] + '...' if len(msg) > 30 else msg

            sched = task.get('schedule', {})
            sched_type = sched.get('type', 'daily')
            if sched_type == 'daily':
                sched_text = f'每天 {sched.get("time", "09:00")}'
            elif sched_type == 'interval':
                sched_text = f'每{sched.get("interval_minutes", 60)}分钟'
            elif sched_type == 'cron':
                sched_text = sched.get('cron_expression', '')
            else:
                sched_text = '-'

            enabled = task.get('enabled', True)
            status_text = "✅ 启用" if enabled else "⏸ 禁用"

            last_run = task.get('_last_run', '')
            if last_run:
                try:
                    last_run = datetime.fromisoformat(last_run).strftime('%m-%d %H:%M')
                except Exception:
                    pass
            else:
                last_run = '-'

            self.task_table.setItem(i, 0, QTableWidgetItem(task.get('name', '')))
            self.task_table.setItem(i, 1, QTableWidgetItem(groups_text))
            self.task_table.setItem(i, 2, QTableWidgetItem(msg_preview))
            self.task_table.setItem(i, 3, QTableWidgetItem(sched_text))
            self.task_table.setItem(i, 4, QTableWidgetItem(''))
            self.task_table.setItem(i, 5, QTableWidgetItem(status_text))
            self.task_table.setItem(i, 6, QTableWidgetItem(last_run))

            # 下次执行
            next_run = task.get('_next_run', '')
            if next_run:
                try:
                    next_run = datetime.fromisoformat(next_run).strftime('%m-%d %H:%M')
                except Exception:
                    pass
            else:
                next_run = '-'
            self.task_table.setItem(i, 7, QTableWidgetItem(next_run))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 1, 2, 1)
            btn_layout.setSpacing(2)

            btn_toggle = QPushButton('⏸' if enabled else '▶')
            btn_toggle.setFixedWidth(28)
            btn_toggle.setFixedHeight(22)
            btn_toggle.setToolTip('点击切换启用/禁用')
            btn_toggle.clicked.connect(lambda checked, r=i: self._toggle_task(r))
            btn_toggle.setStyleSheet(
                'QPushButton { color: #ff9800; font-size: 12px; border: 1px solid #3a3b5e; border-radius: 4px; background: transparent; }'
            )
            btn_layout.addWidget(btn_toggle)

            btn_edit = QPushButton('✏')
            btn_edit.setFixedWidth(28)
            btn_edit.setFixedHeight(22)
            btn_edit.setToolTip('编辑任务')
            btn_edit.clicked.connect(lambda checked, r=i: self._edit_single_task(r))
            btn_edit.setStyleSheet('QPushButton { color: #8888a0; font-size: 12px; border: 1px solid #3a3b5e; border-radius: 4px; background: transparent; }')
            btn_layout.addWidget(btn_edit)

            btn_del = QPushButton('✕')
            btn_del.setFixedWidth(28)
            btn_del.setFixedHeight(22)
            btn_del.setToolTip('删除任务')
            btn_del.clicked.connect(lambda checked, r=i: self._delete_single_task(r))
            btn_del.setStyleSheet('QPushButton { color: #f44336; font-size: 12px; border: 1px solid #3a3b5e; border-radius: 4px; background: transparent; }')
            btn_layout.addWidget(btn_del)

            btn_layout.addStretch()
            self.task_table.setCellWidget(i, 8, btn_widget)

        self._update_count()

    def _update_count(self):
        """更新计数"""
        enabled_count = sum(1 for t in self._tasks if t.get('enabled', True))
        parent = self.parent()
        while parent and not hasattr(parent, '_scheduler'):
            parent = parent.parent()
        if parent and hasattr(parent, 'sidebar'):
            pass  # 侧边栏已显示

    def _add_task(self):
        """新建任务"""
        dialog = QQTaskDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_task_data()
            if not data.get('name'):
                QMessageBox.warning(self, "提示", "请输入任务名称")
                return
            if not data.get('message'):
                QMessageBox.warning(self, "提示", "请输入消息内容")
                return
            if not data.get('groups'):
                QMessageBox.warning(self, "提示", "请至少输入一个QQ群")
                return

            data['id'] = str(uuid.uuid4())
            data['_last_run'] = ''
            data['_last_status'] = ''
            data['created_at'] = datetime.now().isoformat()

            scheduler = self._get_scheduler()
            if scheduler:
                scheduler.add_task(data)
            self._tasks.append(data)

            self._refresh_table()
            self.task_changed.emit()
            QMessageBox.information(self, "成功", f"任务「{data['name']}」已创建")

    def _edit_task(self):
        """编辑选中任务"""
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._tasks):
            QMessageBox.information(self, "提示", "请先选择一个任务")
            return

        task = self._tasks[row].copy()
        dialog = QQTaskDialog(task_data=task, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_task_data()
            if not new_data.get('name'):
                QMessageBox.warning(self, "提示", "请输入任务名称")
                return

            self._tasks[row].update(new_data)
            scheduler = self._get_scheduler()
            if scheduler:
                scheduler.update_task(new_data.get('id', task.get('id', '')), new_data)

            self._refresh_table()
            self.task_changed.emit()
            QMessageBox.information(self, "成功", f"任务「{new_data['name']}」已更新")

    def _delete_task(self):
        """删除选中任务"""
        rows = set()
        for item in self.task_table.selectedItems():
            rows.add(item.row())

        if not rows:
            QMessageBox.information(self, "提示", "请先选择要删除的任务")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(rows)} 个任务吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        scheduler = self._get_scheduler()
        for row in sorted(rows, reverse=True):
            if row < len(self._tasks):
                task = self._tasks[row]
                if scheduler:
                    scheduler.remove_task(task.get('id', ''))
                del self._tasks[row]

        self._refresh_table()
        self.task_changed.emit()
        QMessageBox.information(self, "成功", f"已删除 {len(rows)} 个任务")

    def _toggle_task(self, row: int):
        """切换任务的启用/禁用状态"""
        if 0 <= row < len(self._tasks):
            task = self._tasks[row]
            task['enabled'] = not task.get('enabled', True)
            scheduler = self._get_scheduler()
            if scheduler:
                scheduler.update_task(task.get('id', ''), {'enabled': task['enabled']})
            self._refresh_table()
            self.task_changed.emit()

    def _on_item_clicked(self, item):
        col = item.column()
        if col == 5:
            self._toggle_task(item.row())

    def _edit_single_task(self, row: int):
        self.task_table.selectRow(row)
        self._edit_task()

    def _delete_single_task(self, row: int):
        if 0 <= row < len(self._tasks):
            task = self._tasks[row]
            reply = QMessageBox.question(self, "确认删除",
                f"确定删除任务「{task.get('name', '')}」？",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                scheduler = self._get_scheduler()
                if scheduler:
                    scheduler.remove_task(task.get('id', ''))
                del self._tasks[row]
                self._refresh_table()
                self.task_changed.emit()

    def _test_send(self):
        """测试发送 - 真实调用QQAutomation"""
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._tasks):
            QMessageBox.information(self, "提示", "请先选择一个任务来测试发送")
            return

        task = self._tasks[row]
        msg = task.get('message', '')
        groups = task.get('groups', [])

        if not msg:
            QMessageBox.warning(self, "提示", "该任务没有消息内容")
            return
        if not groups:
            QMessageBox.warning(self, "提示", "该任务没有目标群组")
            return

        from PySide6.QtWidgets import QProgressDialog
        progress = QProgressDialog(f"正在向 {len(groups)} 个群发送测试消息...", "取消", 0, len(groups), self)
        progress.setWindowTitle("测试发送")
        progress.setWindowModality(Qt.WindowModal)

        try:
            from app.core.qq_automation import QQAutomation
            qq = QQAutomation()
            if not qq.is_qq_running:
                QMessageBox.warning(self, "提示", "QQ客户端未运行，请先登录QQ")
                return

            for i, group in enumerate(groups):
                if progress.wasCanceled():
                    break
                progress.setValue(i)
                progress.setLabelText(f"正在发送到群: {group}")
                qq.send_group_message(group, msg)
                import time
                time.sleep(task.get('send_delay', 5))

            progress.setValue(len(groups))
            QMessageBox.information(self, "完成", "测试消息发送完毕！")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送失败: {str(e)}")

    def _run_all(self):
        """执行所有已启用的任务"""
        enabled_tasks = [t for t in self._tasks if t.get('enabled', True)]
        if not enabled_tasks:
            QMessageBox.information(self, "提示", "没有已启用的任务")
            return

        reply = QMessageBox.question(
            self, "确认",
            f"将立即执行 {len(enabled_tasks)} 个已启用任务，确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            from app.core.qq_automation import QQAutomation
            qq = QQAutomation()
            if not qq.is_qq_running:
                QMessageBox.warning(self, "提示", "QQ客户端未运行")
                return

            for task in enabled_tasks:
                groups = task.get('groups', [])
                msg = task.get('message', '')
                for group in groups:
                    qq.send_group_message(group, msg)
                    import time
                    time.sleep(task.get('send_delay', 5))

            QMessageBox.information(self, "完成", "全部任务执行完毕！")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行失败: {str(e)}")
