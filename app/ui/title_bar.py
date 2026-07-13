"""
自定义标题栏 - 模仿现代桌面应用风格
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFont


class CustomTitleBar(QWidget):
    """自定义无边框标题栏"""

    minimized = Signal()
    maximized = Signal()
    closed = Signal()
    double_clicked = Signal()

    def __init__(self, title: str = "QQBotStation", parent=None):
        super().__init__(parent)
        self._dragging = False
        self._drag_start = QPoint()
        self._parent = parent
        self.setObjectName("titleBar")
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 图标
        self.icon_label = QLabel("🤖")
        self.icon_label.setFixedWidth(40)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 18px;")

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: #c8c8d4;
            font-size: 13px;
            font-weight: 600;
            padding-left: 4px;
        """)

        # 弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(0, 1)  # Expanding

        # 窗口控制按钮
        self.btn_min = QPushButton("─")
        self.btn_max = QPushButton("□")
        self.btn_close = QPushButton("×")

        for btn in (self.btn_min, self.btn_max, self.btn_close):
            btn.setFixedSize(42, 42)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #8888a0;
                    font-size: 16px;
                    border-radius: 0;
                }
                QPushButton:hover {
                    background-color: #2a2b3e;
                    color: #e0e0e0;
                }
            """)

        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8888a0;
                font-size: 18px;
                border-radius: 0;
            }
            QPushButton:hover {
                background-color: #e34a4a;
                color: white;
            }
        """)

        self.btn_min.clicked.connect(self.minimized.emit)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.closed.emit)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(spacer, 1)
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    def _toggle_maximize(self):
        if self._parent:
            if self._parent.isMaximized():
                self._parent.showNormal()
                self.btn_max.setText("□")
            else:
                self._parent.showMaximized()
                self.btn_max.setText("❐")
        self.maximized.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and self._parent:
            delta = event.globalPosition().toPoint() - self._drag_start
            if self._parent.isMaximized():
                return
            self._parent.move(self._parent.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()

    def mouseDoubleClickEvent(self, event):
        self._toggle_maximize()
        self.double_clicked.emit()
        event.accept()
