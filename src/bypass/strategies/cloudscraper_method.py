"""
Cloudscraper Method - Automatic Cloudflare Challenge Solver

Uses the cloudscraper library for lightweight bypass of JavaScript challenges
and automatic cookie/session management.
"""

import cloudscraper
import time
import random
from typing import Dict, Optional, Any
from loguru import logger


class CloudscraperMethod:
    """Cloudflare bypass using cloudscraper library"""
    
    def __init__(self, timeout: int = 30, delay_range: tuple = (1, 3)):
        """
        Initialize cloudscraper method
        
        Args:
            timeout: Request timeout in seconds
            delay_range: Random delay range between requests (min, max)
        """
        self.timeout = timeout
        self.delay_range = delay_range
        self.scraper = None
        self._initialize_scraper()
        
    def _initialize_scraper(self):
        """Initialize cloudscraper with optimal settings"""
        try:
            # Create cloudscraper session with browser impersonation
            self.scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                delay=random.uniform(*self.delay_range)
            )
            
            # Set realistic headers with static user agent
            chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
            self.scraper.headers.update({
                'User-Agent': chrome_ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            })
            
            logger.info("Cloudscraper initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cloudscraper: {e}")
            raise
    
    def get(self, url: str, **kwargs) -> Any:
        """
        Perform GET request with Cloudflare bypass
        
        Args:
            url: Target URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        return self._make_request("GET", url, **kwargs)
    
    def post(self, url: str, data=None, json=None, **kwargs) -> Any:
        """
        Perform POST request with Cloudflare bypass
        
        Args:
            url: Target URL
            data: Form data
            json: JSON data
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        return self._make_request("POST", url, data=data, json=json, **kwargs)
    
    def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Make HTTP request with cloudscraper
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            **kwargs: Request parameters
            
        Returns:
            Response object
        """
        try:
            # Add random delay to avoid rate limiting
            self._random_delay()
            
            # Rotate User-Agent occasionally
            if random.random() < 0.1:  # 10% chance
                self._rotate_user_agent()
            
            # Set default timeout
            kwargs.setdefault('timeout', self.timeout)
            
            logger.info(f"Making {method} request to {url}")
            
            # Make request with cloudscraper
            if method.upper() == "GET":
                response = self.scraper.get(url, **kwargs)
            elif method.upper() == "POST":
                response = self.scraper.post(url, **kwargs)
            else:
                response = self.scraper.request(method, url, **kwargs)
            
            logger.success(f"Request successful: {response.status_code}")
            return response
            
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            logger.error(f"Cloudflare challenge failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(*self.delay_range)
        logger.debug(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)
    
    def _rotate_user_agent(self):
        """Rotate User-Agent header"""
        try:
            # Static list of Chrome user agents
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", 
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            ]
            new_ua = random.choice(user_agents)
            self.scraper.headers['User-Agent'] = new_ua
            logger.debug(f"Rotated User-Agent: {new_ua[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to rotate User-Agent: {e}")
    
    def get_cookies(self) -> Dict:
        """Get current session cookies"""
        return dict(self.scraper.cookies)
    
    def set_cookies(self, cookies: Dict):
        """Set session cookies"""
        for name, value in cookies.items():
            self.scraper.cookies[name] = value
    
    def get_cf_clearance(self) -> Optional[str]:
        """Get Cloudflare clearance cookie if available"""
        return self.scraper.cookies.get('cf_clearance')
    
    def has_valid_clearance(self) -> bool:
        """Check if we have a valid Cloudflare clearance cookie"""
        clearance = self.get_cf_clearance()
        return clearance is not None and len(clearance) > 10
    
    def reset_session(self):
        """Reset the scraper session"""
        logger.info("Resetting cloudscraper session")
        self._initialize_scraper()
    
    def test_bypass(self, test_url: str) -> bool:
        """
        Test if cloudscraper can bypass Cloudflare for a given URL
        
        Args:
            test_url: URL to test bypass against
            
        Returns:
            True if bypass successful, False otherwise
        """
        try:
            response = self.get(test_url)
            
            # Check if we got a successful response
            if response.status_code == 200:
                # Check if response contains Cloudflare challenge
                content = response.text.lower()
                cf_indicators = [
                    "checking your browser",
                    "cloudflare",
                    "cf-browser-verification",
                    "challenge validation"
                ]
                
                has_challenge = any(indicator in content for indicator in cf_indicators)
                
                if not has_challenge:
                    logger.success("Cloudscraper bypass test successful")
                    return True
                else:
                    logger.warning("Cloudscraper bypass incomplete - challenge still present")
                    return False
            else:
                logger.warning(f"Bypass test failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Bypass test failed: {e}")
            return False
    
    def get_session_info(self) -> Dict:
        """Get information about current session"""
        return {
            "cookies": len(self.scraper.cookies),
            "cf_clearance": self.has_valid_clearance(),
            "user_agent": self.scraper.headers.get('User-Agent', '')[:50] + '...',
            "timeout": self.timeout,
            "delay_range": self.delay_range
        }