"""
CloudDestroyer - Main Cloudflare Bypass Scraper Interface

Provides a simple, unified API for bypassing Cloudflare protection
and scraping protected content with intelligent strategy selection.
"""

import time
import urllib.parse
from typing import Dict, Optional, Any, Union
from loguru import logger

from ..bypass.bypass_orchestrator import BypassOrchestrator
from ..bypass.session_manager import SessionManager
from ..stealth.fingerprint_manager import FingerprintManager


class CloudDestroyer:
    """
    Main Cloudflare bypass scraper with unified API
    
    Features:
    - Automatic challenge detection and bypass
    - Multi-strategy approach with intelligent fallbacks
    - Session and cookie persistence
    - Browser fingerprint spoofing
    - Success rate tracking and optimization
    """
    
    def __init__(
        self,
        headless: bool = True,
        session_persistence: bool = True,
        max_retries: int = 3,
        timeout: int = 60,
        delay_range: tuple = (1, 3)
    ):
        """
        Initialize CloudDestroyer scraper
        
        Args:
            headless: Run browsers in headless mode
            session_persistence: Enable session/cookie persistence
            max_retries: Maximum retry attempts per URL
            timeout: Request timeout in seconds
            delay_range: Random delay range between requests (min, max)
        """
        self.headless = headless
        self.session_persistence = session_persistence
        self.max_retries = max_retries
        self.timeout = timeout
        self.delay_range = delay_range
        
        # Initialize components
        self.orchestrator = BypassOrchestrator(
            max_retries=max_retries,
            strategy_timeout=timeout
        )
        
        if session_persistence:
            self.session_manager = SessionManager()
        else:
            self.session_manager = None
            
        self.fingerprint_manager = FingerprintManager()
        
        logger.success("CloudDestroyer initialized successfully")
    
    def get(self, url: str, **kwargs) -> Any:
        """
        Perform GET request with Cloudflare bypass
        
        Args:
            url: Target URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object with bypassed content
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
            Response object with bypassed content
        """
        return self._make_request("POST", url, data=data, json=json, **kwargs)
    
    def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Make HTTP request with intelligent Cloudflare bypass
        
        Args:
            method: HTTP method
            url: Target URL
            **kwargs: Request parameters
            
        Returns:
            Response object
        """
        domain = self._extract_domain(url)
        logger.info(f"Making {method} request to {domain}")
        
        # Check for existing valid session
        if self.session_persistence and self.session_manager:
            existing_session = self.session_manager.get_session(domain)
            if existing_session:
                logger.info("Using existing session for bypass")
                response = self._try_with_existing_session(
                    method, url, existing_session, **kwargs
                )
                if response:
                    return response
        
        # No valid session or session failed, perform full bypass
        logger.info("Performing full Cloudflare bypass")
        response, metadata = self.orchestrator.bypass_cloudflare(url, **kwargs)
        
        # Save successful session if persistence enabled
        if (self.session_persistence and self.session_manager and 
            metadata.get('success') and hasattr(response, 'cookies')):
            self._save_successful_session(domain, response, metadata)
        
        return response
    
    def _try_with_existing_session(
        self, 
        method: str, 
        url: str, 
        session_data, 
        **kwargs
    ) -> Optional[Any]:
        """
        Try request with existing session data
        
        Args:
            method: HTTP method
            url: Target URL
            session_data: Existing session data
            **kwargs: Request parameters
            
        Returns:
            Response if successful, None if failed
        """
        try:
            import requests
            
            # Use session cookies and headers
            kwargs.setdefault('cookies', {}).update(session_data.cookies)
            kwargs.setdefault('headers', {}).update(session_data.headers)
            kwargs.setdefault('timeout', self.timeout)
            
            # Make request
            if method.upper() == "GET":
                response = requests.get(url, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, **kwargs)
            else:
                response = requests.request(method, url, **kwargs)
            
            # Verify bypass success
            if self._is_bypass_successful(response):
                logger.success("Existing session bypass successful")
                
                # Update session success
                if self.session_manager:
                    domain = self._extract_domain(url)
                    self.session_manager.update_session(domain, success=True)
                
                return response
            else:
                logger.warning("Existing session bypass failed")
                
                # Update session failure
                if self.session_manager:
                    domain = self._extract_domain(url)
                    self.session_manager.update_session(domain, success=False)
                
                return None
                
        except Exception as e:
            logger.debug(f"Session request failed: {e}")
            return None
    
    def _save_successful_session(self, domain: str, response: Any, metadata: Dict):
        """Save successful bypass session"""
        try:
            # Extract cookies and headers
            cookies = {}
            headers = {}
            
            if hasattr(response, 'cookies'):
                cookies = dict(response.cookies)
            elif isinstance(response, dict) and 'cookies' in response:
                cookies = response['cookies']
            
            if hasattr(response, 'request') and hasattr(response.request, 'headers'):
                headers = dict(response.request.headers)
            elif metadata.get('fingerprint_seed'):
                # Use fingerprint headers
                fingerprint = self.fingerprint_manager.current_fingerprint
                if fingerprint:
                    headers = self.fingerprint_manager.get_headers_for_fingerprint(fingerprint)
            
            if cookies:
                self.session_manager.create_session(
                    domain=domain,
                    cookies=cookies,
                    headers=headers,
                    fingerprint=metadata.get('fingerprint', {})
                )
                logger.success(f"Session saved for {domain}")
            
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")
    
    def _is_bypass_successful(self, response: Any) -> bool:
        """Check if bypass was successful"""
        try:
            # Check status code
            status_code = getattr(response, 'status_code', 200)
            if status_code not in [200, 201, 202]:
                return False
            
            # Check content for challenge indicators
            content = getattr(response, 'text', '')
            if not content:
                return False
            
            challenge_indicators = [
                'checking your browser',
                'cloudflare',
                'cf-browser-verification',
                'challenge validation',
                'please wait'
            ]
            
            content_lower = content.lower()
            has_challenge = any(indicator in content_lower for indicator in challenge_indicators)
            
            return not has_challenge
            
        except Exception:
            return False
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc or url
    
    def get_session_info(self, domain: Optional[str] = None) -> Dict:
        """
        Get session information
        
        Args:
            domain: Specific domain (optional)
            
        Returns:
            Session information dictionary
        """
        info = {
            "session_persistence": self.session_persistence,
            "orchestrator_stats": self.orchestrator.get_statistics()
        }
        
        if self.session_manager:
            if domain:
                session = self.session_manager.get_session(domain)
                info["domain_session"] = {
                    "exists": session is not None,
                    "cf_clearance": session.cf_clearance if session else None,
                    "success_count": session.success_count if session else 0,
                    "failure_count": session.failure_count if session else 0
                }
            else:
                info["session_stats"] = self.session_manager.get_session_stats()
        
        return info
    
    def clear_session(self, domain: Optional[str] = None):
        """
        Clear session data
        
        Args:
            domain: Specific domain to clear (clears all if None)
        """
        if not self.session_manager:
            logger.warning("Session persistence not enabled")
            return
        
        if domain:
            self.session_manager.delete_session(domain)
            logger.info(f"Session cleared for {domain}")
        else:
            self.session_manager.clear_all_sessions()
            logger.info("All sessions cleared")
    
    def test_bypass(self, url: str) -> Dict:
        """
        Test Cloudflare bypass capabilities for a URL
        
        Args:
            url: URL to test
            
        Returns:
            Test results dictionary
        """
        logger.info(f"Testing bypass capabilities for {url}")
        
        start_time = time.time()
        
        try:
            response = self.get(url)
            duration = time.time() - start_time
            
            success = self._is_bypass_successful(response)
            
            result = {
                "url": url,
                "success": success,
                "duration": round(duration, 2),
                "status_code": getattr(response, 'status_code', 0),
                "content_length": len(getattr(response, 'text', '')),
                "has_cf_clearance": 'cf_clearance' in dict(getattr(response, 'cookies', {})),
                "orchestrator_stats": self.orchestrator.get_statistics()
            }
            
            if success:
                logger.success(f"Bypass test successful in {duration:.2f}s")
            else:
                logger.warning(f"Bypass test failed after {duration:.2f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            result = {
                "url": url,
                "success": False,
                "duration": round(duration, 2),
                "error": str(e),
                "orchestrator_stats": self.orchestrator.get_statistics()
            }
            
            logger.error(f"Bypass test error: {e}")
            return result
    
    def batch_requests(self, urls: list, method: str = "GET", **kwargs) -> list:
        """
        Perform batch requests with bypass
        
        Args:
            urls: List of URLs to request
            method: HTTP method to use
            **kwargs: Additional request parameters
            
        Returns:
            List of response objects
        """
        logger.info(f"Starting batch requests for {len(urls)} URLs")
        
        results = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Processing URL {i}/{len(urls)}: {url}")
            
            try:
                if method.upper() == "GET":
                    response = self.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = self.post(url, **kwargs)
                else:
                    response = self._make_request(method, url, **kwargs)
                
                results.append(response)
                
                # Add delay between requests
                if i < len(urls):
                    delay = self.delay_range[0]
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Batch request failed for {url}: {e}")
                results.append(None)
        
        logger.success(f"Batch requests completed: {sum(1 for r in results if r is not None)}/{len(urls)} successful")
        return results
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.orchestrator:
                self.orchestrator.cleanup()
            
            logger.info("CloudDestroyer cleaned up successfully")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def __repr__(self):
        return f"CloudDestroyer(headless={self.headless}, session_persistence={self.session_persistence})"