"""
Fingerprint Manager - Advanced Browser Fingerprinting and Spoofing

Manages browser fingerprints, user agents, TLS characteristics, and other
identifying features to avoid detection by Cloudflare's bot detection systems.
"""

import random
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from loguru import logger


class FingerprintManager:
    """Manages browser fingerprinting and anti-detection techniques"""
    
    def __init__(self):
        self.current_fingerprint = None
        self._load_fingerprint_data()
    
    def _load_fingerprint_data(self):
        """Load fingerprint databases and patterns"""
        # Real Chrome versions and their characteristics
        self.chrome_versions = [
            {"version": "120.0.0.0", "build": "6099", "webkit": "537.36"},
            {"version": "119.0.0.0", "build": "6045", "webkit": "537.36"}, 
            {"version": "118.0.0.0", "build": "5993", "webkit": "537.36"},
            {"version": "117.0.0.0", "build": "5938", "webkit": "537.36"}
        ]
        
        # Operating system variations
        self.os_patterns = [
            {"name": "Windows NT 10.0", "platform": "Win32", "arch": "x86_64"},
            {"name": "Windows NT 11.0", "platform": "Win32", "arch": "x86_64"},
            {"name": "Macintosh", "platform": "MacIntel", "arch": "x86_64"}
        ]
        
        # Screen resolutions (most common)
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (2560, 1440), (1600, 900), (1920, 1200)
        ]
        
        # Timezone variations
        self.timezones = [
            "America/New_York", "America/Chicago", "America/Denver", 
            "America/Los_Angeles", "America/Phoenix", "America/Anchorage"
        ]
        
        # Language preferences
        self.languages = [
            ["en-US", "en"], ["en-GB", "en"], ["en-CA", "en", "fr"],
            ["es-US", "es", "en"], ["fr-US", "fr", "en"]
        ]
        
        # WebGL and Canvas fingerprint data
        self.webgl_vendors = [
            "Google Inc. (Intel)", "Google Inc. (NVIDIA)", 
            "Google Inc. (AMD)", "Google Inc. (Qualcomm)"
        ]
        
        self.webgl_renderers = [
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)"
        ]
    
    def generate_fingerprint(self, fingerprint_type: str = "chrome") -> Dict:
        """
        Generate a complete browser fingerprint
        
        Args:
            fingerprint_type: Type of browser to mimic (chrome, firefox, etc.)
            
        Returns:
            Complete fingerprint dictionary
        """
        if fingerprint_type == "chrome":
            return self._generate_chrome_fingerprint()
        else:
            raise ValueError(f"Unsupported fingerprint type: {fingerprint_type}")
    
    def _generate_chrome_fingerprint(self) -> Dict:
        """Generate realistic Chrome browser fingerprint"""
        
        # Select random versions and OS
        chrome_data = random.choice(self.chrome_versions)
        os_data = random.choice(self.os_patterns)
        resolution = random.choice(self.screen_resolutions)
        timezone = random.choice(self.timezones)
        languages = random.choice(self.languages)
        
        # Generate user agent
        if os_data["name"].startswith("Windows"):
            user_agent = f"Mozilla/5.0 ({os_data['name']}; Win64; x64) AppleWebKit/{chrome_data['webkit']} (KHTML, like Gecko) Chrome/{chrome_data['version']} Safari/{chrome_data['webkit']}"
        else:  # Mac
            user_agent = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/{chrome_data['webkit']} (KHTML, like Gecko) Chrome/{chrome_data['version']} Safari/{chrome_data['webkit']}"
        
        # Generate WebGL data
        webgl_vendor = random.choice(self.webgl_vendors)
        webgl_renderer = random.choice(self.webgl_renderers)
        
        # Canvas fingerprint (simplified hash)
        canvas_data = f"{resolution[0]}x{resolution[1]}{webgl_renderer}{user_agent}"
        canvas_hash = hashlib.md5(canvas_data.encode()).hexdigest()[:16]
        
        fingerprint = {
            # User Agent and basic info
            "user_agent": user_agent,
            "platform": os_data["platform"],
            "languages": languages,
            "timezone": timezone,
            
            # Screen and display
            "screen_width": resolution[0],
            "screen_height": resolution[1],
            "color_depth": 24,
            "pixel_ratio": round(random.uniform(1.0, 2.0), 1),
            
            # Browser capabilities
            "cookies_enabled": True,
            "java_enabled": False,
            "plugins": self._generate_plugin_list(),
            
            # WebGL fingerprinting
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": webgl_renderer,
            "webgl_version": "WebGL 1.0",
            
            # Canvas fingerprinting 
            "canvas_hash": canvas_hash,
            
            # Audio fingerprinting
            "audio_hash": hashlib.md5(f"{user_agent}{timezone}".encode()).hexdigest()[:12],
            
            # Hardware info
            "cpu_cores": random.choice([4, 6, 8, 12, 16]),
            "memory_gb": random.choice([8, 16, 32]),
            
            # Network info
            "connection_type": random.choice(["ethernet", "wifi", "cellular"]),
            "effective_type": random.choice(["4g", "3g"]),
            
            # Chrome-specific
            "chrome_version": chrome_data["version"],
            "chrome_build": chrome_data["build"],
            "webkit_version": chrome_data["webkit"],
            
            # Randomization seed for consistency
            "seed": random.randint(100000, 999999)
        }
        
        self.current_fingerprint = fingerprint
        logger.info(f"Generated fingerprint with seed: {fingerprint['seed']}")
        return fingerprint
    
    def _generate_plugin_list(self) -> List[Dict]:
        """Generate realistic plugin list"""
        base_plugins = [
            {
                "name": "Chrome PDF Plugin",
                "filename": "internal-pdf-viewer",
                "description": "Portable Document Format"
            },
            {
                "name": "Chrome PDF Viewer", 
                "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                "description": "PDF Viewer"
            },
            {
                "name": "Native Client",
                "filename": "internal-nacl-plugin", 
                "description": "Native Client"
            }
        ]
        
        # Randomly add additional plugins
        optional_plugins = [
            {
                "name": "Microsoft Edge PDF Plugin",
                "filename": "pdf",
                "description": "PDF Viewer"
            },
            {
                "name": "WebKit built-in PDF",
                "filename": "webkit-pdf",
                "description": "WebKit PDF"
            }
        ]
        
        plugins = base_plugins.copy()
        if random.random() > 0.5:  # 50% chance to add optional plugins
            plugins.extend(random.sample(optional_plugins, k=random.randint(1, len(optional_plugins))))
        
        return plugins
    
    def apply_fingerprint_to_selenium(self, driver, fingerprint: Optional[Dict] = None):
        """
        Apply fingerprint to Selenium WebDriver
        
        Args:
            driver: Selenium WebDriver instance
            fingerprint: Fingerprint to apply (uses current if None)
        """
        if fingerprint is None:
            fingerprint = self.current_fingerprint
        
        if not fingerprint:
            logger.warning("No fingerprint available to apply")
            return
        
        try:
            # Override navigator properties
            stealth_script = f"""
            // Override navigator properties
            Object.defineProperty(navigator, 'platform', {{get: () => '{fingerprint["platform"]}'}});
            Object.defineProperty(navigator, 'languages', {{get: () => {json.dumps(fingerprint["languages"])}}});
            Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {fingerprint["cpu_cores"]}}});
            Object.defineProperty(navigator, 'deviceMemory', {{get: () => {fingerprint["memory_gb"]}}});
            
            // Override screen properties
            Object.defineProperty(screen, 'width', {{get: () => {fingerprint["screen_width"]}}});
            Object.defineProperty(screen, 'height', {{get: () => {fingerprint["screen_height"]}}});
            Object.defineProperty(screen, 'colorDepth', {{get: () => {fingerprint["color_depth"]}}});
            
            // Override WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return '{fingerprint["webgl_vendor"]}';
                if (parameter === 37446) return '{fingerprint["webgl_renderer"]}';
                return getParameter.call(this, parameter);
            }};
            
            // Override timezone
            Intl.DateTimeFormat.prototype.resolvedOptions = function() {{
                return {{
                    timeZone: '{fingerprint["timezone"]}',
                    locale: '{fingerprint["languages"][0]}'
                }};
            }};
            
            // Canvas fingerprint consistency
            const toDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {{
                const context = this.getContext('2d');
                if (context) {{
                    // Add consistent noise based on fingerprint
                    const seed = {fingerprint["seed"]};
                    const noise = (seed % 255) / 255;
                    context.globalAlpha = 1 - (noise * 0.01);
                }}
                return toDataURL.apply(this, arguments);
            }};
            """
            
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': stealth_script
            })
            
            logger.debug("Fingerprint applied to Selenium driver")
            
        except Exception as e:
            logger.warning(f"Failed to apply fingerprint: {e}")
    
    def get_headers_for_fingerprint(self, fingerprint: Optional[Dict] = None) -> Dict:
        """
        Get HTTP headers matching the fingerprint
        
        Args:
            fingerprint: Fingerprint to use (uses current if None)
            
        Returns:
            Headers dictionary
        """
        if fingerprint is None:
            fingerprint = self.current_fingerprint
        
        if not fingerprint:
            fingerprint = self.generate_fingerprint()
        
        headers = {
            "User-Agent": fingerprint["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": ",".join(fingerprint["languages"]) + ";q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        return headers
    
    def rotate_fingerprint(self) -> Dict:
        """Generate and set new fingerprint"""
        logger.info("Rotating browser fingerprint")
        return self.generate_fingerprint()
    
    def get_tls_config(self, fingerprint: Optional[Dict] = None) -> Dict:
        """
        Get TLS configuration matching the fingerprint
        
        Args:
            fingerprint: Fingerprint to use
            
        Returns:
            TLS configuration dictionary
        """
        if fingerprint is None:
            fingerprint = self.current_fingerprint
        
        if not fingerprint:
            fingerprint = self.generate_fingerprint()
        
        # TLS settings that match Chrome
        tls_config = {
            "cipher_suites": [
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384", 
                "TLS_CHACHA20_POLY1305_SHA256",
                "ECDHE-ECDSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-ECDSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES256-GCM-SHA384"
            ],
            "tls_version": "TLSv1.3",
            "curves": ["X25519", "P-256", "P-384"],
            "signature_algorithms": [
                "ecdsa_secp256r1_sha256",
                "rsa_pss_rsae_sha256", 
                "rsa_pkcs1_sha256"
            ]
        }
        
        return tls_config
    
    def save_fingerprint(self, filename: str):
        """Save current fingerprint to file"""
        if self.current_fingerprint:
            with open(filename, 'w') as f:
                json.dump(self.current_fingerprint, f, indent=2)
            logger.info(f"Fingerprint saved to {filename}")
    
    def load_fingerprint(self, filename: str) -> Dict:
        """Load fingerprint from file"""
        with open(filename, 'r') as f:
            fingerprint = json.load(f)
        self.current_fingerprint = fingerprint
        logger.info(f"Fingerprint loaded from {filename}")
        return fingerprint