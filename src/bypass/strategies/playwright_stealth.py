"""
Playwright Stealth Strategy

Provides a headless Chromium browser with stealth tweaks using Playwright.
"""

import random
import time
from typing import Dict, Any
from loguru import logger

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None
    PlaywrightTimeoutError = Exception  # Fallback to generic exception
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightStealth:
    """Lightweight Playwright-based Cloudflare bypass helper"""

    def __init__(self, headless: bool = True, timeout: int = 45):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("playwright is not installed. Run 'pip install playwright'.")
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._launch()

    def _launch(self):
        self.playwright = sync_playwright().start()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-gpu",
        ]
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )
        self.context = self.browser.new_context(
            user_agent=self._random_user_agent(),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            locale="en-US",
        )
        self.page = self.context.new_page()
        self._apply_stealth()
        logger.success("Playwright stealth browser initialized")

    def _apply_stealth(self):
        """Apply simple JS tweaks to resemble real browsers."""
        scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            "window.chrome = { runtime: {} };",
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});",
            "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});",
        ]
        for script in scripts:
            try:
                self.page.add_init_script(script)
            except Exception as exc:
                logger.debug(f"Playwright stealth script failed: {exc}")

    def _random_user_agent(self) -> str:
        uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36",
        ]
        return random.choice(uas)

    def get(self, url: str, wait_for_load: bool = True) -> Dict[str, Any]:
        if not self.page:
            raise RuntimeError("Playwright browser not initialized")
        logger.info(f"Playwright navigating to {url}")
        try:
            response = self.page.goto(
                url,
                wait_until="networkidle" if wait_for_load else "domcontentloaded",
                timeout=self.timeout * 1000,
            )
            time.sleep(random.uniform(1, 3))
            content = self.page.content()
            cookies = {cookie["name"]: cookie["value"] for cookie in self.context.cookies()}
            status_code = response.status if response else 200
            return {
                "url": self.page.url,
                "status_code": status_code,
                "text": content,
                "title": self.page.title(),
                "cookies": cookies,
            }
        except PlaywrightTimeoutError as exc:
            logger.warning(f"Playwright navigation timeout: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Playwright navigation failed: {exc}")
            raise

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Playwright resources released")
        except Exception as exc:
            logger.warning(f"Playwright cleanup issue: {exc}")
        finally:
            self.context = None
            self.browser = None
            self.playwright = None
            self.page = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
