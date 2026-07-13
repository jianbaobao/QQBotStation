"""
屏幕扫描器 - 扫描屏幕窗口、按钮、输入框等UI元素
"""
import sys
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ScreenElement:
    """屏幕元素信息"""
    element_type: str  # 'button', 'text', 'input', 'window', 'image'
    text: str = ''
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    hwnd: int = 0  # Windows窗口句柄


class ScreenScanner:
    """屏幕扫描器 - 识别窗口中的各种UI元素"""

    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            try:
                from app.core.ocr_engine import OCREngine
                self._ocr = OCREngine()
            except ImportError:
                pass
        return self._ocr

    def scan_windows(self) -> List[ScreenElement]:
        """扫描所有可见窗口（复用window_utils）"""
        elements = []
        try:
            from app.utils.window_utils import find_windows_by_title
            for w in find_windows_by_title(''):
                elements.append(ScreenElement(
                    element_type='window',
                    text=w['title'],
                    x=w['x'], y=w['y'],
                    width=w['w'], height=w['h'],
                    hwnd=w['hwnd'],
                ))
        except ImportError:
            pass
        return elements

    def scan_qq_window(self) -> Optional[ScreenElement]:
        """扫描并返回QQ主窗口信息"""
        windows = self.scan_windows()
        for w in windows:
            if 'QQ' in w.text or 'TIM' in w.text:
                return w
        return None

    def scan_window_elements(self, hwnd: int = 0) -> List[ScreenElement]:
        """扫描窗口内的子元素（按钮、输入框等）"""
        elements = []
        if sys.platform == 'win32' and hwnd:
            try:
                import win32gui
                import win32con

                def enum_child(hwnd_child, results):
                    if not win32gui.IsWindowVisible(hwnd_child):
                        return
                    text = win32gui.GetWindowText(hwnd_child)
                    class_name = win32gui.GetClassName(hwnd_child)
                    rect = win32gui.GetWindowRect(hwnd_child)

                    # 根据类名判断元素类型
                    etype = self._classify_element(class_name, text)
                    if etype or text:
                        results.append(ScreenElement(
                            element_type=etype or 'unknown',
                            text=text,
                            x=rect[0], y=rect[1],
                            width=rect[2] - rect[0],
                            height=rect[3] - rect[1],
                            hwnd=hwnd_child,
                        ))

                win32gui.EnumChildWindows(hwnd, enum_child, elements)
            except ImportError:
                pass
        return elements

    def _classify_element(self, class_name: str, text: str) -> str:
        """根据Windows类名推断元素类型"""
        class_name = class_name.lower()
        if 'button' in class_name:
            return 'button'
        if 'edit' in class_name or 'text' in class_name or 'input' in class_name:
            return 'input'
        if 'static' in class_name:
            return 'text'
        if 'list' in class_name or 'listbox' in class_name:
            return 'list'
        if 'combo' in class_name:
            return 'dropdown'
        if 'scroll' in class_name:
            return 'scrollbar'
        return 'unknown'

    def locate_qq_group_chat_area(self, qq_window: ScreenElement) -> Optional[ScreenElement]:
        """在QQ窗口中定位群聊聊天区域"""
        if not qq_window:
            return None
        children = self.scan_window_elements(qq_window.hwnd)
        # 找最大的输入框（聊天输入区域）
        inputs = [c for c in children if c.element_type == 'input']
        if inputs:
            return max(inputs, key=lambda x: x.width * x.height)
        return None

    def scan_with_ocr(self, region: Tuple[int, int, int, int] = None) -> List[dict]:
        """使用OCR扫描屏幕区域中的文字"""
        if self.ocr:
            return self.ocr.recognize_from_screen(region)
        return []

    def get_window_screenshot(self, hwnd: int) -> Optional[str]:
        """截取指定窗口的截图并保存到临时文件"""
        if sys.platform != 'win32':
            return None
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            from PIL import Image

            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            w = right - left
            h = bottom - top

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bitmap)

            save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                   bmpstr, 'raw', 'BGRX', 0, 1)

            temp_path = f"{__import__('tempfile').gettempdir()}/qqbot_scan_{hwnd}.png"
            img.save(temp_path)

            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            return temp_path
        except Exception:
            return None
