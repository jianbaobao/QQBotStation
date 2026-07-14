"""
数据库模块 - SQLite 持久化存储 (app/core/database.py)
=====================================================
替代JSON文件存储，支持任务、历史记录、配置和站点管理

数据表:
  tasks      - 任务持久化 (id, name, type, enabled, config, schedule, ...)
  history    - 执行历史 (task_id, status, message, time)
  sites      - 网站签到站点 (name, url, selectors, credentials, steps)
  config     - 键值对配置

线程安全: 每线程独立连接 (threading.local)
单例: 继承 SingletonMixin
兼容: 同时写数据库 + JSON备份
"""
import base64
import json
import os
import threading
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


from app.utils.singleton import SingletonMixin


class Database(SingletonMixin):
    """SQLite 数据库管理器 - 线程安全单例"""

    @staticmethod
    def _encrypt(val: str) -> str:
        """简单编码密码（非加密，防明文泄露）"""
        if not val:
            return ''
        return base64.b64encode(val.encode()).decode()

    @staticmethod
    def _decrypt(val: str) -> str:
        """解码密码"""
        if not val:
            return ''
        try:
            return base64.b64decode(val.encode()).decode()
        except Exception:
            return val

    def _init_instance(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "qqbot.db")
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._local = threading.local()
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_tables(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        conn.executescript("""
            -- 任务表
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'qq',
                enabled INTEGER NOT NULL DEFAULT 1,
                config TEXT NOT NULL DEFAULT '{}',
                schedule TEXT NOT NULL DEFAULT '{}',
                next_run TEXT,
                last_run TEXT,
                last_status TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- 执行历史表
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                task_name TEXT,
                task_type TEXT,
                status TEXT NOT NULL,
                message TEXT DEFAULT '',
                time TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            );

            -- 网站签到站点表
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                checkin_selector TEXT DEFAULT '',
                success_indicator TEXT DEFAULT '签到成功',
                need_login INTEGER DEFAULT 0,
                username_selector TEXT DEFAULT '',
                password_selector TEXT DEFAULT '',
                username TEXT DEFAULT '',
                password TEXT DEFAULT '',
                login_selector TEXT DEFAULT '',
                steps TEXT DEFAULT '[]',
                wait_after INTEGER DEFAULT 3,
                last_checkin TEXT DEFAULT '-',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- 配置表 (键值对)
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- 索引
            CREATE INDEX IF NOT EXISTS idx_history_time ON history(time DESC);
            CREATE INDEX IF NOT EXISTS idx_history_task_id ON history(task_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
            CREATE INDEX IF NOT EXISTS idx_tasks_enabled ON tasks(enabled);
        """)
        conn.commit()

    # ==================== 任务操作 ====================

    def save_task(self, task: dict) -> str:
        """保存任务（插入或更新）"""
        conn = self._get_conn()
        task_id = task.get('id', '')
        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())
            task['id'] = task_id

        now = datetime.now().isoformat()
        config = {k: v for k, v in task.items()
                  if k not in ('id', 'name', 'type', 'enabled', 'schedule',
                               '_next_run', '_last_run', '_last_status',
                               'created_at', 'updated_at')}
        # 清理 config 中的内部字段
        for key in list(config.keys()):
            if key.startswith('_'):
                del config[key]

        conn.execute("""
            INSERT INTO tasks (id, name, type, enabled, config, schedule,
                               next_run, last_run, last_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    CASE WHEN ? IS NULL THEN ? ELSE ? END)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                enabled = excluded.enabled,
                config = excluded.config,
                schedule = excluded.schedule,
                next_run = excluded.next_run,
                last_run = excluded.last_run,
                last_status = excluded.last_status,
                updated_at = excluded.updated_at
        """, (
            task_id,
            task.get('name', ''),
            task.get('type', 'qq'),
            1 if task.get('enabled', True) else 0,
            json.dumps(config, ensure_ascii=False),
            json.dumps(task.get('schedule', {}), ensure_ascii=False),
            task.get('_next_run', ''),
            task.get('_last_run', ''),
            task.get('_last_status', ''),
            task.get('created_at', now),
            now, task.get('created_at'), now
        ))
        conn.commit()
        return task_id

    def delete_task(self, task_id: str):
        """删除任务"""
        conn = self._get_conn()
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取单个任务"""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def get_all_tasks(self, task_type: str = None) -> List[dict]:
        """获取所有任务"""
        conn = self._get_conn()
        if task_type:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE type = ? ORDER BY created_at DESC",
                (task_type,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row) -> dict:
        """数据库行转任务字典"""
        task = {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'enabled': bool(row['enabled']),
            'schedule': json.loads(row['schedule'] or '{}'),
            '_next_run': row['next_run'] or '',
            '_last_run': row['last_run'] or '',
            '_last_status': row['last_status'] or '',
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }
        # 合并 config 字段
        config = json.loads(row['config'] or '{}')
        task.update(config)
        return task

    # ==================== 历史记录 ====================

    def add_history(self, entry: dict):
        """添加执行历史"""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO history (task_id, task_name, task_type, status, message, time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.get('task_id', ''),
            entry.get('task_name', ''),
            entry.get('task_type', ''),
            entry.get('status', ''),
            entry.get('message', ''),
            entry.get('_time', datetime.now().isoformat()),
        ))
        conn.commit()

    def get_history(self, limit: int = 100, task_id: str = None) -> List[dict]:
        """获取执行历史"""
        conn = self._get_conn()
        if task_id:
            rows = conn.execute(
                "SELECT * FROM history WHERE task_id = ? ORDER BY time DESC LIMIT ?",
                (task_id, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY time DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

    def clear_history(self):
        """清空历史记录"""
        conn = self._get_conn()
        conn.execute("DELETE FROM history")
        conn.commit()

    # ==================== 站点管理 ====================

    def save_site(self, site: dict) -> int:
        """保存站点（插入或更新）"""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        site_id = site.get('id', 0)

        if site_id:
            conn.execute("""
                UPDATE sites SET name=?, url=?, checkin_selector=?,
                    success_indicator=?, need_login=?, username_selector=?,
                    password_selector=?, username=?, password=?,
                    login_selector=?, steps=?, wait_after=?,
                    last_checkin=?, updated_at=?
                WHERE id=?
            """, (
                site['name'], site.get('url', ''),
                site.get('checkin_selector', ''),
                site.get('success_indicator', '签到成功'),
                1 if site.get('need_login') else 0,
                site.get('username_selector', ''),
                self._encrypt(site.get('password_selector', '')),
                site.get('username', ''),
                self._encrypt(site.get('password', '')),
                site.get('login_selector', ''),
                json.dumps(site.get('steps', []), ensure_ascii=False),
                site.get('wait_after', 3),
                site.get('_last_checkin', '-'),
                now, site_id
            ))
        else:
            cursor = conn.execute("""
                INSERT INTO sites (name, url, checkin_selector, success_indicator,
                    need_login, username_selector, password_selector, username,
                    password, login_selector, steps, wait_after, last_checkin,
                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                site['name'], site.get('url', ''),
                site.get('checkin_selector', ''),
                site.get('success_indicator', '签到成功'),
                1 if site.get('need_login') else 0,
                site.get('username_selector', ''),
                self._encrypt(site.get('password_selector', '')),
                site.get('username', ''),
                self._encrypt(site.get('password', '')),
                site.get('login_selector', ''),
                json.dumps(site.get('steps', []), ensure_ascii=False),
                site.get('wait_after', 3),
                site.get('_last_checkin', '-'),
                now, now
            ))
            site_id = cursor.lastrowid
        conn.commit()
        return site_id

    def delete_site(self, site_id: int):
        """删除站点"""
        conn = self._get_conn()
        conn.execute("DELETE FROM sites WHERE id = ?", (site_id,))
        conn.commit()

    def get_all_sites(self) -> List[dict]:
        """获取所有站点"""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM sites ORDER BY name").fetchall()
        sites = []
        for r in rows:
            site = dict(r)
            site['need_login'] = bool(site['need_login'])
            site['steps'] = json.loads(site['steps'] or '[]')
            site['id'] = site['id']
            site['password'] = self._decrypt(site.get('password', ''))
            site['password_selector'] = self._decrypt(site.get('password_selector', ''))
            sites.append(site)
        return sites

    # ==================== 配置管理 ====================

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        if row:
            try:
                return json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                return row['value']
        return default

    def set_config(self, key: str, value: Any):
        """设置配置项"""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, json.dumps(value, ensure_ascii=False)))
        conn.commit()

    def get_all_config(self) -> dict:
        """获取所有配置"""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM config").fetchall()
        config = {}
        for row in rows:
            try:
                config[row['key']] = json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                config[row['key']] = row['value']
        return config

    # ==================== 统计 ====================

    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        conn = self._get_conn()
        stats = {}
        try:
            stats['tasks_total'] = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            stats['tasks_enabled'] = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE enabled=1").fetchone()[0]
            stats['tasks_qq'] = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE type='qq'").fetchone()[0]
            stats['tasks_web'] = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE type='web'").fetchone()[0]
            stats['sites_total'] = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
            stats['history_total'] = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
            stats['db_size'] = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0
        except Exception as e:
            import logging; logging.getLogger("DB").warning(f"获取统计失败: {e}")
        return stats

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
