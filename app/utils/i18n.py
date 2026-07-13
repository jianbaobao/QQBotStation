"""
国际化模块 - i18n 多语言支持 (app/utils/i18n.py)
=================================================
使用 JSON 翻译文件，支持动态语言切换。

用法:
  from app.utils.i18n import _
  print(_('hello'))          # 自动翻译
  print(_('app_name'))       # 配置文件中的键
  set_language('en-US')      # 切换语言
"""
import os
import json
import threading
from pathlib import Path
from typing import Optional


class I18n:
    """轻量级国际化管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.Lock()
        self._lang_dir = self._get_lang_dir()
        self._translations: dict = {}
        self._current_lang = 'zh-CN'
        self._load_language('zh-CN')

    def _get_lang_dir(self) -> str:
        """获取语言文件目录"""
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(base, 'resources', 'lang')
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    def _load_language(self, lang: str):
        """加载指定语言的翻译文件"""
        path = os.path.join(self._lang_dir, f'{lang}.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._translations = json.load(f)
                self._current_lang = lang
                return True
            except Exception:
                pass  # translation file not available
        self._translations = {}
        return False

    def get(self, key: str, *args, **kwargs) -> str:
        """获取翻译文本
        
        Args:
            key: 翻译键或默认文本
            *args: 格式化参数
            **kwargs: 命名格式化参数
        """
        text = self._translations.get(key, key)
        if args:
            text = text.format(*args)
        elif kwargs:
            text = text.format(**kwargs)
        return text

    def set_language(self, lang: str) -> bool:
        """切换语言"""
        with self._lock:
            return self._load_language(lang)

    @property
    def current_language(self) -> str:
        return self._current_lang

    @property
    def available_languages(self) -> list:
        """获取可用语言列表"""
        langs = []
        if os.path.exists(self._lang_dir):
            for f in sorted(os.listdir(self._lang_dir)):
                if f.endswith('.json'):
                    lang = f.replace('.json', '')
                    name = self._translations.get(f'_lang_{lang}', lang)
                    langs.append((lang, name))
        return langs

    def reload(self):
        """重新加载当前语言"""
        self._load_language(self._current_lang)


# 全局实例
_i18n = I18n()


def _(key: str, *args, **kwargs) -> str:
    """翻译函数 - 全局可用"""
    return _i18n.get(key, *args, **kwargs)


def set_language(lang: str) -> bool:
    """切换语言"""
    return _i18n.set_language(lang)


def current_lang() -> str:
    return _i18n.current_language


def available_langs() -> list:
    return _i18n.available_languages


def reload_i18n():
    _i18n.reload()
