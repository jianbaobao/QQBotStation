"""
单例模式混入类 - 统一所有模块的单例实现
用法: class MyClass(SingletonMixin): ...
"""
import threading


class SingletonMixin:
    """线程安全的单例混入，使用 __init__ 保护防止重复初始化"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, *args, **kwargs):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._init_instance(*args, **kwargs)
            self._initialized = True

    def _init_instance(self, *args, **kwargs):
        """子类重写此方法替代 __init__"""
        pass

    @classmethod
    def reset_instance(cls):
        """重置单例（仅测试用）"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
