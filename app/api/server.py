"""
REST API 服务器 - FastAPI 实现
提供完整的远程管理接口，支持 Web 管理页面
"""
import asyncio
import json
import os
import sys
import threading
from typing import List, Optional
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Query, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Pydantic 模型（仅 FastAPI 模式需要）
if HAS_FASTAPI:
    class TaskCreate(BaseModel):
        name: str
        type: str = "qq"
        message: str = ""
        groups: List[str] = []
        schedule: dict = {"type": "daily", "time": "09:00"}
        send_delay: int = 5
        enabled: bool = True

    class TaskUpdate(BaseModel):
        name: Optional[str] = None
        message: Optional[str] = None
        groups: Optional[List[str]] = None
        schedule: Optional[dict] = None
        send_delay: Optional[int] = None
        enabled: Optional[bool] = None

    class SiteCreate(BaseModel):
        name: str
        url: str = ""
        checkin_selector: str = ""
        success_indicator: str = "签到成功"
        need_login: bool = False
        username_selector: str = ""
        password_selector: str = ""
        username: str = ""
        password: str = ""
        login_selector: str = ""
        wait_after: int = 3

    class SiteUpdate(BaseModel):
        name: Optional[str] = None
        url: Optional[str] = None
        checkin_selector: Optional[str] = None
        success_indicator: Optional[str] = None
        need_login: Optional[bool] = None
        username_selector: Optional[str] = None
        password_selector: Optional[str] = None
        username: Optional[str] = None
        password: Optional[str] = None
        login_selector: Optional[str] = None
        wait_after: Optional[int] = None

    class MessageSend(BaseModel):
        message: str
        groups: List[str]
        delay: int = 5


class ApiServer:
    """API 服务器管理器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8580):
        self._host = host
        self._port = port
        self._server = None
        self._thread = None
        self._running = False
        self._app = None
        self._scheduler = None

    def _get_scheduler(self):
        if self._scheduler is None:
            try:
                from app.core.scheduler import TaskScheduler
                self._scheduler = TaskScheduler()
            except Exception as e:
                import logging; logging.getLogger("API").warning(f"获取调度器失败: {e}")
        return self._scheduler

    def _create_app(self):
        """创建 FastAPI 应用并注册路由"""
        app = FastAPI(
            title="QQBotStation API",
            description="全能自动化工作站 - 远程管理接口",
            version="1.0.0",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        scheduler = self._get_scheduler()

        # ==================== 系统状态 ====================
        @app.get("/api/status")
        async def get_status():
            sched = scheduler
            stats = sched.get_stats() if sched else {}
            return {
                "status": "running",
                "version": "1.0.0",
                "platform": sys.platform,
                "stats": stats,
                "time": datetime.now().isoformat(),
            }

        # ==================== 任务管理 ====================
        @app.get("/api/tasks")
        async def list_tasks(type: Optional[str] = None):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            return {"tasks": sched.get_all_tasks(type)}

        @app.get("/api/tasks/{task_id}")
        async def get_task(task_id: str):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            task = sched.get_task(task_id)
            if not task:
                raise HTTPException(404, "任务不存在")
            return task

        @app.post("/api/tasks")
        async def create_task(task: TaskCreate):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            data = task.model_dump()
            data['_last_run'] = ''
            data['_last_status'] = ''
            data['created_at'] = datetime.now().isoformat()
            task_id = sched.add_task(data)
            return {"id": task_id, "message": "任务已创建"}

        @app.put("/api/tasks/{task_id}")
        async def update_task(task_id: str, updates: TaskUpdate):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            existing = sched.get_task(task_id)
            if not existing:
                raise HTTPException(404, "任务不存在")
            update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
            sched.update_task(task_id, update_data)
            return {"message": "任务已更新"}

        @app.delete("/api/tasks/{task_id}")
        async def delete_task(task_id: str):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            sched.remove_task(task_id)
            return {"message": "任务已删除"}

        @app.post("/api/tasks/{task_id}/execute")
        async def execute_task(task_id: str):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            task = sched.get_task(task_id)
            if not task:
                raise HTTPException(404, "任务不存在")
            # 异步执行
            def run():
                from app.core.scheduler import TaskScheduler
                ts = TaskScheduler()
                ts._execute_task(task_id, task)
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            return {"message": f"任务「{task.get('name', '')}」已开始执行"}

        @app.post("/api/tasks/{task_id}/toggle")
        async def toggle_task(task_id: str):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            task = sched.get_task(task_id)
            if not task:
                raise HTTPException(404, "任务不存在")
            new_state = not task.get('enabled', True)
            sched.update_task(task_id, {'enabled': new_state})
            return {"enabled": new_state, "message": f"任务已{'启用' if new_state else '禁用'}"}

        # ==================== Web签到站点 ====================
        @app.get("/api/sites")
        async def list_sites():
            try:
                from app.core.database import Database
                db = Database()
                return {"sites": db.get_all_sites()}
            except Exception as e:
                raise HTTPException(503, f"数据库不可用: {e}")

        @app.post("/api/sites")
        async def create_site(site: SiteCreate):
            try:
                from app.core.database import Database
                db = Database()
                data = site.model_dump()
                data['_last_checkin'] = '-'
                site_id = db.save_site(data)
                return {"id": site_id, "message": f"站点「{data['name']}」已创建"}
            except Exception as e:
                raise HTTPException(500, f"创建失败: {e}")

        @app.put("/api/sites/{site_id}")
        async def update_site(site_id: int, updates: SiteUpdate):
            try:
                from app.core.database import Database
                db = Database()
                update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
                update_data['id'] = site_id
                db.save_site(update_data)
                return {"message": "站点已更新"}
            except Exception as e:
                raise HTTPException(500, f"更新失败: {e}")

        @app.delete("/api/sites/{site_id}")
        async def delete_site(site_id: int):
            try:
                from app.core.database import Database
                db = Database()
                db.delete_site(site_id)
                return {"message": "站点已删除"}
            except Exception as e:
                raise HTTPException(500, f"删除失败: {e}")

        @app.post("/api/sites/{site_id}/checkin")
        async def checkin_site(site_id: int):
            try:
                from app.core.database import Database
                db = Database()
                sites = db.get_all_sites()
                site = next((s for s in sites if s.get('id') == site_id), None)
                if not site:
                    raise HTTPException(404, "站点不存在")

                import asyncio
                from app.core.web_automation import WebAutomation

                async def do_checkin():
                    web = WebAutomation(headless=True)
                    if await web.start():
                        result = await web.execute_checkin(site)
                        await web.stop()
                        return result
                    return {'success': False, 'message': '浏览器启动失败'}

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(do_checkin())
                loop.close()

                return {"success": result.get('success', False), "message": result.get('message', '')}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(500, f"签到失败: {e}")

        # ==================== QQ 消息 ====================
        @app.post("/api/qq/send")
        async def send_qq_message(msg: MessageSend):
            try:
                from app.core.qq_automation import QQAutomation
                qq = QQAutomation()
                if not qq.is_qq_running:
                    raise HTTPException(400, "QQ客户端未运行")
                for group in msg.groups:
                    qq.send_group_message(group, msg.message)
                    import time
                    time.sleep(msg.delay)
                return {"message": f"消息已发送到 {len(msg.groups)} 个群"}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(500, f"发送失败: {e}")

        @app.get("/api/qq/status")
        async def qq_status():
            try:
                from app.core.qq_automation import QQAutomation
                qq = QQAutomation()
                return {"running": qq.is_qq_running}
            except Exception:
                return {"running": False, "error": "检测失败"}

        # ==================== 执行历史 ====================
        @app.get("/api/history")
        async def get_history(limit: int = 50, task_id: Optional[str] = None):
            sched = scheduler
            if not sched:
                raise HTTPException(503, "调度器不可用")
            return {"history": sched.get_history(limit=limit, task_id=task_id)}

        @app.delete("/api/history")
        async def clear_history():
            try:
                from app.core.database import Database
                db = Database()
                db.clear_history()
                return {"message": "历史已清空"}
            except Exception as e:
                raise HTTPException(500, f"清空失败: {e}")

        # ==================== Web管理页面 ====================
        @app.get("/", response_class=HTMLResponse)
        async def web_admin():
            return self._get_admin_html()

        @app.get("/api/config")
        async def get_config():
            try:
                from app.core.database import Database
                db = Database()
                return db.get_all_config()
            except Exception as e:
                raise HTTPException(503, f"配置不可用: {e}")

        @app.put("/api/config")
        async def update_config(config: dict = Body(...)):
            try:
                from app.core.database import Database
                db = Database()
                for key, value in config.items():
                    db.set_config(key, value)
                return {"message": "配置已更新"}
            except Exception as e:
                raise HTTPException(500, f"更新失败: {e}")

        return app

    def _get_admin_html(self) -> str:
        """返回 Web 管理页面 HTML"""
        try:
            from .admin_template import ADMIN_HTML
            return ADMIN_HTML
        except Exception:
            return "<html><body><h1>QQBotStation API</h1></body></html>"

    def start(self):
        """启动 API 服务器"""
        if self._running:
            return
        if not HAS_FASTAPI:
            print("[API] FastAPI未安装，启动简易HTTP服务器")
            self._start_simple()
            return

        self._app = self._create_app()
        self._running = True

        import uvicorn
        config = uvicorn.Config(self._app, host=self._host, port=self._port,
                                log_level="info")
        self._server = uvicorn.Server(config)

        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        print(f"[API] FastAPI服务器已启动: http://{self._host}:{self._port}")

    def _start_simple(self):
        """简易HTTP服务器（无FastAPI备选）"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        import urllib.parse

        scheduler = self._get_scheduler()

        class SimpleAPI(BaseHTTPRequestHandler):
            def _json(self, data, status=200):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

            def _html(self, html, status=200):
                self.send_response(status)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode())

            def do_OPTIONS(self):
                self._json({})

            def do_GET(self):
                path = urllib.parse.urlparse(self.path).path
                if path == '/':
                    self._html(self.server._get_admin_html())
                elif path == '/api/status':
                    st = scheduler.get_stats() if scheduler else {}
                    self._json({"status": "running", "version": "1.0.0",
                                "platform": sys.platform, "stats": st})
                elif path == '/api/tasks':
                    self._json({"tasks": scheduler.get_all_tasks() if scheduler else []})
                elif path.startswith('/api/tasks/'):
                    tid = path.split('/')[-1]
                    t = scheduler.get_task(tid) if scheduler else None
                    self._json(t or {"error": "not found"}, 404 if not t else 200)
                elif path == '/api/sites':
                    try:
                        from app.core.database import Database
                        self._json({"sites": Database().get_all_sites()})
                    except Exception as e:
                        self._json({"sites": [], "error": str(e)})
                elif path == '/api/history':
                    self._json({"history": scheduler.get_history() if scheduler else []})
                elif path == '/api/qq/status':
                    try:
                        from app.core.qq_automation import QQAutomation
                        self._json({"running": QQAutomation().is_qq_running})
                    except Exception:
                        self._json({"running": False})
                else:
                    self._json({"error": "not found"}, 404)

            def do_POST(self):
                path = urllib.parse.urlparse(self.path).path
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length)) if length else {}

                if path == '/api/qq/send':
                    try:
                        from app.core.qq_automation import QQAutomation
                        qq = QQAutomation()
                        for g in body.get('groups', []):
                            qq.send_group_message(g, body.get('message', ''))
                            import time; time.sleep(body.get('delay', 5))
                        self._json({"message": f"已发送到 {len(body.get('groups',[]))} 个群"})
                    except Exception as e:
                        self._json({"error": str(e)}, 500)
                else:
                    self._json({"error": "not found"}, 404)

        class ThreadedServer(HTTPServer):
            allow_reuse_address = True
            daemon_threads = True

        server = ThreadedServer((self._host, self._port), SimpleAPI)
        server._get_admin_html = self._get_admin_html
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        print(f"[API] 简易HTTP服务器已启动: http://{self._host}:{self._port}")
        self._running = True

    def stop(self):
        """停止 API 服务器"""
        self._running = False
        if self._server:
            self._server.should_exit = True
        print("[API] 服务器已停止")
