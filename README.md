# QQBotStation · 全能自动化工作站

🤖 功能强大的桌面自动化工具，支持 **定时QQ群消息发送**、**网站签到与积分领取**、**OCR屏幕识别** 和 **窗口扫描**。

三种部署方式：**Windows桌面** / **Linux服务** / **Docker容器**

UI 风格参考 [WechatOnCloud](https://github.com/Gloridust/WechatOnCloud) 项目——左侧导航栏 + 右侧内容区，暗色现代主题。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 💬 **定时QQ群发** | 指定时间向多个QQ群发送消息，支持多任务调度 |
| 🌐 **网站签到** | 自动登录网站执行签到、积分领取（基于Playwright） |
| 📷 **OCR识别** | 屏幕文字识别，支持中英文，可定位文本坐标 |
| 🪟 **窗口扫描** | 扫描系统窗口、按钮、输入框等UI元素 |
| 🖱️ **人机模拟** | 贝塞尔曲线鼠标移动、随机延迟、拟人化操作 |
| 📋 **日志系统** | 实时日志、分级过滤、自动滚屏 |
| 🌐 **Web管理** | 守护进程模式自带REST API + 管理面板 |

---

## 📦 依赖库

### 必需（运行必需）

| 包 | 版本 | 用途 |
|---|------|------|
| PySide6 | >=6.5.0 | Qt GUI框架 |
| playwright | >=1.40.0 | 浏览器自动化引擎（签到用） |
| pyautogui | >=0.9.54 | 鼠标键盘模拟（QQ操作用） |
| pywin32 | >=305 (仅Windows) | Windows API (窗口/截图) |
| keyboard | >=0.13.5 | 键盘事件 |
| APScheduler | >=3.10.0 | 定时任务调度 |
| Pillow | >=10.0.0 | 图像处理 |
| numpy | >=1.24.0 | 数值计算 |
| opencv-python-headless | >=4.8.0 | 计算机视觉 |
| psutil | >=5.9.0 | 系统资源监控 |
| requests | >=2.31.0 | HTTP请求 |

### 可选

| 包 | 用途 |
|---|------|
| fastapi + uvicorn + pydantic | Web管理API服务器 |
| paddlepaddle + paddleocr | OCR文字识别（推荐） |
| pytesseract | OCR轻量备选 |
| pyinstaller | 打包为exe |

### 安装命令

```bash
# 最小安装（无OCR、无Web管理）
pip install PySide6 playwright pyautogui pywin32 keyboard APScheduler Pillow numpy opencv-python-headless psutil requests
playwright install chromium

# 完整安装
pip install -r requirements.txt
playwright install chromium

# 安装OCR
pip install paddlepaddle paddleocr
```

### Go Daemon（高性能守护进程）

```bash
cd daemon
go build -o qqbot-daemon .
./qqbot-daemon --port 8580 --db ../data/qqbot.db

# 跨平台编译
GOOS=linux GOARCH=amd64 go build -o qqbot-daemon .
GOOS=windows GOARCH=amd64 go build -o qqbot-daemon.exe .
```

---

## 🗄️ 数据库 (SQLite)

### 数据表结构

```
tasks                  history                  sites
├── id (PK)            ├── id (PK AUTO)         ├── id (PK AUTO)
├── name               ├── task_id (FK→tasks)   ├── name (UNIQUE)
├── type (qq/web/ocr)  ├── task_name            ├── url
├── enabled            ├── task_type            ├── checkin_selector
├── config (JSON)      ├── status               ├── success_indicator
├── schedule (JSON)    ├── message              ├── need_login
├── next_run           ├── time (INDEX)         ├── username_selector
├── last_run                                    ├── password_selector
├── last_status        config                   ├── username
├── created_at         ├── key (PK)             ├── password
└── updated_at         └── value                ├── login_selector
                                                ├── steps (JSON)
                                                ├── wait_after
                                                ├── last_checkin
                                                ├── created_at
                                                └── updated_at
```

### 存储位置

`data/qqbot.db` — SQLite 数据库（主存储）
`data/tasks.json` — JSON 备份（兼容旧版）
`data/history.json` — 历史记录备份

### 线程安全

每线程独立连接（`threading.local`），WAL 模式，支持并发读写。

---

## ⚙️ 运行库架构

```
main.py (入口)
  ├── GUI模式 → app/ui/main_window.py (PySide6桌面)
  │   ├── QQ面板     → app/core/qq_automation.py    → QQ桌面客户端
  │   ├── 网页签到    → app/core/web_automation.py   → Playwright浏览器
  │   ├── OCR识别    → app/core/ocr_engine.py        → PaddleOCR
  │   ├── 窗口扫描   → app/core/screen_scanner.py    → win32gui
  │   ├── 日志       → app/utils/logger.py           → 文件+控制台
  │   └── 设置       → app/utils/config_manager.py   → SQLite+JSON
  │
  ├── CLI/守护进程 → app/api/server.py (FastAPI/简易HTTP)
  │   ├── GET  /api/status     系统状态
  │   ├── GET  /api/tasks      任务列表
  │   ├── POST /api/tasks      创建任务
  │   ├── GET  /api/sites      站点列表
  │   ├── POST /api/qq/send    发送QQ消息
  │   ├── GET  /api/history    执行历史
  │   └── GET  /               管理面板HTML
  │
  └── 通用
      ├── app/core/scheduler.py       任务调度器 (SingletonMixin)
      ├── app/core/human_simulator.py 人机模拟 (贝塞尔曲线)
      ├── app/core/database.py        数据库 (SingletonMixin)
      ├── app/utils/singleton.py      单例混入基类
      └── app/utils/window_utils.py   窗口工具 (统一枚举入口)
```

### 单例模式

`Database`、`ConfigManager`、`TaskScheduler` 三个核心类继承 `SingletonMixin`（`app/utils/singleton.py`），确保全局唯一实例，线程安全初始化。

### 数据流

```
用户操作GUI → 页面面板 → TaskScheduler.add_task()
  → Database.save_task() (SQLite写入)
  → _calc_next_run() + APScheduler注册
  → 定时触发 _execute_task()
  → 调用 QQAutomation / WebAutomation / OCREngine
  → Database.add_history() (执行记录)
  → 状态更新到UI
```

---

## 🚀 快速开始

### Windows 桌面版

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

### Linux 服务版

```bash
chmod +x scripts/install_deps.sh && ./scripts/install_deps.sh
source venv/bin/activate
python main.py --daemon --port 8580
```

### Docker

```bash
docker compose up -d
```

### CLI 命令

```bash
# 守护进程（带Web管理面板）
python main.py --daemon --port 8580

# 发送QQ消息
python main.py --qq-message "你好" --qq-groups "工作群" "项目群"

# 执行网站签到
python main.py --web-checkin checkin_config.json

# OCR扫描屏幕
python main.py --ocr-scan

# 执行任务文件
python main.py --task tasks.json
```

---

## 📁 项目结构

```
QQBotStation/
├── main.py                     # 主入口
├── requirements.txt            # 依赖清单
├── Dockerfile                  # Docker构建
├── docker-compose.yml          # Docker编排
├── build.bat                   # Windows打包
├── config/default_config.json  # 默认配置
├── app/
│   ├── core/                   # 核心引擎
│   │   ├── scheduler.py        # 任务调度器
│   │   ├── database.py         # SQLite数据库
│   │   ├── human_simulator.py  # 人机模拟
│   │   ├── ocr_engine.py       # OCR引擎
│   │   ├── qq_automation.py    # QQ自动化
│   │   ├── web_automation.py   # 网页自动化
│   │   └── screen_scanner.py   # 屏幕扫描
│   ├── ui/                     # 用户界面
│   │   ├── main_window.py      # 主窗口
│   │   ├── title_bar.py        # 标题栏
│   │   ├── sidebar.py          # 侧边栏
│   │   └── pages/              # 功能页面
│   ├── api/                    # REST API
│   │   ├── server.py           # API服务器
│   │   └── admin_template.py   # 管理面板HTML
│   ├── models/task.py          # 数据模型
│   └── utils/                  # 工具
│       ├── singleton.py        # 单例混入基类
│       ├── logger.py           # 日志系统
│       ├── config_manager.py   # 配置管理
│       └── window_utils.py     # 窗口工具
├── resources/styles/main.qss   # 主题样式表
├── data/                       # 运行时数据
│   ├── qqbot.db                # SQLite数据库
│   ├── tasks.json              # 任务备份
│   └── history.json            # 历史备份
└── scripts/                    # 安装脚本
```

---

## 🛠️ 技术方案

| 技术 | 用途 |
|------|------|
| **PySide6** | 桌面GUI框架，暗色主题，无边框窗口 |
| **Playwright** | 浏览器自动化，支持人类化操作 |
| **PaddleOCR** | 中英文OCR文字识别 |
| **pyautogui + pywin32** | 鼠标/键盘/窗口模拟 |
| **APScheduler** | 定时任务调度 |
| **SQLite (WAL模式)** | 数据持久化 |
| **FastAPI / http.server** | REST API |

### 人机模拟特性

- 🖱️ **贝塞尔曲线** - 鼠标移动轨迹模拟真实人手
- ⏱️ **随机延迟** - 操作间隔符合人类分布
- 🎯 **偏移点击** - 点击位置有微小的随机偏移
- ⌨️ **拟人打字** - 逐字输入，偶尔停顿模拟思考
- 📜 **分段滚动** - 滚动操作分段执行

---

## 📝 许可证

MIT License

## 🙏 致谢

- UI设计参考 [WechatOnCloud](https://github.com/Gloridust/WechatOnCloud)
- OCR引擎 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- 浏览器自动化 [Playwright](https://playwright.dev/)
