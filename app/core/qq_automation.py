"""
QQ桌面客户端自动化 - 通过模拟操作QQ NT客户端窗口实现群消息发送
"""
import sys
import time
import random
import re
from typing import List, Optional
from .human_simulator import HumanSimulator as HS


class QQAutomation:
    """QQ桌面客户端自动化操作"""

    def __init__(self):
        self._qq_window = None
        self._running = False

    def _ensure_qq_running(self) -> bool:
        """确保QQ正在运行，否则尝试启动"""
        try:
            import win32gui
            import win32con
            import subprocess

            # 查找QQ窗口（复用window_utils）
            from app.utils.window_utils import find_windows_by_title
            qq_wins = []
            for kw in ['QQ', 'TIM']:
                for w in find_windows_by_title(kw):
                    qq_wins.append((w['hwnd'], w['title']))
            if qq_wins:
                # 取最大的窗口
                qq_wins.sort(key=lambda x: (
                    win32gui.GetWindowRect(x[0])[2] - win32gui.GetWindowRect(x[0])[0]) *
                    (win32gui.GetWindowRect(x[0])[3] - win32gui.GetWindowRect(x[0])[1]),
                    reverse=True)
                self._qq_window = qq_wins[0]
                return True

            # 尝试启动QQ
            qq_paths = [
                r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
                r"C:\Program Files\Tencent\QQ\Bin\QQ.exe",
                r"C:\Program Files (x86)\Tencent\TIM\Bin\TIM.exe",
            ]
            for path in qq_paths:
                import os
                if os.path.exists(path):
                    subprocess.Popen([path])
                    time.sleep(5)
                    qq_wins = find_qq()
                    if qq_wins:
                        self._qq_window = qq_wins[0]
                        return True
            return False
        except ImportError:
            return False

    def _bring_qq_to_front(self):
        """将QQ窗口置于前台"""
        if self._qq_window:
            try:
                import win32gui
                import win32con
                win32gui.ShowWindow(self._qq_window[0], win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self._qq_window[0])
                time.sleep(0.5)
            except ImportError:
                pass

    def find_group_by_ocr(self, group_name: str) -> bool:
        """通过OCR查找群聊（在QQ窗口搜索框输入群名）"""
        if not self._ensure_qq_running():
            return False
        self._bring_qq_to_front()

        try:
            import pyautogui
            import win32gui
            pyautogui.FAILSAFE = False

            # 点击搜索框（通常在QQ窗口顶部）
            qq_rect = win32gui.GetWindowRect(self._qq_window[0])
            search_x = qq_rect[0] + (qq_rect[2] - qq_rect[0]) // 2
            search_y = qq_rect[1] + 50

            HS.human_click(search_x, search_y)
            HS.random_delay(0.3, 0.6)

            # 清除已有内容
            try:
                import keyboard
                keyboard.press_and_release('ctrl+a')
                time.sleep(0.2)
                keyboard.press_and_release('delete')
            except ImportError:
                pass
            HS.random_delay(0.2, 0.4)

            # 输入群名
            HS.human_type(group_name)
            HS.random_delay(0.5, 1.0)

            # 点击搜索结果
            result_y = search_y + 80
            HS.human_click(search_x, result_y)
            HS.random_delay(0.5, 1.5)
            return True
        except Exception as e:
            import logging; logger = logging.getLogger("QQ"); logger.error(f"搜索群聊失败: {e}")
            return False

    def send_message_to_current_chat(self, message: str):
        """给当前聊天窗口发送消息"""
        self._bring_qq_to_front()
        try:
            import pyautogui
            pyautogui.FAILSAFE = False

            HS.random_delay(0.5, 1.0)

            # 点击输入区域
            if self._qq_window:
                import win32gui
                rect = win32gui.GetWindowRect(self._qq_window[0])
                input_x = rect[0] + (rect[2] - rect[0]) // 2
                input_y = rect[3] - 80
                HS.human_click(input_x, input_y)
                HS.random_delay(0.3, 0.6)

            # 打字发送
            HS.human_type(message)
            HS.random_delay(0.3, 0.8)

            # 按回车发送
            try:
                import keyboard
                keyboard.press_and_release('enter')
            except ImportError:
                pyautogui.press('enter')

            HS.random_delay(0.5, 1.0)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def send_group_message(self, group_name: str, message: str):
        """向指定QQ群发送消息"""
        logger.info(f"正在向群 '{group_name}' 发送消息...")

        if self.find_group_by_ocr(group_name):
            time.sleep(random.uniform(0.5, 1.5))
            self.send_message_to_current_chat(message)
            logger.info(f"消息已发送到群 '{group_name}'")
            return True
        else:
            logger.warning(f"未找到群 '{group_name}'")
            return False

    def send_mass_messages(self, group_names: List[str], message: str,
                           interval_sec: tuple = (30, 60)):
        """向多个群依次发送消息"""
        for i, group in enumerate(group_names):
            logger.info(f"正在处理第 {i+1}/{len(group_names)} 个群: {group}")
            self.send_group_message(group, message)
            if i < len(group_names) - 1:
                delay = random.uniform(*interval_sec)
                logger.info(f"等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)

    @property
    def is_qq_running(self) -> bool:
        return self._ensure_qq_running()
