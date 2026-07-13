"""
窗口工具 - 查找窗口、获取窗口信息等
统一所有窗口枚举操作的入口，避免重复代码
"""
import sys
import time
import random
from typing import Optional, List, Tuple


def find_windows_by_title(title_keyword: str = '') -> List[dict]:
    """根据标题关键词查找窗口（跨平台）
    
    Args:
        title_keyword: 窗口标题关键词，空字符串返回所有可见窗口
    
    Returns:
        窗口信息列表，每个包含 hwnd/title/class_name/rect/x/y/w/h
    """
    windows = []
    if sys.platform != 'win32':
        return windows
    
    try:
        import win32gui
        
        def enum_callback(hwnd, results):
            if not win32gui.IsWindowVisible(hwnd):
                return
            text = win32gui.GetWindowText(hwnd)
            # 空关键词匹配所有非空标题；非空关键词精确匹配
            if title_keyword:
                if title_keyword.lower() not in text.lower():
                    return
            elif not text:
                return
            rect = win32gui.GetWindowRect(hwnd)
            results.append({
                'hwnd': hwnd,
                'title': text,
                'class_name': win32gui.GetClassName(hwnd),
                'rect': rect,
                'x': rect[0], 'y': rect[1],
                'w': rect[2] - rect[0], 'h': rect[3] - rect[1],
            })
        
        win32gui.EnumWindows(enum_callback, windows)
    except ImportError:
        pass
    
    return windows


def find_qq_window() -> Optional[dict]:
    """查找QQ主窗口（返回面积最大的匹配窗口）"""
    for kw in ['QQ', 'TIM']:
        windows = find_windows_by_title(kw)
        if windows:
            return max(windows, key=lambda w: w['w'] * w['h'])
    return None


def get_screen_size() -> Tuple[int, int]:
    """获取屏幕尺寸"""
    if sys.platform == 'win32':
        try:
            import win32api
            import win32con
            w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            return (w, h)
        except ImportError:
            pass
    return (1920, 1080)


def bring_window_to_front(hwnd: int) -> bool:
    """将窗口带到前台"""
    if sys.platform != 'win32':
        return False
    try:
        import win32gui
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return True
    except Exception:
        return False
