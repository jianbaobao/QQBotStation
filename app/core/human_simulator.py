"""
人机模拟器 - 模拟人类操作行为：鼠标曲线移动、随机延迟、随机偏移
"""
import math
import random
import time
from typing import List, Tuple, Optional


class HumanSimulator:
    """模拟人类操作，让自动化行为更自然"""

    # 人类典型延迟范围（秒）
    TYPING_DELAY = (0.05, 0.25)        # 按键间隔
    CLICK_DELAY = (0.1, 0.4)           # 点击后等待
    MOVE_DELAY = (0.3, 1.2)            # 移动后等待
    SCROLL_DELAY = (0.05, 0.15)        # 滚动间隔
    PAGE_LOAD_DELAY = (1.0, 3.0)       # 页面加载后等待

    @staticmethod
    def random_delay(min_sec: float = 0.1, max_sec: float = 0.5):
        """随机等待一段时间"""
        time.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    def bezier_curve(start: Tuple[int, int], end: Tuple[int, int],
                     control_points: int = 3) -> List[Tuple[int, int]]:
        """生成贝塞尔曲线路径点，模拟人类鼠标移动轨迹"""
        points = []
        # 生成随机控制点，让路径有弧度
        cx1 = start[0] + (end[0] - start[0]) * random.uniform(0.2, 0.8)
        cy1 = start[1] + random.uniform(-100, 100) * random.uniform(0.2, 1.0)
        cx2 = end[0] + random.uniform(-100, 100) * random.uniform(0.2, 1.0)
        cy2 = end[1] + random.uniform(-100, 100) * random.uniform(0.2, 1.0)

        steps = max(8, int(math.dist(start, end) / random.uniform(15, 30)))
        for t in [i / steps for i in range(steps + 1)]:
            # 三次贝塞尔
            x = (1 - t) ** 3 * start[0] + 3 * (1 - t) ** 2 * t * cx1 + \
                3 * (1 - t) * t ** 2 * cx2 + t ** 3 * end[0]
            y = (1 - t) ** 3 * start[1] + 3 * (1 - t) ** 2 * t * cy1 + \
                3 * (1 - t) * t ** 2 * cy2 + t ** 3 * end[1]
            points.append((int(x), int(y)))
        return points

    @staticmethod
    def smooth_move_to(x: int, y: int, duration: float = None):
        """平滑移动鼠标到目标位置，模拟人类轨迹"""
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            cur_x, cur_y = pyautogui.position()
            points = HumanSimulator.bezier_curve((cur_x, cur_y), (x, y))
            if duration is None:
                duration = random.uniform(0.3, 1.0)
            interval = duration / len(points)
            for px, py in points:
                pyautogui.moveTo(px, py, duration=interval, _pause=False)
                time.sleep(interval * 0.3)
        except ImportError:
            pass

    @staticmethod
    def human_click(x: int, y: int, button: str = 'left'):
        """人类化点击 - 移动 + 小停顿 + 点击"""
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            # 移动到目标附近再精确定位
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            HumanSimulator.smooth_move_to(x + offset_x, y + offset_y)
            HumanSimulator.random_delay(0.05, 0.15)
            pyautogui.moveTo(x, y, duration=random.uniform(0.05, 0.15))
            HumanSimulator.random_delay(0.02, 0.08)
            pyautogui.click(button=button)
            HumanSimulator.random_delay(*HumanSimulator.CLICK_DELAY)
        except ImportError:
            pass

    @staticmethod
    def human_double_click(x: int, y: int):
        """人类化双击"""
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            HumanSimulator.human_click(x, y)
            time.sleep(random.uniform(0.1, 0.3))
            pyautogui.click()
            HumanSimulator.random_delay(0.2, 0.5)
        except ImportError:
            pass

    @staticmethod
    def human_type(text: str, min_delay: float = 0.05, max_delay: float = 0.2):
        """模拟人类打字 - 带随机延迟和偶尔的错误纠正"""
        try:
            import pyautogui
            import keyboard
            pyautogui.FAILSAFE = False
            for char in text:
                pyautogui.typewrite(char, interval=random.uniform(min_delay, max_delay))
                # 偶尔模拟打错字停顿
                if random.random() < 0.02:  # 2%概率
                    time.sleep(random.uniform(0.3, 0.8))
        except ImportError:
            pass

    @staticmethod
    def human_scroll(clicks: int = -3):
        """人类化滚动 - 分段滚动"""
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            remaining = abs(clicks)
            while remaining > 0:
                chunk = min(remaining, random.randint(1, 3))
                pyautogui.scroll(-chunk if clicks < 0 else chunk)
                remaining -= chunk
                time.sleep(random.uniform(*HumanSimulator.SCROLL_DELAY))
        except ImportError:
            pass

    @staticmethod
    def random_wait_after_action(action_type: str = 'general'):
        """根据操作类型随机等待"""
        delays = {
            'click': (0.3, 1.0),
            'type': (0.5, 1.5),
            'scroll': (0.5, 1.0),
            'page_load': (1.0, 3.0),
            'screenshot': (0.3, 0.8),
            'general': (0.2, 0.8),
        }
        min_d, max_d = delays.get(action_type, delays['general'])
        time.sleep(random.uniform(min_d, max_d))

    @staticmethod
    def random_offset(bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """在矩形区域内返回一个随机偏移坐标"""
        x = random.randint(bounds[0], bounds[2])
        y = random.randint(bounds[1], bounds[3])
        return (x, y)
