"""
数据模型 - 任务、配置等数据结构
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class TaskSchedule:
    """调度计划"""
    type: str = 'cron'          # 'cron', 'interval', 'daily', 'once'
    cron_expression: str = '0 9 * * *'  # cron表达式
    interval_minutes: int = 60  # 间隔分钟
    time: str = '09:00'         # 每日执行时间
    start_date: str = None      # 开始日期
    end_date: str = None        # 结束日期


@dataclass
class QQTask:
    """QQ消息任务"""
    id: str = ''
    name: str = ''
    type: str = 'qq'
    enabled: bool = True
    schedule: Dict = field(default_factory=lambda: asdict(TaskSchedule()))
    groups: List[str] = field(default_factory=list)   # 目标群列表
    message: str = ''                                  # 发送内容
    send_mode: str = 'text'                            # 'text', 'image'
    image_path: str = ''
    _last_run: str = ''
    _last_status: str = ''
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WebTask:
    """网页签到任务"""
    id: str = ''
    name: str = ''
    type: str = 'web'
    enabled: bool = True
    schedule: Dict = field(default_factory=lambda: asdict(TaskSchedule()))
    headless: bool = False
    sites: List[Dict] = field(default_factory=list)   # 站点配置列表
    _last_run: str = ''
    _last_status: str = ''
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OCRScanTask:
    """OCR扫描任务"""
    id: str = ''
    name: str = ''
    type: str = 'ocr_scan'
    enabled: bool = True
    schedule: Dict = field(default_factory=lambda: asdict(TaskSchedule()))
    target_text: str = ''
    region: List[int] = field(default_factory=list)   # [left, top, width, height]
    action_on_find: str = 'log'                        # 'log', 'click', 'screenshot'
    _last_run: str = ''
    _last_status: str = ''
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SiteConfig:
    """网站配置"""
    name: str = ''
    url: str = ''
    login_selector: str = ''
    checkin_selector: str = ''
    username_selector: str = ''
    password_selector: str = ''
    username: str = ''
    password: str = ''
    success_indicator: str = '签到成功'
    steps: List[Dict] = field(default_factory=list)


def task_from_dict(data: dict) -> Any:
    """从字典创建对应的任务对象"""
    ttype = data.get('type', 'qq')
    if ttype == 'qq':
        return QQTask(**{k: v for k, v in data.items() if k in QQTask.__dataclass_fields__})
    elif ttype == 'web':
        return WebTask(**{k: v for k, v in data.items() if k in WebTask.__dataclass_fields__})
    elif ttype == 'ocr_scan':
        return OCRScanTask(**{k: v for k, v in data.items() if k in OCRScanTask.__dataclass_fields__})
    return data
