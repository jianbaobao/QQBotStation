"""
任务调度引擎 - 基于APScheduler的定时任务管理
"""
import asyncio
import json
import os
import random
import threading
import time
from typing import List, Dict, Callable, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path


from app.utils.singleton import SingletonMixin


class TaskScheduler(SingletonMixin):
    """任务调度器 - 全局单例"""

    def _init_instance(self, data_dir: str = None):
        from app.utils.logger import logger
        self.log = logger
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self._data_dir = data_dir
        self._scheduler = None
        self._tasks: Dict[str, dict] = {}
        self._running = False
        self._lock = threading.Lock()
        self._event_loop = None
        # 初始化数据库
        self._db = self._get_db()
        self._load_tasks()

    def _get_apscheduler(self):
        """延迟导入APScheduler"""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.triggers.date import DateTrigger
            return BackgroundScheduler, CronTrigger, IntervalTrigger, DateTrigger
        except ImportError:
            return None, None, None, None

    def _get_db(self):
        from .database import Database
        return Database()

    def start(self):
        with self._lock:
            if self._running:
                return
            BG, CT, IT, DT = self._get_apscheduler()
            if BG is None:
                self.log.warning("APScheduler未安装，使用简易调度模式")
                self._running = True
                t = threading.Thread(target=self._simple_scheduler_loop, daemon=True)
                t.start()
                return
            self._scheduler = BG()
            self._scheduler.start()
            self._running = True
            for task_id, task in self._tasks.items():
                self._register_task(task_id, task)
            self.log.info(f"调度器已启动，{len(self._tasks)} 个任务")

    def stop(self):
        """停止调度器"""
        with self._lock:
            if self._scheduler:
                self._scheduler.shutdown(wait=False)
            self._running = False

    def _simple_scheduler_loop(self):
        """简易调度模式（无APScheduler时的备选）"""
        while self._running:
            now = datetime.now()
            with self._lock:
                for task_id, task in list(self._tasks.items()):
                    if not task.get('enabled', True):
                        continue
                    schedule = task.get('schedule', {})
                    next_run = task.get('_next_run')

                    if next_run:
                        try:
                            next_dt = datetime.fromisoformat(next_run)
                        except Exception:
                            next_dt = None
                    else:
                        next_dt = None

                    if next_dt and now >= next_dt:
                        threading.Thread(
                            target=self._execute_task,
                            args=(task_id, task),
                            daemon=True
                        ).start()
                        # 计算下次执行时间
                        self._calc_next_run(task)
            time.sleep(10)

    def _calc_next_run(self, task: dict):
        """计算下次执行时间"""
        schedule = task.get('schedule', {})
        s_type = schedule.get('type', 'cron')

        if s_type == 'interval':
            minutes = schedule.get('interval_minutes', 60)
            task['_next_run'] = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        elif s_type == 'daily':
            time_str = schedule.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            next_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_dt <= datetime.now():
                next_dt += timedelta(days=1)
            task['_next_run'] = next_dt.isoformat()
        elif s_type == 'cron':
            cron_expr = schedule.get('cron_expression', '0 9 * * *')
            try:
                from croniter import croniter
                next_dt = croniter(cron_expr, datetime.now()).get_next(datetime)
                task['_next_run'] = next_dt.isoformat()
            except ImportError:
                task['_next_run'] = (datetime.now() + timedelta(hours=1)).isoformat()

    def _register_task(self, task_id: str, task: dict):
        """向APScheduler注册任务"""
        BG, CT, IT, DT = self._get_apscheduler()
        if not BG or not self._scheduler:
            return

        schedule = task.get('schedule', {})
        s_type = schedule.get('type', 'cron')

        def task_wrapper():
            self._execute_task(task_id, task)

        try:
            if s_type == 'interval':
                minutes = schedule.get('interval_minutes', 60)
                trigger = IT(minutes=minutes)
            elif s_type == 'daily':
                time_str = schedule.get('time', '09:00')
                hour, minute = map(int, time_str.split(':'))
                trigger = CT(hour=hour, minute=minute)
            elif s_type == 'cron':
                cron_expr = schedule.get('cron_expression', '0 9 * * *')
                parts = cron_expr.split()
                if len(parts) == 5:
                    trigger = CT(
                        minute=parts[0], hour=parts[1],
                        day=parts[2], month=parts[3], day_of_week=parts[4]
                    )
                else:
                    trigger = CT(hour=9, minute=0)
            else:
                trigger = CT(hour=9, minute=0)

            self._scheduler.add_job(task_wrapper, trigger, id=task_id,
                                    replace_existing=True, misfire_grace_time=300)
        except Exception as e:
            self.log.error(f"注册任务 {task_id} 失败: {e}")

    def _execute_task(self, task_id: str, task: dict):
        """执行任务"""
        task_type = task.get('type', 'qq')
        self.log.info(f"执行: {task.get('name', task_id)} [{task_type}]")

        try:
            if task_type == 'qq':
                self._execute_qq_task(task)
            elif task_type == 'web':
                asyncio.run(self._execute_web_task(task))
            elif task_type == 'ocr_scan':
                self._execute_ocr_task(task)

            # 更新任务日志
            task['_last_run'] = datetime.now().isoformat()
            task['_last_status'] = 'success'
            self._save_task(task)
            self.add_history({
                'task_id': task_id,
                'task_name': task.get('name', ''),
                'task_type': task_type,
                'status': 'success',
                'message': '执行成功',
            })

        except Exception as e:
            self.log.error(f"执行失败 {task_id}: {e}")
            task['_last_run'] = datetime.now().isoformat()
            task['_last_status'] = f'failed: {str(e)}'
            self._save_task(task)
            self.add_history({
                'task_id': task_id,
                'task_name': task.get('name', ''),
                'task_type': task_type,
                'status': 'failed',
                'message': str(e),
            })

    def _execute_qq_task(self, task: dict):
        """执行QQ消息任务"""
        try:
            from .qq_automation import QQAutomation
            qq = QQAutomation()
            groups = task.get('groups', [])
            message = task.get('message', '')
            if groups and message:
                for group in groups:
                    qq.send_group_message(group, message)
                    time.sleep(random.uniform(5, 15))
            else:
                self.log.warning("QQ任务配置不完整")
        except Exception as e:
            self.log.error(f"QQ任务执行失败: {e}")

    async def _execute_web_task(self, task: dict):
        """执行Web签到任务"""
        try:
            from .web_automation import WebAutomation
            web = WebAutomation(headless=task.get('headless', False))
            if await web.start():
                sites = task.get('sites', [])
                for site in sites:
                    result = await web.execute_checkin(site)
                    self.log.info(f"{result['message']}")
                    await asyncio.sleep(random.uniform(3, 8))
                await web.stop()
        except Exception as e:
            self.log.error(f"Web任务执行失败: {e}")

    def _execute_ocr_task(self, task: dict):
        """执行OCR扫描任务"""
        try:
            from .ocr_engine import OCREngine
            from .screen_scanner import ScreenScanner
            ocr = OCREngine()
            scanner = ScreenScanner()
            target_text = task.get('target_text', '')
            region = task.get('region')
            if target_text:
                result = ocr.find_text_on_screen(target_text, region)
                if result:
                    self.log.info(f"OCR找到目标 '{target_text}' 在 {result}")
                else:
                    self.log.info(f"OCR未找到 '{target_text}'")
            # 扫描窗口
            windows = scanner.scan_windows()
            self.log.info(f"扫描到 {len(windows)} 个窗口")
        except Exception as e:
            self.log.error(f"OCR任务执行失败: {e}")

    # ---- 任务CRUD ----

    def add_task(self, task: dict) -> str:
        """添加任务"""
        import uuid
        task_id = task.get('id', str(uuid.uuid4()))
        task['id'] = task_id
        with self._lock:
            self._tasks[task_id] = task
            self._calc_next_run(task)
            if self._scheduler:
                self._register_task(task_id, task)
        return task_id

    def remove_task(self, task_id: str):
        """删除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                if self._scheduler:
                    try:
                        self._scheduler.remove_job(task_id)
                    except Exception:
                        pass  # remove_job may fail if not registered(task_id)

    def update_task(self, task_id: str, updates: dict):
        """更新任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(updates)
                self._calc_next_run(self._tasks[task_id])
                if self._scheduler:
                    self._register_task(task_id, self._tasks[task_id])
                self._save_task(self._tasks[task_id])

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def get_all_tasks(self, task_type: str = None) -> List[dict]:
        if task_type:
            return [t for t in self._tasks.values() if t.get('type') == task_type]
        return list(self._tasks.values())

    def get_task_count(self, task_type: str = None) -> dict:
        tasks = self.get_all_tasks(task_type)
        return {
            'total': len(tasks),
            'enabled': sum(1 for t in tasks if t.get('enabled', True)),
            'qq': len([t for t in tasks if t.get('type') == 'qq']),
            'web': len([t for t in tasks if t.get('type') == 'web']),
            'ocr': len([t for t in tasks if t.get('type') == 'ocr_scan']),
        }

    def add_history(self, entry: dict):
        entry['_time'] = datetime.now().isoformat()
        if self._db:
            try:
                self._db.add_history(entry)
            except Exception as e:
                self.log.warning(f"写入历史失败: {e}")

    def get_history(self, limit: int = 100, task_id: str = None) -> List[dict]:
        if self._db:
            try:
                return self._db.get_history(limit, task_id)
            except Exception as e:
                self.log.warning(f"读取历史失败: {e}")
        return []

    def get_stats(self) -> dict:
        """获取调度器统计"""
        if self._db:
            try:
                return self._db.get_stats()
            except Exception as e:
                self.log.warning(f"读取统计失败: {e}")
        return self.get_task_count()

    def _load_tasks(self):
        """加载任务（从数据库）"""
        self._tasks.clear()
        if self._db:
            try:
                db_tasks = self._db.get_all_tasks()
                for t in db_tasks:
                    tid = t.get('id', '')
                    if tid:
                        self._tasks[tid] = t
            except Exception as e:
                self.log.error(f"加载失败: {e}")

    def _save_task(self, task: dict):
        """保存任务到数据库（异步写入，不阻塞）"""
        if self._db:
            try:
                self._db.save_task(task)
            except Exception as e:
                self.log.error(f"保存失败: {e}")

    def _remove_task_file(self, task_id: str):
        """从数据库删除任务"""
        if self._db:
            try:
                self._db.delete_task(task_id)
            except Exception as e:
                self.log.warning(f"删除任务失败: {e}")

