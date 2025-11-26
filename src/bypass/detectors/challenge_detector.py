"""
Cloudflare Challenge Detection System

Identifies different types of Cloudflare protection mechanisms and determines
the appropriate bypass strategy to use.
"""

import re
from typing import Dict, Optional, Tuple
from enum import Enum
from loguru import logger


class ChallengeType(Enum):
    """Types of Cloudflare challenges detected"""
    NONE = "none"
    JS_CHALLENGE = "js_challenge" 
    CAPTCHA = "captcha"
    RATE_LIMIT = "rate_limit"
    ACCESS_DENIED = "access_denied"
    UNDER_ATTACK_MODE = "under_attack_mode"
    BOT_FIGHT_MODE = "bot_fight_mode"
    UNKNOWN = "unknown"


class ChallengeDetector:
    """Detects Cloudflare protection mechanisms from HTTP responses"""
    
    def __init__(self):
        self.cf_patterns = {
            ChallengeType.JS_CHALLENGE: [
                r"Checking your browser before accessing",
                r"Please wait while your request is being verified",
                r"cf-browser-verification",
                r"__cf_bm",
                r"cf_clearance",
                r"ray ID:",
                r"cloudflare-nginx",
                r"Challenge Validation"
            ],
            ChallengeType.CAPTCHA: [
                r"captcha-delivery",
                r"cf-captcha-container",
                r"captcha\.website",
                r"Please complete the security check",
                r"cf-hcaptcha",
                r"h-captcha"
            ],
            ChallengeType.RATE_LIMIT: [
                r"Rate limited",
                r"Too many requests",
                r"You are being rate limited",
                r"Request blocked",
                r"Error 429"
            ],
            ChallengeType.ACCESS_DENIED: [
                r"Access denied",
                r"Error 1020",
                r"You do not have access to",
                r"This website is using a security service",
                r"Cloudflare.*blocked"
            ],
            ChallengeType.UNDER_ATTACK_MODE: [
                r"Under Attack Mode",
                r"DDoS protection by Cloudflare",
                r"Attack Mode Enabled",
                r"Security check"
            ],
            ChallengeType.BOT_FIGHT_MODE: [
                r"Bot Fight Mode",
                r"Automated traffic detected",
                r"cf-bot-fight-mode"
            ]
        }
        
        # Cloudflare server headers
        self.cf_headers = [
            "cf-ray",
            "cf-cache-status", 
            "cf-request-id",
            "server"
        ]
        
    def detect_challenge(self, response) -> Tuple[ChallengeType, Dict]:
        """
        Analyze HTTP response to detect Cloudflare challenge type
        
        Args:
            response: HTTP response object (requests.Response)
            
        Returns:
            Tuple of (ChallengeType, metadata dict)
        """
        try:
            status_code = response.status_code
            headers = response.headers
            content = response.text if hasattr(response, 'text') else str(response.content)
            
            metadata = {
                "status_code": status_code,
                "cf_ray": headers.get("cf-ray", ""),
                "server": headers.get("server", ""),
                "content_type": headers.get("content-type", ""),
                "cf_detected": self._is_cloudflare_response(headers)
            }
            
            # Check for Cloudflare presence first
            if not metadata["cf_detected"]:
                logger.debug("No Cloudflare headers detected")
                return ChallengeType.NONE, metadata
            
            # Check status code patterns
            if status_code == 429:
                metadata["challenge_reason"] = "HTTP 429 Too Many Requests"
                return ChallengeType.RATE_LIMIT, metadata
            elif status_code == 403:
                metadata["challenge_reason"] = "HTTP 403 Forbidden"
                return ChallengeType.ACCESS_DENIED, metadata
            elif status_code == 503:
                metadata["challenge_reason"] = "HTTP 503 Service Unavailable"
                return ChallengeType.JS_CHALLENGE, metadata
                
            # Analyze response content for challenge patterns
            challenge_type = self._analyze_content(content)
            
            if challenge_type != ChallengeType.NONE:
                metadata["challenge_reason"] = f"Content pattern match: {challenge_type.value}"
                logger.info(f"Detected Cloudflare challenge: {challenge_type.value}")
            
            return challenge_type, metadata
            
        except Exception as e:
            logger.error(f"Error detecting challenge: {e}")
            return ChallengeType.UNKNOWN, {"error": str(e)}
    
    def _is_cloudflare_response(self, headers: Dict) -> bool:
        """Check if response contains Cloudflare headers"""
        for header in self.cf_headers:
            if header in headers:
                return True
        
        # Check server header for cloudflare
        server = headers.get("server", "").lower()
        return "cloudflare" in server or "cf-" in str(headers).lower()
    
    def _analyze_content(self, content: str) -> ChallengeType:
        """Analyze response content for challenge patterns"""
        content_lower = content.lower()
        
        # Check each challenge type pattern
        for challenge_type, patterns in self.cf_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    logger.debug(f"Matched pattern '{pattern}' for {challenge_type.value}")
                    return challenge_type
        
        # Check for generic Cloudflare indicators
        cf_indicators = [
            "cloudflare",
            "cf_clearance", 
            "__cf_bm",
            "ray id"
        ]
        
        for indicator in cf_indicators:
            if indicator in content_lower:
                logger.debug(f"Found Cloudflare indicator: {indicator}")
                return ChallengeType.JS_CHALLENGE
                
        return ChallengeType.NONE
    
    def get_bypass_strategy(self, challenge_type: ChallengeType) -> str:
        """Get recommended bypass strategy for challenge type"""
        strategy_map = {
            ChallengeType.NONE: "direct",
            ChallengeType.JS_CHALLENGE: "cloudscraper", 
            ChallengeType.CAPTCHA: "selenium_stealth",
            ChallengeType.RATE_LIMIT: "delay_retry",
            ChallengeType.ACCESS_DENIED: "selenium_stealth",
            ChallengeType.UNDER_ATTACK_MODE: "selenium_stealth", 
            ChallengeType.BOT_FIGHT_MODE: "playwright_stealth",
            ChallengeType.UNKNOWN: "full_escalation"
        }
        
        return strategy_map.get(challenge_type, "selenium_stealth")
    
    def should_retry(self, challenge_type: ChallengeType) -> bool:
        """Determine if challenge type allows for retry attempts"""
        no_retry_types = {
            ChallengeType.ACCESS_DENIED,
            ChallengeType.CAPTCHA  # Requires manual intervention
        }
        
        return challenge_type not in no_retry_types