"""
OCR引擎 - 基于PaddleOCR的文本识别，支持屏幕区域截图识别
"""
import os
import sys
import time
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path


class OCREngine:
    """OCR识别引擎，封装PaddleOCR并提供屏幕文字识别"""

    def __init__(self, use_gpu: bool = False, lang: str = 'ch'):
        self._ocr = None
        self._use_gpu = use_gpu
        self._lang = lang
        self._ready = False

    def _init_ocr(self):
        """延迟初始化OCR引擎"""
        if self._ready:
            return
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                use_gpu=self._use_gpu,
                show_log=False,
                use_mkl=False  # Windows兼容
            )
            self._ready = True
        except ImportError:
            import logging; logger = logging.getLogger("OCR"); logger.warning("PaddleOCR未安装，尝试使用简易OCR备用方案")
            self._ready = False

    def recognize(self, image_path: str) -> List[dict]:
        """识别图片中的文字"""
        if not self._ready:
            self._init_ocr()
        if not self._ready or self._ocr is None:
            return []
        try:
            result = self._ocr.ocr(image_path, cls=True)
            texts = []
            if result and result[0]:
                for line in result[0]:
                    box, (text, confidence) = line[0], line[1]
                    texts.append({
                        'text': text,
                        'confidence': confidence,
                        'box': box,
                    })
            return texts
        except Exception as e:
            logger.error(f"识别失败: {e}")
            return []

    def recognize_from_screen(self, region: Tuple[int, int, int, int] = None) -> List[dict]:
        """从屏幕区域识别文字

        Args:
            region: (left, top, width, height) 屏幕区域

        Returns:
            识别结果列表
        """
        try:
            import pyautogui
            screenshot = pyautogui.screenshot(region=region)
            temp_path = os.path.join(str(Path.home()), ".qqbot_ocr_temp.png")
            screenshot.save(temp_path)
            return self.recognize(temp_path)
        except Exception as e:
            logger.error(f"屏幕识别失败: {e}")
            return []

    def find_text_on_screen(self, target: str, region: tuple = None,
                            threshold: float = 0.6) -> Optional[Tuple[int, int]]:
        """在屏幕上查找指定文本，返回中心坐标

        Args:
            target: 要查找的文本
            region: 搜索区域 (left, top, width, height)
            threshold: 匹配阈值

        Returns:
            (x, y) 文本中心坐标，未找到返回None
        """
        results = self.recognize_from_screen(region)
        for r in results:
            if target in r['text'] and r['confidence'] >= threshold:
                box = r['box']
                cx = int((box[0][0] + box[2][0]) / 2)
                cy = int((box[0][1] + box[2][1]) / 2)
                return (cx, cy)
        return None

    def find_all_text_on_screen(self, target: str, region: tuple = None,
                                threshold: float = 0.5) -> List[Tuple[int, int, str, float]]:
        """在屏幕上查找所有匹配文本的位置"""
        results = self.recognize_from_screen(region)
        matches = []
        for r in results:
            if target in r['text'] and r['confidence'] >= threshold:
                box = r['box']
                cx = int((box[0][0] + box[2][0]) / 2)
                cy = int((box[0][1] + box[2][1]) / 2)
                matches.append((cx, cy, r['text'], r['confidence']))
        return matches

    def wait_for_text(self, target: str, timeout: float = 30,
                      region: tuple = None, interval: float = 1.0) -> Optional[Tuple[int, int]]:
        """等待屏幕上出现指定文本

        Args:
            target: 要等待的文本
            timeout: 超时秒数
            region: 搜索区域
            interval: 轮询间隔

        Returns:
            文本中心坐标，超时返回None
        """
        start = time.time()
        while time.time() - start < timeout:
            pos = self.find_text_on_screen(target, region)
            if pos:
                return pos
            time.sleep(interval)
        return None
