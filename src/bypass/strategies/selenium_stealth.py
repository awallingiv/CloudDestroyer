"""
Selenium Stealth Method - Advanced Browser Automation Bypass

Uses undetected-chromedriver with stealth techniques to bypass sophisticated
Cloudflare protection including CAPTCHAs and Bot Fight Mode.
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import random
import json
from typing import Dict, Optional, Any
from loguru import logger


class SeleniumStealth:
    """Advanced Selenium-based Cloudflare bypass with stealth capabilities"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize Selenium stealth method
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for operations
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup undetected Chrome driver with stealth options"""
        try:
            # Chrome options for stealth
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless=new')
            
            # Stealth arguments
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-first-run')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-notifications')
            
            # Realistic window size
            options.add_argument('--window-size=1920,1080')
            
            # User agent rotation
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            ]
            options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            # Prefs to avoid detection
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                }
            }
            options.add_experimental_option("prefs", prefs)
            
            # Create undetected Chrome driver
            self.driver = uc.Chrome(options=options, version_main=None)
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            # Execute stealth scripts
            self._execute_stealth_scripts()
            
            logger.success("Selenium stealth driver initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup Selenium driver: {e}")
            raise
    
    def _execute_stealth_scripts(self):
        """Execute JavaScript to enhance stealth capabilities"""
        stealth_scripts = [
            # Hide webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Spoof plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: 'Portable Document Format'
                }))
            })
            """,
            
            # Spoof languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
            
            # Permission API
            """
            const originalQuery = window.navigator.permissions.query;
            return navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            """,
            
            # Hide automation indicators
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array",
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise", 
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol"
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.debug(f"Stealth script execution failed: {e}")
    
    def get(self, url: str, wait_for_load: bool = True) -> Dict[str, Any]:
        """
        Navigate to URL and bypass Cloudflare protection
        
        Args:
            url: Target URL
            wait_for_load: Wait for page to fully load
            
        Returns:
            Dict with response data
        """
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate to URL
            self.driver.get(url)
            
            # Wait for initial load
            if wait_for_load:
                self._wait_for_page_load()
            
            # Check for and handle Cloudflare challenges
            challenge_handled = self._handle_cloudflare_challenge()
            
            # Get page source and info
            response_data = {
                "url": self.driver.current_url,
                "status_code": self._get_response_status(),
                "text": self.driver.page_source,
                "title": self.driver.title,
                "cookies": self._get_cookies(),
                "challenge_handled": challenge_handled
            }
            
            logger.success(f"Page loaded successfully: {response_data['title']}")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to get URL: {e}")
            raise
    
    def _wait_for_page_load(self, timeout: Optional[int] = None):
        """Wait for page to finish loading"""
        timeout = timeout or self.timeout
        
        try:
            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Additional wait for any async content
            time.sleep(random.uniform(2, 4))
            
        except TimeoutException:
            logger.warning("Page load timeout reached")
    
    def _handle_cloudflare_challenge(self) -> bool:
        """
        Detect and handle Cloudflare challenges
        
        Returns:
            True if challenge was detected and handled
        """
        try:
            # Check for various Cloudflare challenge indicators
            cf_indicators = [
                "//div[contains(@class, 'cf-browser-verification')]",
                "//div[contains(text(), 'Checking your browser')]",
                "//div[contains(text(), 'Please wait')]",
                "//*[@id='challenge-form']",
                "//div[contains(@class, 'cf-captcha')]"
            ]
            
            challenge_detected = False
            
            for xpath in cf_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    if element.is_displayed():
                        challenge_detected = True
                        logger.info("Cloudflare challenge detected")
                        break
                except:
                    continue
            
            if challenge_detected:
                return self._wait_for_challenge_completion()
            
            return False
            
        except Exception as e:
            logger.warning(f"Challenge detection failed: {e}")
            return False
    
    def _wait_for_challenge_completion(self, max_wait: int = 60) -> bool:
        """
        Wait for Cloudflare challenge to complete
        
        Args:
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if challenge completed successfully
        """
        logger.info("Waiting for Cloudflare challenge to complete...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check if we're still on a challenge page
                current_url = self.driver.current_url
                page_source = self.driver.page_source.lower()
                
                # Challenge completion indicators
                if not any(indicator in page_source for indicator in [
                    "checking your browser",
                    "cf-browser-verification",
                    "challenge validation",
                    "please wait"
                ]):
                    logger.success("Cloudflare challenge completed")
                    return True
                
                # Wait a bit before checking again
                time.sleep(2)
                
            except Exception as e:
                logger.debug(f"Challenge check failed: {e}")
                time.sleep(1)
        
        logger.warning("Challenge completion timeout")
        return False
    
    def _get_response_status(self) -> int:
        """Get HTTP response status code"""
        try:
            # Try to get status from performance logs
            logs = self.driver.get_log('performance')
            for log in logs:
                message = json.loads(log['message'])
                if message.get('method') == 'Network.responseReceived':
                    response = message.get('params', {}).get('response', {})
                    if response.get('url') == self.driver.current_url:
                        return response.get('status', 200)
        except:
            pass
        
        return 200  # Default to 200 if unable to determine
    
    def _get_cookies(self) -> Dict:
        """Get all cookies from current session"""
        try:
            cookies = {}
            for cookie in self.driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            return cookies
        except Exception as e:
            logger.debug(f"Failed to get cookies: {e}")
            return {}
    
    def get_cf_clearance(self) -> Optional[str]:
        """Get Cloudflare clearance cookie"""
        cookies = self._get_cookies()
        return cookies.get('cf_clearance')
    
    def screenshot(self, filename: str = None) -> str:
        """Take screenshot of current page"""
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        
        try:
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            raise
    
    def execute_script(self, script: str) -> Any:
        """Execute JavaScript in browser"""
        try:
            return self.driver.execute_script(script)
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            raise
    
    def close(self):
        """Close browser and cleanup"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Selenium driver closed")
        except Exception as e:
            logger.warning(f"Driver cleanup failed: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()