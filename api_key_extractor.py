"""
API Key Extractor - Extracts API keys from websites using Chrome DevTools Protocol
Supports Azure API Management and other common API authentication patterns
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time
from typing import Optional, Dict, List
from loguru import logger


class APIKeyExtractor:
    """
    Extract API keys from websites by monitoring network traffic
    """

    # Common API key header patterns
    API_KEY_HEADERS = [
        'ocp-apim-subscription-key',  # Azure API Management
        'x-api-key',                   # Generic API key
        'api-key',                     # Generic
        'apikey',                      # Generic
        'authorization',               # Bearer tokens
        'x-auth-token',                # Auth token
        'x-subscription-key',          # Subscription key
    ]

    # Common API endpoint patterns
    API_ENDPOINT_PATTERNS = [
        'api',
        'graphql',
        'menu',
        'restaurant',
        'location',
        'order',
        'catalog',
        'product'
    ]

    def __init__(self):
        self.driver = None
        self.api_keys_found = {}
        self.api_endpoints_found = []

    def setup_chrome(self) -> webdriver.Chrome:
        """
        Setup Chrome with performance logging enabled
        """
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')

        # Enable performance logging to capture network requests
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        driver = webdriver.Chrome(options=options)
        return driver

    def extract_from_url(
        self,
        url: str,
        wait_time: int = 10,
        click_selectors: List[str] = None
    ) -> Dict[str, any]:
        """
        Extract API keys and endpoints from a URL

        Args:
            url: URL to load
            wait_time: Time to wait for API calls (seconds)
            click_selectors: Optional list of CSS selectors to click to trigger API calls

        Returns:
            Dict with 'api_keys', 'endpoints', and 'headers'
        """
        logger.info(f"Extracting API keys from: {url}")

        self.driver = self.setup_chrome()

        try:
            # Load the page
            logger.info("Loading page...")
            self.driver.get(url)

            # Optional: Click elements to trigger API calls
            if click_selectors:
                for selector in click_selectors:
                    try:
                        element = self.driver.find_element('css selector', selector)
                        element.click()
                        time.sleep(2)
                        logger.info(f"Clicked: {selector}")
                    except:
                        pass

            # Wait for API calls
            logger.info(f"Waiting {wait_time}s for API calls...")
            time.sleep(wait_time)

            # Analyze network logs
            logger.info("Analyzing network logs...")
            logs = self.driver.get_log('performance')

            self._analyze_logs(logs)

            result = {
                'api_keys': self.api_keys_found,
                'endpoints': self.api_endpoints_found,
                'success': len(self.api_keys_found) > 0 or len(self.api_endpoints_found) > 0
            }

            logger.info(f"Found {len(self.api_keys_found)} API key types")
            logger.info(f"Found {len(self.api_endpoints_found)} API endpoints")

            return result

        finally:
            if self.driver:
                self.driver.quit()

    def _analyze_logs(self, logs: List[Dict]) -> None:
        """
        Analyze Chrome performance logs to extract API keys and endpoints
        """
        for log in logs:
            try:
                log_message = json.loads(log['message'])
                message = log_message.get('message', {})

                # Look for Network.requestWillBeSentExtraInfo (has full headers)
                if message.get('method') == 'Network.requestWillBeSentExtraInfo':
                    self._extract_from_extra_info(message)

                # Look for Network.requestWillBeSent (has URL and request headers)
                elif message.get('method') == 'Network.requestWillBeSent':
                    self._extract_from_request(message)

            except Exception as e:
                continue

    def _extract_from_extra_info(self, message: Dict) -> None:
        """
        Extract API keys from Network.requestWillBeSentExtraInfo events
        These events have the full headers including API keys
        """
        headers = message.get('params', {}).get('headers', {})

        for header_name, header_value in headers.items():
            header_lower = header_name.lower()

            # Check if this is an API key header
            if any(pattern in header_lower for pattern in self.API_KEY_HEADERS):
                if header_lower not in self.api_keys_found:
                    self.api_keys_found[header_lower] = header_value
                    logger.success(f"Found API key: {header_name} = {header_value[:8]}...{header_value[-8:]}")

    def _extract_from_request(self, message: Dict) -> None:
        """
        Extract API endpoints from Network.requestWillBeSent events
        """
        request = message.get('params', {}).get('request', {})
        url = request.get('url', '')
        method = request.get('method', 'GET')

        # Check if URL looks like an API endpoint
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in self.API_ENDPOINT_PATTERNS):
            # Avoid duplicates
            if url not in [ep['url'] for ep in self.api_endpoints_found]:
                endpoint_info = {
                    'url': url,
                    'method': method,
                    'headers': request.get('headers', {})
                }
                self.api_endpoints_found.append(endpoint_info)
                logger.info(f"Found API endpoint: {method} {url[:100]}")

                # Also check request headers for API keys
                req_headers = request.get('headers', {})
                for h_name, h_value in req_headers.items():
                    h_lower = h_name.lower()
                    if any(pattern in h_lower for pattern in self.API_KEY_HEADERS):
                        if h_lower not in self.api_keys_found:
                            self.api_keys_found[h_lower] = h_value
                            logger.success(f"Found API key in request: {h_name} = {h_value[:8]}...{h_value[-8:]}")


def extract_api_keys(url: str, wait_time: int = 10) -> Dict[str, any]:
    """
    Convenience function to extract API keys from a URL

    Args:
        url: URL to extract from
        wait_time: Time to wait for API calls

    Returns:
        Dict with api_keys and endpoints
    """
    extractor = APIKeyExtractor()
    return extractor.extract_from_url(url, wait_time=wait_time)


if __name__ == "__main__":
    # Test with Chipotle
    result = extract_api_keys("https://www.chipotle.com/order", wait_time=10)

    print("\n" + "=" * 80)
    print("API KEYS FOUND:")
    print("=" * 80)
    for header, key in result['api_keys'].items():
        print(f"  {header}: {key}")

    print("\n" + "=" * 80)
    print("API ENDPOINTS FOUND:")
    print("=" * 80)
    for endpoint in result['endpoints'][:10]:
        print(f"  {endpoint['method']} {endpoint['url'][:100]}")
