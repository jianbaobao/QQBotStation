"""
Web自动化 - 使用Playwright实现网站签到和积分领取
"""
import os
import sys
import time
import random
import json
from typing import List, Dict, Optional, Callable
from pathlib import Path
from .human_simulator import HumanSimulator as HS


class WebAutomation:
    """网页自动化操作 - 基于Playwright"""

    def __init__(self, headless: bool = False, data_dir: str = None):
        self._browser = None
        self._context = None
        self._page = None
        self._headless = headless
        self._playwright = None
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "browser_data")
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self._data_dir = data_dir

    async def start(self):
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()

            # 使用有状态浏览器上下文（保持登录）
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                ]
            )

            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                storage_state=os.path.join(self._data_dir, "state.json")
                if os.path.exists(os.path.join(self._data_dir, "state.json"))
                else None,
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
            )

            self._page = await self._context.new_page()
            return True
        except ImportError:
            import logging; logger = logging.getLogger("Web"); logger.warning("Playwright未安装，请执行: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return False

    async def stop(self):
        """关闭浏览器"""
        try:
            if self._context:
                # 保存登录状态
                if os.path.exists(self._data_dir):
                    state = await self._context.storage_state()
                    with open(os.path.join(self._data_dir, "state.json"), 'w') as f:
                        json.dump(state, f)
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            import logging; logging.getLogger("Web").warning(f"关闭浏览器失败: {e}")

    async def navigate(self, url: str, wait_until: str = 'networkidle'):
        """导航到URL"""
        if not self._page:
            return False
        try:
            await self._page.goto(url, wait_until=wait_until, timeout=30000)
            await HS.random_wait_after_action('page_load')
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False

    async def human_click_selector(self, selector: str, timeout: float = 10):
        """人类化点击页面元素"""
        if not self._page:
            return False
        try:
            elem = await self._page.wait_for_selector(selector, timeout=timeout * 1000)
            if not elem:
                return False
            box = await elem.bounding_box()
            if box:
                # 模拟人类移动再点击
                x = box['x'] + box['width'] / 2
                y = box['y'] + box['height'] / 2
                # 先在页面执行鼠标移动（JS模拟，不会真的移动物理鼠标）
                await self._page.mouse.move(
                    x + random.uniform(-5, 5),
                    y + random.uniform(-5, 5)
                )
                await self._page.wait_for_timeout(random.randint(100, 400))
                await self._page.mouse.move(x, y)
                await self._page.wait_for_timeout(random.randint(50, 150))
                await self._page.mouse.click(x, y)
            else:
                await elem.click()
            await HS.random_wait_after_action('click')
            return True
        except Exception as e:
            logger.error(f"点击失败 {selector}: {e}")
            return False

    async def human_type_selector(self, selector: str, text: str):
        """人类化输入文本"""
        if not self._page:
            return False
        try:
            elem = await self._page.wait_for_selector(selector, timeout=5000)
            if not elem:
                return False
            await elem.click()
            await self._page.wait_for_timeout(random.randint(200, 500))
            # 清空已有内容
            await elem.fill('')
            await self._page.wait_for_timeout(random.randint(100, 300))
            # 模拟人类逐字输入
            for char in text:
                await self._page.keyboard.type(char, delay=random.randint(50, 150))
                if random.random() < 0.01:  # 1%概率停顿
                    await self._page.wait_for_timeout(random.randint(300, 800))
            await HS.random_wait_after_action('type')
            return True
        except Exception as e:
            logger.error(f"输入失败 {selector}: {e}")
            return False

    async def human_scroll_page(self, pixels: int = None):
        """模拟人类滚动页面"""
        if not self._page:
            return
        try:
            if pixels is None:
                pixels = random.randint(300, 800)
            # 分段滚动
            remaining = abs(pixels)
            while remaining > 0:
                chunk = min(remaining, random.randint(80, 200))
                await self._page.evaluate(f'window.scrollBy(0, {"-" if pixels < 0 else "+"}{chunk})')
                remaining -= chunk
                await self._page.wait_for_timeout(random.randint(50, 150))
        except Exception as e:
            logger.error(f"滚动失败: {e}")

    async def screenshot(self, path: str = None) -> Optional[str]:
        """截图当前页面"""
        if not self._page:
            return None
        if path is None:
            path = os.path.join(self._data_dir, f"screenshot_{int(time.time())}.png")
        try:
            await self._page.screenshot(path=path, full_page=False)
            return path
        except Exception:
            return None

    async def execute_checkin(self, config: dict) -> dict:
        """执行签到任务

        Args:
            config: {
                'name': '站点名称',
                'url': '签到页面URL',
                'login_selector': '登录按钮选择器',
                'checkin_selector': '签到按钮选择器',
                'username_selector': '用户名输入框',
                'password_selector': '密码输入框',
                'username': '用户名',
                'password': '密码',
                'success_indicator': '签到成功后的文本特征',
                'steps': [  # 可选的点击步骤链
                    {'selector': '...', 'wait': 1},
                ]
            }

        Returns:
            {'success': bool, 'message': str}
        """
        name = config.get('name', '未知站点')
        logger.info(f"开始签到: {name}")
        try:
            await self.navigate(config['url'])

            # 执行前置步骤
            steps = config.get('steps', [])
            for step in steps:
                sel = step.get('selector')
                if sel:
                    await self.human_click_selector(sel)
                wait = step.get('wait', 1)
                await self._page.wait_for_timeout(int(wait * 1000))

            # 登录（如果需要）
            if config.get('username_selector') and config.get('username'):
                await self.human_type_selector(config['username_selector'], config['username'])
            if config.get('password_selector') and config.get('password'):
                await self.human_type_selector(config['password_selector'], config['password'])
            if config.get('login_selector'):
                await self.human_click_selector(config['login_selector'])
                await self._page.wait_for_timeout(3000)

            # 点击签到按钮
            if config.get('checkin_selector'):
                await self.human_click_selector(config['checkin_selector'])
                await self._page.wait_for_timeout(2000)

            # 验证结果
            if config.get('success_indicator'):
                content = await self._page.content()
                if config['success_indicator'] in content:
                    return {'success': True, 'message': f'{name} 签到成功'}
                else:
                    return {'success': False, 'message': f'{name} 可能未签到成功（未找到特征文本）'}

            return {'success': True, 'message': f'{name} 签到操作已完成'}

        except Exception as e:
            return {'success': False, 'message': f'{name} 签到失败: {str(e)}'}
