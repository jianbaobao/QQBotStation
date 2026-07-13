"""
OCR识别面板 - 完整图形化操作
支持：全屏/窗口/区域截图识别、窗口扫描、文字搜索定位、截图保存、结果复制
"""
import os
import sys
import time
import tempfile
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QFormLayout, QSpinBox, QComboBox,
    QMessageBox, QCheckBox, QGridLayout, QFrame, QListWidget,
    QListWidgetItem, QProgressBar, QApplication, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QPixmap, QImage, QClipboard


class OCRWorker(QThread):
    """OCR识别工作线程 - 防止界面卡顿"""
    finished = Signal(list)
    progress = Signal(str)

    def __init__(self, region=None):
        super().__init__()
        self.region = region

    def run(self):
        self.progress.emit("正在截图...")
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=self.region)
            temp_path = os.path.join(tempfile.gettempdir(),
                                     f"qqbot_ocr_{int(time.time())}.png")
            screenshot.save(temp_path)

            self.progress.emit("正在识别文字...")

            # 尝试PaddleOCR
            try:
                from paddleocr import PaddleOCR
                ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
                result = ocr.ocr(temp_path, cls=True)
                texts = []
                if result and result[0]:
                    for line in result[0]:
                        box, (text, confidence) = line[0], line[1]
                        texts.append({
                            'text': text,
                            'confidence': confidence,
                            'box': box,
                        })
                self.finished.emit(texts)
                return
            except ImportError:
                pass

            # 备选：简易OCR（tesseract）
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(temp_path)
                data = pytesseract.image_to_data(img, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
                texts = []
                for i in range(len(data['text'])):
                    if data['text'][i].strip():
                        texts.append({
                            'text': data['text'][i],
                            'confidence': float(data['conf'][i]) / 100 if data['conf'][i] != '-1' else 0.5,
                            'box': [[data['left'][i], data['top'][i]],
                                    [data['left'][i]+data['width'][i], data['top'][i]],
                                    [data['left'][i]+data['width'][i], data['top'][i]+data['height'][i]],
                                    [data['left'][i], data['top'][i]+data['height'][i]]]
                        })
                self.finished.emit(texts)
                return
            except ImportError:
                pass

            self.finished.emit([{'text': f'截图已保存到: {temp_path}\n请安装PaddleOCR或pytesseract获得文字识别能力',
                                 'confidence': 0, 'box': []}])

        except Exception as e:
            self.finished.emit([{'text': f'错误: {str(e)}', 'confidence': 0, 'box': []}])


class WindowScanWorker(QThread):
    """窗口扫描工作线程"""
    finished = Signal(list)

    def run(self):
        windows = []
        if sys.platform == 'win32':
            try:
                import win32gui

                def enum_cb(hwnd, results):
                    if win32gui.IsWindowVisible(hwnd):
                        text = win32gui.GetWindowText(hwnd)
                        if text:
                            rect = win32gui.GetWindowRect(hwnd)
                            results.append({
                                'title': text,
                                'class_name': win32gui.GetClassName(hwnd),
                                'x': rect[0], 'y': rect[1],
                                'w': rect[2] - rect[0], 'h': rect[3] - rect[1],
                                'hwnd': hwnd,
                            })

                win32gui.EnumWindows(enum_cb, windows)
                # 按大小排序
                windows.sort(key=lambda w: w['w'] * w['h'], reverse=True)
            except ImportError:
                windows = [{'title': 'pywin32未安装，无法扫描窗口', 'x': 0, 'y': 0, 'w': 0, 'h': 0}]
        else:
            windows = [{'title': f'窗口扫描仅支持Windows ({sys.platform})', 'x': 0, 'y': 0, 'w': 0, 'h': 0}]

        self.finished.emit(windows)


class OCRPanel(QWidget):
    """OCR识别和屏幕扫描页面 - 完整图形化操作"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ocr_worker = None
        self._window_worker = None
        self._last_screenshot = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        header = QHBoxLayout()
        title = QLabel("📷 OCR 屏幕识别")
        title.setObjectName("titleLabel")
        subtitle = QLabel("屏幕文字识别、窗口扫描、元素定位，全图形化操作")
        subtitle.setObjectName("subtitleLabel")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(subtitle)
        layout.addLayout(header)

        # 主区域
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)

        # ---- 左侧控制面板 ----
        left_panel = QWidget()
        left_panel.setObjectName("card")
        left_panel.setStyleSheet("""
            QWidget#card {
                background-color: #1e1f32;
                border: 1px solid #2a2b3e;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("🖥 识别控制"))
        left_layout.addWidget(QLabel("选择识别区域:"))

        # 识别按钮
        self.btn_scan_full = QPushButton("🖥 扫描全屏")
        self.btn_scan_full.setObjectName("btnPrimary")
        self.btn_scan_full.setFixedHeight(36)
        self.btn_scan_full.clicked.connect(lambda: self._start_ocr(None))
        left_layout.addWidget(self.btn_scan_full)

        self.btn_scan_window = QPushButton("📋 扫描当前窗口")
        self.btn_scan_window.setFixedHeight(36)
        self.btn_scan_window.clicked.connect(self._scan_active_window)
        left_layout.addWidget(self.btn_scan_window)

        self.btn_scan_area = QPushButton("🔲 选择区域（手动）")
        self.btn_scan_area.setFixedHeight(36)
        self.btn_scan_area.clicked.connect(self._scan_custom_area)
        left_layout.addWidget(self.btn_scan_area)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2a2b3e;")
        left_layout.addWidget(sep)

        # 识别设置
        left_layout.addWidget(QLabel("⚙️ 识别设置:"))

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("语言:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["中文+英文", "仅中文", "仅英文"])
        lang_layout.addWidget(self.lang_combo)
        left_layout.addLayout(lang_layout)

        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("延迟(秒):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 30)
        self.delay_spin.setValue(1)
        delay_layout.addWidget(self.delay_spin)
        left_layout.addLayout(delay_layout)

        self.chk_auto_scan = QCheckBox("定时自动扫描")
        left_layout.addWidget(self.chk_auto_scan)

        # 分隔
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #2a2b3e;")
        left_layout.addWidget(sep2)

        # 窗口列表
        left_layout.addWidget(QLabel("🪟 窗口列表:"))
        self.window_list = QListWidget()
        self.window_list.setMinimumHeight(120)
        self.window_list.setStyleSheet("""
            QListWidget {
                background-color: #141526;
                border: 1px solid #2a2b3e;
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 11px;
            }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:hover { background-color: #2a2b3e; }
            QListWidget::item:selected { background-color: #3a3b5e; }
        """)
        self.window_list.itemDoubleClicked.connect(self._on_window_double_click)
        left_layout.addWidget(self.window_list)

        self.btn_refresh_windows = QPushButton("🔄 刷新窗口列表")
        self.btn_refresh_windows.setFixedHeight(28)
        self.btn_refresh_windows.clicked.connect(self._scan_windows)
        left_layout.addWidget(self.btn_refresh_windows)

        left_layout.addStretch()
        main_layout.addWidget(left_panel, 2)

        # ---- 右侧结果显示 ----
        right_panel = QWidget()
        right_panel.setObjectName("card")
        right_panel.setStyleSheet("""
            QWidget#card {
                background-color: #1e1f32;
                border: 1px solid #2a2b3e;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)

        right_layout.addWidget(QLabel("📸 截图预览:"))

        # 截图预览（带滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #141526;
                border: 1px solid #2a2b3e;
                border-radius: 8px;
            }
        """)

        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(450, 280)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            background-color: #141526;
            border-radius: 8px;
            color: #5a5a70;
            font-size: 14px;
        """)
        self.preview_label.setText("点击「扫描全屏」开始识别\n或双击窗口列表中的窗口")
        scroll.setWidget(self.preview_label)
        right_layout.addWidget(scroll)

        # OCR结果
        result_header = QHBoxLayout()
        result_header.addWidget(QLabel("📝 识别结果:"))
        result_header.addStretch()
        self.result_count_label = QLabel("0 条")
        self.result_count_label.setStyleSheet("color: #6a6a80; font-size: 11px;")
        result_header.addWidget(self.result_count_label)
        right_layout.addLayout(result_header)

        self.ocr_result = QTextEdit()
        self.ocr_result.setReadOnly(True)
        self.ocr_result.setPlaceholderText("OCR识别结果将在这里显示...\n点击「扫描全屏」开始")
        self.ocr_result.setMinimumHeight(150)
        self.ocr_result.setStyleSheet("""
            QTextEdit {
                background-color: #141526;
                border: 1px solid #2a2b3e;
                border-radius: 8px;
                color: #e0e0e0;
                padding: 8px;
                font-family: "Microsoft YaHei UI", monospace;
                font-size: 12px;
            }
        """)
        right_layout.addWidget(self.ocr_result)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #141526;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #e0e0e0;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #5c5cf0;
                border-radius: 4px;
            }
        """)
        right_layout.addWidget(self.progress_bar)

        right_layout.addStretch()
        main_layout.addWidget(right_panel, 3)
        layout.addLayout(main_layout)

        # 底部工具栏
        bottom_layout = QHBoxLayout()

        self.btn_save_screenshot = QPushButton("📸 保存截图")
        self.btn_save_screenshot.setFixedWidth(100)
        self.btn_save_screenshot.clicked.connect(self._save_screenshot)
        bottom_layout.addWidget(self.btn_save_screenshot)

        self.btn_copy_result = QPushButton("📋 复制结果")
        self.btn_copy_result.setFixedWidth(100)
        self.btn_copy_result.clicked.connect(self._copy_result)
        bottom_layout.addWidget(self.btn_copy_result)

        self.btn_clear_result = QPushButton("🗑 清空结果")
        self.btn_clear_result.setFixedWidth(100)
        self.btn_clear_result.clicked.connect(lambda: self.ocr_result.clear())
        bottom_layout.addWidget(self.btn_clear_result)

        bottom_layout.addStretch()

        # 文字搜索
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("在识别结果中搜索文字...")
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(self._search_text)
        bottom_layout.addWidget(self.search_input)

        self.btn_search = QPushButton("🔍 搜索")
        self.btn_search.setFixedWidth(60)
        self.btn_search.clicked.connect(self._search_text)
        bottom_layout.addWidget(self.btn_search)

        layout.addLayout(bottom_layout)

    # ---- OCR 操作 ----

    def _start_ocr(self, region=None):
        """启动OCR识别"""
        if self._ocr_worker and self._ocr_worker.isRunning():
            return

        delay = self.delay_spin.value()
        if delay > 0:
            time.sleep(delay)

        self.progress_bar.setVisible(True)
        self.ocr_result.setText("正在识别中，请稍候...")

        self._ocr_worker = OCRWorker(region)
        self._ocr_worker.progress.connect(lambda msg: self.ocr_result.setText(msg))
        self._ocr_worker.finished.connect(self._on_ocr_finished)
        self._ocr_worker.start()

    def _on_ocr_finished(self, results):
        """OCR识别完成"""
        self.progress_bar.setVisible(False)

        if not results:
            self.ocr_result.setText("未识别到文字")
            self.result_count_label.setText("0 条")
            return

        text_output = []
        for r in results:
            text = r.get('text', '')
            conf = r.get('confidence', 0)
            if text and conf > 0.1:  # 过滤低置信度
                text_output.append(f"[{conf:.0%}] {text}")

        if text_output:
            self.ocr_result.setText('\n'.join(text_output))
            self.result_count_label.setText(f"{len(text_output)} 条")
        else:
            self.ocr_result.setText("未识别到有效文字")
            self.result_count_label.setText("0 条")

        # 尝试显示截图
        self._update_preview()

    def _update_preview(self):
        """更新截图预览"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            temp = os.path.join(tempfile.gettempdir(), "qqbot_preview.png")
            screenshot.save(temp)
            pixmap = QPixmap(temp)
            # 缩放以适应
            scaled = pixmap.scaled(450, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self._last_screenshot = temp
        except Exception:
            pass

    def _scan_active_window(self):
        """扫描当前活动窗口"""
        if sys.platform == 'win32':
            try:
                import win32gui
                import win32con
                hwnd = win32gui.GetForegroundWindow()
                rect = win32gui.GetWindowRect(hwnd)
                region = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                self._start_ocr(region)
                title = win32gui.GetWindowText(hwnd)
                self.ocr_result.setText(f"正在扫描窗口: {title}")
            except ImportError:
                QMessageBox.warning(self, "提示", "需要pywin32来扫描窗口")
        else:
            self._start_ocr(None)  # 回退到全屏

    def _scan_custom_area(self):
        """选择区域扫描（用户手动输入坐标）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择识别区域")
        dialog.setFixedSize(320, 180)
        dialog.setStyleSheet("""
            QDialog { background-color: #1a1b2e; }
            QLabel { color: #c8c8d4; }
            QSpinBox { background-color: #141526; border: 1px solid #2a2b3e;
                       border-radius: 4px; color: #e0e0e0; padding: 4px; }
        """)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("输入要识别的屏幕区域坐标（像素）:"))

        grid = QGridLayout()
        from PySide6.QtWidgets import QSpinBox
        self._area_x = QSpinBox(); self._area_x.setRange(0, 9999)
        self._area_y = QSpinBox(); self._area_y.setRange(0, 9999)
        self._area_w = QSpinBox(); self._area_w.setRange(100, 9999); self._area_w.setValue(800)
        self._area_h = QSpinBox(); self._area_h.setRange(100, 9999); self._area_h.setValue(600)

        grid.addWidget(QLabel("X:"), 0, 0); grid.addWidget(self._area_x, 0, 1)
        grid.addWidget(QLabel("Y:"), 0, 2); grid.addWidget(self._area_y, 0, 3)
        grid.addWidget(QLabel("宽:"), 1, 0); grid.addWidget(self._area_w, 1, 1)
        grid.addWidget(QLabel("高:"), 1, 2); grid.addWidget(self._area_h, 1, 3)
        layout.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("开始识别")
        btn_ok.setObjectName("btnPrimary")
        btn_ok.setStyleSheet("QPushButton#btnPrimary { background-color: #5c5cf0; color: white; "
                             "border: none; border-radius: 6px; padding: 6px 16px; }")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        if dialog.exec() == QDialog.Accepted:
            region = (self._area_x.value(), self._area_y.value(),
                      self._area_w.value(), self._area_h.value())
            self._start_ocr(region)

    # ---- 窗口扫描 ----

    def _scan_windows(self):
        """扫描窗口列表"""
        self.window_list.clear()
        self.window_list.addItem("正在扫描窗口...")

        self._window_worker = WindowScanWorker()
        self._window_worker.finished.connect(self._on_windows_scanned)
        self._window_worker.start()

    def _on_windows_scanned(self, windows):
        """窗口扫描完成"""
        self.window_list.clear()
        for w in windows[:30]:  # 最多显示30个
            text = f"{w.get('title', '')[:40]}  ({w.get('x',0)},{w.get('y',0)}) {w.get('w',0)}x{w.get('h',0)}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, w)
            self.window_list.addItem(item)

    def _on_window_double_click(self, item):
        """双击窗口项进行OCR识别"""
        w = item.data(Qt.UserRole)
        if w and w.get('w', 0) > 0 and w.get('h', 0) > 0:
            region = (w['x'], w['y'], w['w'], w['h'])
            self._start_ocr(region)
            self.ocr_result.setText(f"正在扫描窗口: {w.get('title', '')[:30]}...")

    # ---- 辅助功能 ----

    def _save_screenshot(self):
        """保存截图到文件"""
        try:
            import pyautogui
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                self, "保存截图", f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "PNG图片 (*.png)")
            if path:
                pyautogui.screenshot().save(path)
                QMessageBox.information(self, "成功", f"截图已保存到:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存截图失败: {e}")

    def _copy_result(self):
        """复制识别结果到剪贴板"""
        text = self.ocr_result.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "已复制", "识别结果已复制到剪贴板")

    def _search_text(self):
        """在识别结果中搜索文字"""
        keyword = self.search_input.text().strip()
        if not keyword:
            return
        text = self.ocr_result.toPlainText()
        # 只显示匹配的行
        lines = text.split('\n')
        matched = [l for l in lines if keyword.lower() in l.lower()]
        if matched:
            # 高亮显示
            highlighted = '\n'.join(matched)
            idx = self.ocr_result.toPlainText().lower().find(keyword.lower())
            self.ocr_result.setText(highlighted)
            cursor = self.ocr_result.textCursor()
            # 简单滚动到顶部
            cursor.movePosition(cursor.Start)
            self.ocr_result.setTextCursor(cursor)
        else:
            QMessageBox.information(self, "搜索结果", f"未找到包含「{keyword}」的文字")
