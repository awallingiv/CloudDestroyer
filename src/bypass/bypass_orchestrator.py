"""
Bypass Orchestrator - Intelligent Strategy Coordination

Coordinates multiple bypass strategies with intelligent fallback logic,
retry mechanisms, and success rate tracking to defeat Cloudflare protection.
"""

import time
import random
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .detectors.challenge_detector import ChallengeDetector, ChallengeType
from .strategies.cloudscraper_method import CloudscraperMethod
from .strategies.selenium_stealth import SeleniumStealth
from .strategies.playwright_stealth import PlaywrightStealth, PLAYWRIGHT_AVAILABLE
from ..stealth.fingerprint_manager import FingerprintManager


class BypassStrategy(Enum):
    """Available bypass strategies"""
    DIRECT = "direct"
    CLOUDSCRAPER = "cloudscraper"
    SELENIUM_STEALTH = "selenium_stealth"
    PLAYWRIGHT_STEALTH = "playwright_stealth"
    FULL_ESCALATION = "full_escalation"


@dataclass
class BypassAttempt:
    """Record of a bypass attempt"""
    strategy: BypassStrategy
    success: bool
    duration: float
    challenge_type: ChallengeType
    error: Optional[str] = None
    response_code: Optional[int] = None


class BypassOrchestrator:
    """Orchestrates multiple bypass strategies with intelligent fallbacks"""
    
    def __init__(self, max_retries: int = 3, strategy_timeout: int = 60):
        """
        Initialize bypass orchestrator
        
        Args:
            max_retries: Maximum retry attempts per strategy
            strategy_timeout: Timeout per strategy attempt in seconds
        """
        self.max_retries = max_retries
        self.strategy_timeout = strategy_timeout
        
        # Initialize components
        self.challenge_detector = ChallengeDetector()
        self.fingerprint_manager = FingerprintManager()
        
        # Strategy instances
        self.cloudscraper = None
        self.selenium_stealth = None
        self.playwright_stealth = None
        
        # Success tracking
        self.attempt_history: List[BypassAttempt] = []
        self.strategy_success_rates: Dict[BypassStrategy, float] = {}
        
        # Strategy escalation order
        self.escalation_order = [
            BypassStrategy.DIRECT,
            BypassStrategy.CLOUDSCRAPER,
            BypassStrategy.SELENIUM_STEALTH,
            BypassStrategy.FULL_ESCALATION
        ]
        
        logger.info("Bypass orchestrator initialized")
    
    def bypass_cloudflare(self, url: str, **kwargs) -> Tuple[Any, Dict]:
        """
        Main bypass method - tries strategies until success
        
        Args:
            url: Target URL to bypass
            **kwargs: Additional parameters for requests
            
        Returns:
            Tuple of (response, metadata)
        """
        logger.info(f"Starting Cloudflare bypass for: {url}")
        
        # Generate fresh fingerprint
        fingerprint = self.fingerprint_manager.generate_fingerprint()
        
        # Try initial probe to detect challenge type
        challenge_type = self._probe_target(url)
        logger.info(f"Initial challenge detection: {challenge_type.value}")
        
        # Determine optimal strategy order based on challenge
        strategy_order = self._get_optimal_strategy_order(challenge_type)
        
        # Try each strategy until success
        for strategy in strategy_order:
            logger.info(f"Attempting bypass with strategy: {strategy.value}")
            
            success, response, metadata = self._attempt_strategy(
                strategy, url, challenge_type, fingerprint, **kwargs
            )
            
            if success:
                logger.success(f"Bypass successful with strategy: {strategy.value}")
                self._update_success_rates(strategy, True)
                return response, metadata
            else:
                logger.warning(f"Strategy failed: {strategy.value}")
                self._update_success_rates(strategy, False)
        
        # All strategies failed
        logger.error("All bypass strategies failed")
        raise Exception("Cloudflare bypass failed - all strategies exhausted")
    
    def _probe_target(self, url: str) -> ChallengeType:
        """
        Perform initial probe to detect challenge type
        
        Args:
            url: Target URL
            
        Returns:
            Detected challenge type
        """
        try:
            # Use a simple request to probe
            import requests
            
            response = requests.get(url, timeout=10, allow_redirects=True)
            challenge_type, _ = self.challenge_detector.detect_challenge(response)
            
            return challenge_type
            
        except Exception as e:
            logger.debug(f"Probe failed: {e}")
            return ChallengeType.UNKNOWN
    
    def _get_optimal_strategy_order(self, challenge_type: ChallengeType) -> List[BypassStrategy]:
        """
        Get optimal strategy order based on challenge type and success rates
        
        Args:
            challenge_type: Detected challenge type
            
        Returns:
            Ordered list of strategies to try
        """
        # Base strategy mapping
        strategy_mapping = {
            ChallengeType.NONE: [BypassStrategy.DIRECT],
            ChallengeType.JS_CHALLENGE: [BypassStrategy.CLOUDSCRAPER, BypassStrategy.SELENIUM_STEALTH],
            ChallengeType.CAPTCHA: [BypassStrategy.SELENIUM_STEALTH],
            ChallengeType.RATE_LIMIT: [BypassStrategy.CLOUDSCRAPER, BypassStrategy.SELENIUM_STEALTH],
            ChallengeType.ACCESS_DENIED: [BypassStrategy.CLOUDSCRAPER, BypassStrategy.SELENIUM_STEALTH],
            ChallengeType.UNDER_ATTACK_MODE: [BypassStrategy.SELENIUM_STEALTH],
            ChallengeType.BOT_FIGHT_MODE: [BypassStrategy.SELENIUM_STEALTH],
            ChallengeType.UNKNOWN: [BypassStrategy.CLOUDSCRAPER, BypassStrategy.SELENIUM_STEALTH]
        }
        
        strategies = strategy_mapping.get(challenge_type, self.escalation_order)
        
        # Sort by success rate if we have history
        if self.strategy_success_rates:
            strategies.sort(key=lambda s: self.strategy_success_rates.get(s, 0.5), reverse=True)
        
        return strategies
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _attempt_strategy(
        self, 
        strategy: BypassStrategy, 
        url: str, 
        challenge_type: ChallengeType,
        fingerprint: Dict,
        **kwargs
    ) -> Tuple[bool, Any, Dict]:
        """
        Attempt bypass with specific strategy
        
        Args:
            strategy: Strategy to attempt
            url: Target URL
            challenge_type: Detected challenge type
            fingerprint: Browser fingerprint to use
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (success, response, metadata)
        """
        start_time = time.time()
        metadata = {
            "strategy": strategy.value,
            "challenge_type": challenge_type.value,
            "fingerprint_seed": fingerprint.get("seed"),
            "attempt_time": start_time
        }
        
        try:
            if strategy == BypassStrategy.DIRECT:
                response = self._direct_request(url, fingerprint, **kwargs)
            elif strategy == BypassStrategy.CLOUDSCRAPER:
                response = self._cloudscraper_request(url, fingerprint, **kwargs)
            elif strategy == BypassStrategy.SELENIUM_STEALTH:
                response = self._selenium_request(url, fingerprint, **kwargs)
            elif strategy == BypassStrategy.PLAYWRIGHT_STEALTH:
                response = self._playwright_request(url, fingerprint, **kwargs)
            elif strategy == BypassStrategy.FULL_ESCALATION:
                response = self._full_escalation_request(url, challenge_type, fingerprint, **kwargs)
            else:
                raise ValueError(f"Unsupported strategy: {strategy}")
            
            # Verify bypass success
            success = self._verify_bypass_success(response, challenge_type)
            
            duration = time.time() - start_time
            metadata.update({
                "success": success,
                "duration": duration,
                "response_code": getattr(response, 'status_code', 200)
            })
            
            # Record attempt
            attempt = BypassAttempt(
                strategy=strategy,
                success=success,
                duration=duration,
                challenge_type=challenge_type,
                response_code=getattr(response, 'status_code', 200)
            )
            self.attempt_history.append(attempt)
            
            return success, response, metadata
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            metadata.update({
                "success": False,
                "duration": duration,
                "error": error_msg
            })
            
            # Record failed attempt
            attempt = BypassAttempt(
                strategy=strategy,
                success=False,
                duration=duration,
                challenge_type=challenge_type,
                error=error_msg
            )
            self.attempt_history.append(attempt)
            
            logger.error(f"Strategy {strategy.value} failed: {error_msg}")
            return False, None, metadata
    
    def _direct_request(self, url: str, fingerprint: Dict, **kwargs) -> Any:
        """Direct request without bypass"""
        import requests
        
        headers = self.fingerprint_manager.get_headers_for_fingerprint(fingerprint)
        response = requests.get(url, headers=headers, timeout=self.strategy_timeout, **kwargs)
        return response
    
    def _cloudscraper_request(self, url: str, fingerprint: Dict, **kwargs) -> Any:
        """Request using cloudscraper method"""
        if not self.cloudscraper:
            self.cloudscraper = CloudscraperMethod(timeout=self.strategy_timeout)
        
        response = self.cloudscraper.get(url, **kwargs)
        return response
    
    def _selenium_request(self, url: str, fingerprint: Dict, **kwargs) -> Any:
        """Request using Selenium stealth method"""
        if not self.selenium_stealth:
            self.selenium_stealth = SeleniumStealth(
                headless=kwargs.get('headless', True),
                timeout=self.strategy_timeout
            )
            # Apply fingerprint
            self.fingerprint_manager.apply_fingerprint_to_selenium(
                self.selenium_stealth.driver, fingerprint
            )
        
        response = self.selenium_stealth.get(url)
        return response
    
    def _playwright_request(self, url: str, fingerprint: Dict, **kwargs) -> Any:
        """Request using Playwright stealth method"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright strategy unavailable - install playwright to enable it.")
        
        if not self.playwright_stealth:
            self.playwright_stealth = PlaywrightStealth(
                headless=kwargs.get('headless', True),
                timeout=self.strategy_timeout
            )
        
        response = self.playwright_stealth.get(url)
        return response
    
    def _full_escalation_request(
        self,
        url: str,
        challenge_type: ChallengeType,
        fingerprint: Dict,
        **kwargs
    ) -> Any:
        """Run a chain of increasingly heavy strategies."""
        strategies = [
            self._cloudscraper_request,
            self._selenium_request,
            self._playwright_request
        ]
        
        last_exception = None
        for handler in strategies:
            try:
                response = handler(url, fingerprint, **kwargs)
                if self._verify_bypass_success(response, challenge_type):
                    return response
            except Exception as exc:
                last_exception = exc
                logger.debug(f"Escalation sub-strategy failed: {exc}")
                continue
        
        if last_exception:
            raise last_exception
        raise RuntimeError("Full escalation failed without response")
    
    def _verify_bypass_success(self, response: Any, original_challenge: ChallengeType) -> bool:
        """
        Verify that bypass was successful
        
        Args:
            response: Response object to verify
            original_challenge: Original challenge type detected
            
        Returns:
            True if bypass was successful
        """
        try:
            # Check response code
            status_code = getattr(response, 'status_code', 200)
            if hasattr(response, 'get') and 'status_code' in response:
                status_code = response['status_code']
            
            if status_code not in [200, 201, 202]:
                return False
            
            # Get response content
            content = ""
            if hasattr(response, 'text'):
                content = response.text
            elif hasattr(response, 'get') and 'text' in response:
                content = response['text']
            elif isinstance(response, dict) and 'text' in response:
                content = response['text']
            
            if not content:
                return False
            
            # Check for Cloudflare challenge indicators
            challenge_type, metadata = self.challenge_detector.detect_challenge(response)
            
            # Success if no challenge detected or different from original
            if challenge_type == ChallengeType.NONE:
                return True
            
            # Check for actual content vs challenge pages
            content_lower = content.lower()
            success_indicators = [
                "<html", "<body", "<div", "<p>", "<title>",
                "<!doctype", "<!DOCTYPE"
            ]
            
            # Only consider actual Cloudflare challenge indicators, not general mentions
            challenge_indicators = [
                "checking your browser",
                "cf-browser-verification",
                "challenge validation",
                "please wait while we check your browser",
                "cloudflare ray id" + " blocked",  # More specific patterns
                "please wait",
                "ray id:"
            ]
            
            has_content = any(indicator in content_lower for indicator in success_indicators)
            has_challenge = any(indicator in content_lower for indicator in challenge_indicators)
            
            # Additional checks for substantial content (SPA or regular websites)
            content_length = len(content)
            has_substantial_content = content_length > 5000  # Substantial content indicates success
            
            # Check for application/SPA indicators
            spa_indicators = ["<app-", "angular", "react", "vue", "ionic"]
            has_spa_content = any(indicator in content_lower for indicator in spa_indicators)
            
            # Success criteria:
            # 1. Has HTML structure AND no challenge indicators
            # 2. OR has substantial content (>5k chars) with no challenges
            # 3. OR is identified SPA content
            return (has_content and not has_challenge) or \
                   (has_substantial_content and not has_challenge) or \
                   (has_spa_content and not has_challenge)
            
        except Exception as e:
            logger.debug(f"Bypass verification failed: {e}")
            return False
    
    def _update_success_rates(self, strategy: BypassStrategy, success: bool):
        """Update strategy success rates"""
        if strategy not in self.strategy_success_rates:
            self.strategy_success_rates[strategy] = 0.5
        
        # Use exponential moving average
        current_rate = self.strategy_success_rates[strategy]
        new_value = 1.0 if success else 0.0
        alpha = 0.3  # Learning rate
        
        self.strategy_success_rates[strategy] = (
            alpha * new_value + (1 - alpha) * current_rate
        )
    
    def get_statistics(self) -> Dict:
        """Get bypass statistics and performance metrics"""
        total_attempts = len(self.attempt_history)
        successful_attempts = sum(1 for a in self.attempt_history if a.success)
        
        stats = {
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "success_rate": successful_attempts / total_attempts if total_attempts > 0 else 0,
            "average_duration": sum(a.duration for a in self.attempt_history) / total_attempts if total_attempts > 0 else 0,
            "strategy_success_rates": self.strategy_success_rates.copy(),
            "recent_attempts": [
                {
                    "strategy": a.strategy.value,
                    "success": a.success,
                    "duration": round(a.duration, 2),
                    "challenge": a.challenge_type.value
                }
                for a in self.attempt_history[-10:]  # Last 10 attempts
            ]
        }
        
        return stats
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.selenium_stealth:
                self.selenium_stealth.close()
                self.selenium_stealth = None
            if self.playwright_stealth:
                self.playwright_stealth.close()
                self.playwright_stealth = None
                
            logger.info("Bypass orchestrator cleaned up")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()