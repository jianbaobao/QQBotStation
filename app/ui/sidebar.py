"""
侧边栏导航 - 模仿WechatOnCloud风格
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QButtonGroup
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont


class Sidebar(QWidget):
    """左侧导航侧边栏"""

    page_changed = Signal(int)  # 页面索引

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # Logo
        self.logo_label = QLabel("🤖")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setFixedHeight(48)
        self.logo_label.setStyleSheet("font-size: 26px; padding: 4px;")

        # 按钮组
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.nav_items = [
            (0, "💬", "QQ群"),       # QQ Panel
            (1, "🌐", "网页"),       # Web Tasks
            (2, "📷", "OCR"),        # OCR Scan
            (3, "📋", "日志"),       # Logs
            (4, "⚙️", "设置"),       # Settings
        ]

        self.buttons = []
        for idx, icon, tooltip in self.nav_items:
            btn = QPushButton(icon)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 20px;
                    border-radius: 12px;
                    margin: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #2a2b3e;
                }
                QPushButton:checked {
                    background-color: #3a3b5e;
                }
            """)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn, 0, Qt.AlignCenter)
            self.buttons.append(btn)

        layout.addStretch(1)

        # 版本号
        self.version_label = QLabel("v1.0")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("color: #5a5a70; font-size: 10px; padding: 8px;")
        layout.addWidget(self.version_label)

        # 选中第一个
        self.buttons[0].setChecked(True)

        # 信号连接
        self.btn_group.idClicked.connect(self._on_btn_clicked)

    def _on_btn_clicked(self, idx):
        self.page_changed.emit(idx)

    def set_active(self, index: int):
        """设置当前激活的页面"""
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
