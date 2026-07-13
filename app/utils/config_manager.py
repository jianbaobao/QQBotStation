"""
配置管理 - JSON持久化，支持自动保存和热加载
"""
import os
import json
import threading
from typing import Any, Dict, Optional
from pathlib import Path


from app.utils.singleton import SingletonMixin


class ConfigManager(SingletonMixin):
    """线程安全的JSON配置管理器（同时支持SQLite数据库）"""

    def _init_instance(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        Path(config_dir).mkdir(parents=True, exist_ok=True)
        self._config_dir = config_dir
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._db = None
        self._init_db()
        self._load_all()

    def _init_db(self):
        """初始化数据库连接"""
        try:
            from app.core.database import Database
            self._db = Database()
        except Exception:
            self._db = None

    def _load_all(self):
        """加载所有配置（数据库优先）"""
        # 从数据库加载配置
        if self._db:
            try:
                db_config = self._db.get_all_config()
                if db_config:
                    self._data.update(db_config)
                    return
            except Exception:
                pass
        # 回退：从JSON文件加载
        for fname in ["config.json", "qq_tasks.json", "web_tasks.json", "schedules.json"]:
            path = os.path.join(self._config_dir, fname)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        key = fname.replace('.json', '')
                        self._data[key] = json.load(f)
                except Exception:
                    self._data[key] = {}  # ignore corrupted config

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True):
        with self._lock:
            self._data[key] = value
            if persist:
                self._save(key)
                # 同步到数据库
                if self._db and isinstance(key, str) and isinstance(value, (dict, list, str, int, float, bool)):
                    try:
                        self._db.set_config(key, value)
                    except Exception:
                        pass  # db sync failure is non-critical

    def _save(self, key: str):
        """保存指定key到对应文件"""
        fname = f"{key}.json"
        path = os.path.join(self._config_dir, fname)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._data.get(key, {}), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Config] 保存 {fname} 失败: {e}")

    def save_all(self):
        """保存所有配置"""
        for key in self._data:
            self._save(key)

    def get_app_config(self, key: str, default: Any = None) -> Any:
        """获取应用配置项"""
        cfg = self.get("config", {})
        return cfg.get(key, default)

    def set_app_config(self, key: str, value: Any):
        """设置应用配置项"""
        cfg = self.get("config", {})
        cfg[key] = value
        self.set("config", cfg)

    @property
    def config_path(self) -> str:
        return self._config_dir
