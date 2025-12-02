#!/usr/bin/env python3
"""
CloudDestroyer Production API
Restaurant menu scraping with intelligent detection and extraction
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Dict, List, Optional, Any, Tuple
import json
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging

# Import CloudDestroyer
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.core.cloud_destroyer import CloudDestroyer
from src.bypass.bypass_orchestrator import BypassOrchestrator, BypassStrategy
from src.bypass.session_manager import SessionManager
from src.bypass.detectors.challenge_detector import ChallengeDetector, ChallengeType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CloudDestroyer API",
    description="Production-ready restaurant menu scraping API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Production API Models
class RestaurantScrapeRequest(BaseModel):
    website_url: HttpUrl
    restaurant_name: Optional[str] = None
    force_menu_url: Optional[str] = None
    
    @field_validator('website_url')
    @classmethod
    def validate_url(cls, v):
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL must include http:// or https://')
        return v

class MenuExtractionResult(BaseModel):
    success: bool
    restaurant_name: str
    website_url: str
    menu_url: str
    items_found: int
    categories_found: int
    processing_time_seconds: float
    confidence_score: float
    menu_data: Dict[str, Any]
    error_message: Optional[str] = None

# Production Restaurant Menu Engine
class RestaurantMenuScraper:
    """Production restaurant menu scraper using multi-strategy CloudDestroyer bypass"""
    
    MENU_PATHS = [
        '/menu', '/menus', '/our-menu', '/food-menu', '/dining-menu',
        '/lunch-menu', '/dinner-menu', '/full-menu', '/menu/', '/food',
        '/order', '/order-online', '/ordering', '/takeout', '/delivery',
        '/eat', '/dine', '/restaurant-menu', '/online-menu', '/mobile-menu',
        '/catering', '/specials', '/today', '/current-menu'
    ]
    
    MENU_INDICATORS = [
        'menu', 'appetizer', 'entree', 'main', 'dessert', 'beverage', 'drink',
        'pizza', 'burger', 'sandwich', 'salad', 'pasta', 'chicken', 'beef',
        'price', '$', 'order', 'delivery', 'takeout', 'dine-in'
    ]
    
    def __init__(self, save_api_endpoints: bool = True):
        self.destroyer = CloudDestroyer(
            headless=True,
            session_persistence=True,
            max_retries=3,
            timeout=60
        )
        self.orchestrator = BypassOrchestrator(max_retries=3, strategy_timeout=60)
        self.session_manager = SessionManager()
        self.challenge_detector = ChallengeDetector()
        self.save_api_endpoints = save_api_endpoints
        self._db_manager = None  # Lazy initialization
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'orchestrator'):
            self.orchestrator.cleanup()
        # SessionManager doesn't have cleanup method, it handles cleanup automatically
        if self._db_manager:
            self._db_manager.close()

    @property
    def db(self):
        """Lazy initialization of database manager"""
        if self._db_manager is None and self.save_api_endpoints:
            try:
                from db_config import DatabaseManager
                self._db_manager = DatabaseManager()
            except Exception as e:
                logger.warning(f"Failed to initialize database manager: {e}")
        return self._db_manager

    def _save_discovered_api_endpoint(self, domain: str, endpoint: str, endpoint_type: str = 'unknown',
                                      requires_location: bool = False, site_type: str = None):
        """Save discovered API endpoint to database"""
        if not self.save_api_endpoints or not self.db:
            return

        try:
            # Determine authentication method from endpoint
            auth_method = 'none'
            if any(x in endpoint.lower() for x in ['auth', 'token', 'key']):
                auth_method = 'session'

            result = self.db.save_api_endpoint(
                domain=domain,
                api_menu_endpoint=endpoint,
                api_endpoint_type=endpoint_type,
                requires_location=requires_location,
                authentication_method=auth_method,
                site_type=site_type
            )
            logger.info(f"Saved API endpoint to database: {endpoint} (type: {endpoint_type})")
            return result
        except Exception as e:
            logger.warning(f"Failed to save API endpoint to database: {e}")
            return None

    def _try_api_extraction(self, website_url: str, restaurant_name: Optional[str] = None) -> Optional[MenuExtractionResult]:
        """
        Try to extract menu using API-first approach
        1. Check database for saved endpoint
        2. If found and working, use it directly
        3. If not found, try API discovery with CDP
        4. Return None if API extraction fails (fallback to traditional scraping)
        """
        start_time = datetime.now()
        parsed_url = urlparse(website_url)
        domain = parsed_url.netloc

        logger.info(f"Attempting API-first extraction for {domain}")

        # Step 1: Check database for saved endpoint
        saved_endpoint = None
        if self.db:
            try:
                saved_endpoint = self.db.get_api_endpoint(domain)
                if saved_endpoint and saved_endpoint.get('api_endpoint_working'):
                    logger.info(f"Found saved API endpoint for {domain}")

                    # Try to use saved endpoint
                    result = self._use_saved_api_endpoint(
                        saved_endpoint,
                        website_url,
                        restaurant_name,
                        start_time
                    )

                    if result and result.success:
                        logger.success(f"Successfully used saved API endpoint")
                        self.db.verify_api_endpoint(domain)
                        return result
                    else:
                        logger.warning("Saved API endpoint failed, marking as broken")
                        self.db.mark_api_endpoint_failed(domain, "Endpoint returned no data or error")
                        saved_endpoint = None  # Force re-discovery
            except Exception as e:
                logger.warning(f"Error using saved endpoint: {e}")

        # Step 2: Try API discovery if no saved endpoint or it failed
        if not saved_endpoint:
            logger.info("No saved endpoint or it failed - attempting API discovery")
            result = self._discover_and_use_api(website_url, restaurant_name, start_time, domain)

            if result and result.success:
                return result

        # Step 3: Return None to fallback to traditional scraping
        logger.info("API extraction unsuccessful, will fallback to traditional scraping")
        return None

    def _use_saved_api_endpoint(
        self,
        endpoint_info: Dict,
        website_url: str,
        restaurant_name: Optional[str],
        start_time: datetime
    ) -> Optional[MenuExtractionResult]:
        """
        Use a saved API endpoint to extract menu data
        """
        try:
            from api_menu_parser import APIMenuParser

            api_endpoint = endpoint_info['api_menu_endpoint']
            auth_method = endpoint_info.get('api_authentication_method', 'none')

            logger.info(f"Using saved endpoint: {api_endpoint}")
            logger.info(f"Authentication method: {auth_method}")

            # If API key is required, we need to extract it
            api_key_headers = {}
            if auth_method == 'api_key':
                logger.info("API key required - extracting from website")
                api_key_headers = self._extract_api_keys(website_url)

                if not api_key_headers:
                    logger.warning("Could not extract required API key")
                    return None

            # Parse menu from API
            parser = APIMenuParser(api_key_headers=api_key_headers)
            result = parser.fetch_and_parse(api_endpoint)

            if not result['success']:
                return None

            # Convert to MenuExtractionResult
            processing_time = (datetime.now() - start_time).total_seconds()

            return MenuExtractionResult(
                success=True,
                restaurant_name=restaurant_name or urlparse(website_url).netloc,
                website_url=website_url,
                menu_url=api_endpoint,
                items_found=len(result['items']),
                categories_found=len(result['categories']),
                processing_time_seconds=processing_time,
                confidence_score=1.0,  # API data is highly confident
                menu_data={
                    'categories': result['categories'],
                    'items': result['items'],
                    'extraction_method': 'api_saved_endpoint'
                }
            )

        except ImportError:
            logger.warning("api_menu_parser module not found - skipping API extraction")
            return None
        except Exception as e:
            logger.error(f"Error using saved API endpoint: {e}")
            return None

    def _discover_and_use_api(
        self,
        website_url: str,
        restaurant_name: Optional[str],
        start_time: datetime,
        domain: str
    ) -> Optional[MenuExtractionResult]:
        """
        Discover API endpoints and keys, then extract menu data
        """
        try:
            from api_key_extractor import APIKeyExtractor
            from api_menu_parser import APIMenuParser

            logger.info("Starting API discovery with CDP")

            # Extract API keys and endpoints
            extractor = APIKeyExtractor()
            discovery_result = extractor.extract_from_url(website_url, wait_time=10)

            if not discovery_result['success']:
                logger.info("No API keys or endpoints discovered")
                return None

            api_keys = discovery_result['api_keys']
            endpoints = discovery_result['endpoints']

            logger.info(f"Discovered {len(api_keys)} API key types and {len(endpoints)} endpoints")

            # Convert API keys dict to headers format
            api_key_headers = {
                '-'.join(word.capitalize() for word in header.split('-')): value
                for header, value in api_keys.items()
            }

            # Try menu-related endpoints
            parser = APIMenuParser(api_key_headers=api_key_headers)

            for endpoint_info in endpoints:
                endpoint_url = endpoint_info['url']

                # Check if this looks like a menu endpoint
                if any(keyword in endpoint_url.lower() for keyword in ['menu', 'meal', 'product', 'catalog']):
                    logger.info(f"Trying menu endpoint: {endpoint_url[:80]}...")

                    result = parser.fetch_and_parse(endpoint_url)

                    if result['success'] and len(result['items']) >= 10:
                        logger.success(f"Successfully extracted {len(result['items'])} items from API")

                        # Save this endpoint to database
                        endpoint_type = 'rest'
                        if 'graphql' in endpoint_url.lower():
                            endpoint_type = 'graphql'

                        self._save_discovered_api_endpoint(
                            domain=domain,
                            endpoint=endpoint_url,
                            endpoint_type=endpoint_type,
                            requires_location=False,
                            site_type='api_driven'
                        )

                        # Return result
                        processing_time = (datetime.now() - start_time).total_seconds()

                        return MenuExtractionResult(
                            success=True,
                            restaurant_name=restaurant_name or domain,
                            website_url=website_url,
                            menu_url=endpoint_url,
                            items_found=len(result['items']),
                            categories_found=len(result['categories']),
                            processing_time_seconds=processing_time,
                            confidence_score=1.0,
                            menu_data={
                                'categories': result['categories'],
                                'items': result['items'],
                                'extraction_method': 'api_discovery'
                            }
                        )

            logger.info("No suitable menu endpoints found in discovery")
            return None

        except ImportError:
            logger.warning("API extraction modules not found - skipping")
            return None
        except Exception as e:
            logger.error(f"Error during API discovery: {e}")
            return None

    def _extract_api_keys(self, website_url: str) -> Dict[str, str]:
        """
        Extract API keys from a website using CDP
        Returns dict of header names to values
        """
        try:
            from api_key_extractor import APIKeyExtractor

            extractor = APIKeyExtractor()
            result = extractor.extract_from_url(website_url, wait_time=10)

            if result['success'] and result['api_keys']:
                # Convert to proper header format
                headers = {}
                for header_name, value in result['api_keys'].items():
                    # Proper case header names
                    proper_name = '-'.join(word.capitalize() for word in header_name.split('-'))
                    headers[proper_name] = value

                return headers

            return {}

        except Exception as e:
            logger.error(f"Error extracting API keys: {e}")
            return {}

    def find_menu_page(self, base_url: str) -> tuple[str, float]:
        """Comprehensive 15-attempt menu page discovery with intelligent scoring"""
        # Returns (url, score) tuple
        
        try:
            import time
            discovery_start_time = time.time()
            discovery_timeout = 300  # 5 minutes max for entire discovery process
            
            parsed_url = urlparse(base_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            logger.info(f"Starting comprehensive menu discovery for: {base_url}")
            
            # Initialize discovery tracking
            discovery_log = []
            best_candidate = None
            best_score = 0
            attempt = 0
            
            # TIER 1: Direct Menu Paths (Attempts 1-5)
            logger.info("Tier 1: Testing direct menu paths...")
            priority_paths = ['/menu', '/our-menu', '/food-menu', '/menus', '/dining']
            
            for path in priority_paths:
                # Check timeout
                if time.time() - discovery_start_time > discovery_timeout:
                    logger.warning(f"Discovery timeout reached ({discovery_timeout}s), terminating")
                    break
                    
                attempt += 1
                menu_url = urljoin(base_domain, path)
                
                try:
                    start_time = time.time()
                    response = self._get_with_orchestrator_bypass(menu_url)
                    response_time = (time.time() - start_time) * 1000
                    
                    if self._is_successful_response(response):
                        content = self._extract_content_from_response(response)
                        score = self._score_menu_content(content, menu_url)
                        
                        discovery_log.append({
                            'attempt': attempt,
                            'method': f'direct_path_{path}',
                            'url': menu_url,
                            'score': score,
                            'response_time_ms': int(response_time),
                            'content_length': len(content)
                        })
                        
                        logger.info(f"Attempt {attempt}: {menu_url} scored {score} ({int(response_time)}ms)")
                        
                        if score > best_score:
                            best_score = score
                            best_candidate = menu_url
                            
                        # Early return for good scores (8+ is sufficient for menu page)
                        if score >= 8:
                            logger.info(f"EARLY EXIT: Good menu page found: {menu_url} (score: {score})")
                            self._log_discovery_success(base_url, menu_url, attempt, 'direct_path', discovery_log)
                            return menu_url, score
                            
                except Exception as e:
                    discovery_log.append({
                        'attempt': attempt,
                        'method': f'direct_path_{path}',
                        'url': menu_url,
                        'error': str(e)
                    })
                    continue
            
            # EARLY EXIT CHECK: If we found a good score in Tier 1, return it
            if best_score >= 8 and best_candidate:
                logger.info(f"EARLY EXIT after Tier 1: Best score {best_score} for {best_candidate}")
                return best_candidate, best_score
            
            # TIER 2: Extended Path Discovery (Attempts 6-8)
            logger.info("Tier 2: Extended path discovery...")
            extended_paths = ['/order', '/order-online', '/takeout', '/delivery', '/eat']
            
            for path in extended_paths[:3]:  # Limit to 3 attempts
                attempt += 1
                menu_url = urljoin(base_domain, path)
                
                try:
                    response = self._get_with_orchestrator_bypass(menu_url)
                    if self._is_successful_response(response):
                        content = self._extract_content_from_response(response)
                        score = self._score_menu_content(content, menu_url)
                        
                        discovery_log.append({
                            'attempt': attempt,
                            'method': f'extended_path_{path}',
                            'url': menu_url,
                            'score': score
                        })
                        
                        if score > best_score:
                            best_score = score
                            best_candidate = menu_url
                        
                        # Early exit for good scores
                        if score >= 8:
                            logger.info(f"EARLY EXIT: Good menu page found in Tier 2: {menu_url} (score: {score})")
                            return menu_url, score
                            
                except Exception:
                    continue
            
            # EARLY EXIT CHECK: If we found a good score in Tier 2, return it
            if best_score >= 6 and best_candidate:
                logger.info(f"EARLY EXIT after Tier 2: Best score {best_score} for {best_candidate}")
                return best_candidate, best_score
            
            # TIER 3: Sitemap and Navigation Analysis (Attempts 9-11)
            # Only proceed if we haven't found a good menu page yet
            if attempt < 15 and best_score < 6:
                logger.info("Tier 3: Sitemap and navigation analysis...")
                
                # Attempt 9: Sitemap parsing
                if attempt < 15:
                    attempt += 1
                    try:
                        sitemap_urls = self._parse_sitemap(base_domain)
                        if sitemap_urls:
                            for sitemap_url in sitemap_urls[:2]:  # Test top 2 sitemap URLs
                                try:
                                    response = self._get_with_orchestrator_bypass(sitemap_url)
                                    if self._is_successful_response(response):
                                        content = self._extract_content_from_response(response)
                                        score = self._score_menu_content(content, sitemap_url)
                                        
                                        discovery_log.append({
                                            'attempt': attempt,
                                            'method': 'sitemap_discovery',
                                            'url': sitemap_url,
                                            'score': score
                                        })
                                        
                                        if score > best_score:
                                            best_score = score
                                            best_candidate = sitemap_url
                                            
                                        # Early termination for good scores
                                        if score >= 12:
                                            break
                                except Exception as e:
                                    logger.debug(f"Sitemap URL failed: {sitemap_url} - {e}")
                                    continue
                    except Exception as e:
                        logger.warning(f"Sitemap parsing failed: {e}")
                        discovery_log.append({
                            'attempt': attempt,
                            'method': 'sitemap_discovery',
                            'error': str(e)
                        })
                
                # Attempt 10: Main page link analysis
                attempt += 1
                menu_links = self._extract_menu_links_from_main_page(base_url)
                if menu_links:
                    for link_score, candidate_url in sorted(menu_links, reverse=True)[:3]:
                        try:
                            response = self._get_with_orchestrator_bypass(candidate_url)
                            if self._is_successful_response(response):
                                content = self._extract_content_from_response(response)
                                score = self._score_menu_content(content, candidate_url)
                                
                                if score > best_score:
                                    best_score = score
                                    best_candidate = candidate_url
                                    discovery_log.append({
                                        'attempt': attempt,
                                        'method': 'link_analysis',
                                        'url': candidate_url,
                                        'score': score
                                    })
                                    break
                        except Exception:
                            continue
                
                # Attempt 11: Schema markup analysis
                attempt += 1
                schema_urls = self._analyze_schema_markup(base_url)
                if schema_urls:
                    for schema_url in schema_urls[:2]:
                        try:
                            response = self._get_with_orchestrator_bypass(schema_url)
                            if self._is_successful_response(response):
                                content = self._extract_content_from_response(response)
                                score = self._score_menu_content(content, schema_url)
                                
                                if score > best_score:
                                    best_score = score
                                    best_candidate = schema_url
                                    discovery_log.append({
                                        'attempt': attempt,
                                        'method': 'schema_markup',
                                        'url': schema_url,
                                        'score': score
                                    })
                                    break
                        except Exception:
                            continue
            
            # TIER 4: JavaScript Rendering and Third-Party Detection (Attempts 12-14)  
            if attempt < 15 and best_score < 10:
                logger.info("Tier 4: JavaScript rendering and third-party detection...")
                
                # Attempt 12: JavaScript rendering check
                if attempt < 15:
                    attempt += 1
                    try:
                        if self._needs_js_rendering(base_url):
                            js_urls = self._discover_js_menu_urls(base_url)
                            for js_url in js_urls[:2]:
                                try:
                                    response = self._get_with_orchestrator_bypass(js_url)
                                    if self._is_successful_response(response):
                                        content = self._extract_content_from_response(response)
                                        score = self._score_menu_content(content, js_url)
                                        
                                        discovery_log.append({
                                            'attempt': attempt,
                                            'method': 'javascript_rendering',
                                            'url': js_url,
                                            'score': score
                                        })
                                        
                                        if score > best_score:
                                            best_score = score
                                            best_candidate = js_url
                                            
                                        if score >= 10:
                                            break
                                except Exception as e:
                                    logger.debug(f"JS URL failed: {js_url} - {e}")
                                    continue
                        else:
                            discovery_log.append({
                                'attempt': attempt,
                                'method': 'javascript_rendering',
                                'skipped': 'No JS rendering needed'
                            })
                    except Exception as e:
                        logger.warning(f"JS rendering check failed: {e}")
                        discovery_log.append({
                            'attempt': attempt,
                            'method': 'javascript_rendering',
                            'error': str(e)
                        })
                
                # Attempt 13: Third-party menu service detection
                attempt += 1
                third_party_urls = self._detect_third_party_menu_services(base_url)
                if third_party_urls:
                    for service_name, service_url in third_party_urls.items():
                        try:
                            # Note: This would require special handling for third-party APIs
                            logger.info(f"Detected {service_name} integration: {service_url}")
                            discovery_log.append({
                                'attempt': attempt,
                                'method': 'third_party_detection',
                                'service': service_name,
                                'url': service_url
                            })
                            break  # Just log detection, don't try to scrape third-party directly
                        except Exception:
                            continue
                
                # Attempt 14: Deep crawling with intelligent filtering
                attempt += 1
                deep_crawl_urls = self._crawl_internal_links(base_url, max_depth=2)
                if deep_crawl_urls:
                    for crawl_url in deep_crawl_urls[:3]:
                        try:
                            response = self._get_with_orchestrator_bypass(crawl_url)
                            if self._is_successful_response(response):
                                content = self._extract_content_from_response(response)
                                score = self._score_menu_content(content, crawl_url)
                                
                                if score > best_score:
                                    best_score = score
                                    best_candidate = crawl_url
                                    discovery_log.append({
                                        'attempt': attempt,
                                        'method': 'deep_crawling',
                                        'url': crawl_url,
                                        'score': score
                                    })
                                    break
                        except Exception:
                            continue
            
            # TIER 5: Final Fallback (Attempt 15)
            if attempt < 15 and best_score < 8:
                attempt += 1
                logger.info("Tier 5: Final fallback to base URL analysis...")
                
                try:
                    response = self._get_with_orchestrator_bypass(base_url)
                    if self._is_successful_response(response):
                        content = self._extract_content_from_response(response)
                        score = self._score_menu_content(content, base_url)
                        
                        discovery_log.append({
                            'attempt': attempt,
                            'method': 'base_url_fallback',
                            'url': base_url,
                            'score': score
                        })
                        
                        if score > best_score or best_candidate is None:
                            best_score = score
                            best_candidate = base_url
                            
                except Exception as e:
                    logger.error(f"Final fallback failed: {e}")
            
            # Early termination if we found a really good candidate
            if best_candidate and best_score >= 8:
                logger.info(f"Early termination - good candidate found: {best_candidate} (score: {best_score})")
                self._save_discovery_log(base_url, discovery_log, best_candidate, best_score)
                return best_candidate, best_score
            
            # Log discovery results and return best candidate
            final_url = best_candidate or base_url
            
            logger.info(f"Menu discovery completed: {final_url} (score: {best_score}, attempts: {attempt})")
            
            # Save discovery log for debugging
            self._save_discovery_log(base_url, discovery_log, final_url, best_score)
            
            return final_url, best_score
            
        except Exception as e:
            logger.error(f"Critical error in menu discovery: {e}")
            return base_url, 0
    
    def detect_api_endpoints(self, page_content: str, base_url: str) -> List[str]:
        """Detect potential API endpoints for menu data with dynamic JavaScript discovery"""
        
        endpoints = []
        
        # =================================================================
        # OLO-SPECIFIC API DETECTION (Priority for restaurant ordering platforms)
        # =================================================================
        olo_endpoints = self._detect_olo_api_endpoints(page_content, base_url)
        if olo_endpoints:
            logger.info(f"Found {len(olo_endpoints)} OLO API endpoints")
            endpoints.extend(olo_endpoints)
        
        # Static pattern detection (fallback)
        api_patterns = [
            r'/api/menu', r'/api/v\d+/menu', r'/wp-json/.*menu',
            r'/rest/.*menu', r'/api/.*food', r'/menu\.json', r'/data/menu',
            r'/api/.*items', r'/api/.*products', r'/graphql.*menu',
            # OLO patterns
            r'/api/olo/.*', r'/olo/.*menu', r'/api/restaurants/\d+/menu'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                endpoints.append(urljoin(base_url, match))
        
        # Dynamic JavaScript API discovery
        js_endpoints = self._discover_js_api_endpoints(base_url)
        endpoints.extend(js_endpoints)
        
        # If we didn't find API endpoints, try direct JavaScript extraction with navigation
        if not endpoints:
            logger.info("No API endpoints found, attempting direct JavaScript extraction with navigation")
            js_menu_data = self._extract_js_menu_with_navigation(base_url)
            if js_menu_data.get('success') and js_menu_data.get('total_items', 0) > 0:
                # Store the result for later use
                self._direct_extraction_result = js_menu_data
                endpoints.append("DIRECT_EXTRACTION_AVAILABLE")
        
        return list(set(endpoints))
    
    def _detect_olo_api_endpoints(self, page_content: str, base_url: str) -> List[str]:
        """
        Detect OLO (Online Ordering) API endpoints specifically.
        OLO is used by many restaurant chains including Bubba's 33.
        
        OLO API format: /api/olo/restaurants/{restaurant_id}/menu
        """
        endpoints = []
        parsed_url = urlparse(base_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Pattern 1: Direct OLO restaurant ID in JavaScript/HTML
        # Look for patterns like: restaurantId: 236820, "restaurant_id": "236820", etc.
        olo_id_patterns = [
            r'restaurantId["\']?\s*[:=]\s*["\']?(\d{5,8})["\']?',
            r'restaurant[_-]?id["\']?\s*[:=]\s*["\']?(\d{5,8})["\']?',
            r'vendorId["\']?\s*[:=]\s*["\']?(\d{5,8})["\']?',
            r'vendor[_-]?id["\']?\s*[:=]\s*["\']?(\d{5,8})["\']?',
            r'/restaurants/(\d{5,8})/',
            r'/api/olo/restaurants/(\d{5,8})',
            r'olo.*?["\']?id["\']?\s*[:=]\s*["\']?(\d{5,8})["\']?',
            # Look for OLO config objects
            r'oloConfig.*?(\d{5,8})',
            r'menuConfig.*?restaurantId.*?(\d{5,8})',
        ]
        
        restaurant_ids = set()
        for pattern in olo_id_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                if match and len(match) >= 5:  # OLO IDs are typically 5-8 digits
                    restaurant_ids.add(match)
                    logger.info(f"Found potential OLO restaurant ID: {match}")
        
        # Pattern 2: Look for explicit OLO API URLs in the content
        olo_url_patterns = [
            r'(https?://[^"\'\s]*olo[^"\'\s]*(?:menu|restaurant)[^"\'\s]*)',
            r'["\']([^"\']*api/olo[^"\']*)["\']',
            r'["\']([^"\']*olo\.com[^"\']*menu[^"\']*)["\']',
        ]
        
        for pattern in olo_url_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                if match:
                    endpoints.append(match)
                    logger.info(f"Found OLO API URL: {match}")
        
        # Pattern 3: Build OLO API endpoints from discovered IDs
        for restaurant_id in restaurant_ids:
            # Standard OLO API format
            olo_menu_url = f"{base_domain}/api/olo/restaurants/{restaurant_id}/menu"
            endpoints.append(olo_menu_url)
            logger.info(f"Generated OLO API endpoint: {olo_menu_url}")
            
            # Alternative OLO formats
            alt_formats = [
                f"{base_domain}/api/restaurants/{restaurant_id}/menu",
                f"{base_domain}/api/v1/restaurants/{restaurant_id}/menu",
                f"{base_domain}/api/v2/restaurants/{restaurant_id}/menu",
                f"{base_domain}/olo/restaurants/{restaurant_id}/menu",
            ]
            endpoints.extend(alt_formats)
        
        # Pattern 4: Check for known OLO domains/subdomains
        olo_domains = ['olo.com', 'olocdn.net', 'olostorage']
        for domain in olo_domains:
            if domain in page_content.lower():
                logger.info(f"OLO platform detected via {domain}")
                # Try to extract full URLs
                domain_pattern = rf'(https?://[^"\'\s]*{re.escape(domain)}[^"\'\s]*)'
                matches = re.findall(domain_pattern, page_content, re.IGNORECASE)
                endpoints.extend(matches)
        
        # Pattern 5: Bubba's 33 specific - known restaurant ID
        if 'bubbas33' in base_url.lower() or 'bubba' in page_content.lower():
            logger.info("Bubba's 33 detected - adding known OLO endpoint")
            # Known working endpoint for Bubba's 33
            endpoints.append(f"{base_domain}/api/olo/restaurants/236820/menu")
        
        return list(set(endpoints))
    
    def _validate_and_extract_api_menu(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and extract menu data from API response"""
        
        if not isinstance(api_data, dict):
            return None
        
        menu_data = {'items': [], 'categories': {}}
        
        # Common API response patterns
        data_paths = [
            # Direct structure
            ['items'], ['menu', 'items'], ['data', 'items'], ['menuItems'], 
            ['products'], ['menu', 'products'], ['data', 'products'],
            # Nested structures
            ['data', 'menu', 'items'], ['response', 'data', 'items'],
            ['result', 'items'], ['menu'], ['data']
        ]
        
        items_found = False
        
        for path in data_paths:
            try:
                current = api_data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    # Successfully navigated the path
                    if isinstance(current, list) and len(current) > 0:
                        # Extract items from list
                        for item in current:
                            if isinstance(item, dict):
                                extracted_item = self._extract_item_from_api_data(item)
                                if extracted_item:
                                    menu_data['items'].append(extracted_item)
                                    items_found = True
                        
                        if items_found:
                            break
                    elif isinstance(current, dict):
                        # Check if this dict contains menu structure
                        for key, value in current.items():
                            if isinstance(value, list) and len(value) > 0:
                                for item in value:
                                    if isinstance(item, dict):
                                        extracted_item = self._extract_item_from_api_data(item)
                                        if extracted_item:
                                            menu_data['items'].append(extracted_item)
                                            items_found = True
                                
                                if items_found:
                                    # Also extract category name
                                    category_name = key.replace('_', ' ').title()
                                    menu_data['categories'][category_name] = len([i for i in menu_data['items'] if not i.get('category')])
                                    # Add category to items
                                    for item in menu_data['items']:
                                        if not item.get('category'):
                                            item['category'] = category_name
            except Exception:
                continue
        
        return menu_data if items_found and len(menu_data['items']) >= 3 else None
    
    def _extract_olo_menu(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract menu data specifically from OLO API response format.
        
        OLO typically returns data in this structure:
        {
            "categories": [
                {
                    "id": 123,
                    "name": "Appetizers",
                    "products": [
                        {
                            "id": 456,
                            "name": "Buffalo Wings",
                            "description": "...",
                            "baseprice": 12.99,
                            "cost": 12.99,
                            "images": [...],
                            "optiongroups": [...],
                            "availability": {...}
                        }
                    ]
                }
            ]
        }
        """
        menu_data = {'items': [], 'categories': {}}
        
        if not isinstance(api_data, dict):
            logger.warning("OLO API data is not a dictionary")
            return None
        
        # Find categories array - OLO uses various key names
        categories_keys = ['categories', 'menu', 'menuCategories', 'data', 'items']
        categories = None
        
        for key in categories_keys:
            if key in api_data:
                potential_categories = api_data[key]
                if isinstance(potential_categories, list) and len(potential_categories) > 0:
                    # Check if this looks like OLO categories (has name and products)
                    first_item = potential_categories[0]
                    if isinstance(first_item, dict) and ('name' in first_item or 'products' in first_item):
                        categories = potential_categories
                        logger.info(f"Found OLO categories under key '{key}' with {len(categories)} categories")
                        break
        
        if not categories:
            # Try nested paths
            nested_paths = [
                ['data', 'categories'],
                ['menu', 'categories'],
                ['response', 'categories'],
                ['result', 'categories'],
            ]
            for path in nested_paths:
                current = api_data
                try:
                    for key in path:
                        current = current[key]
                    if isinstance(current, list) and len(current) > 0:
                        categories = current
                        logger.info(f"Found OLO categories at nested path {path}")
                        break
                except (KeyError, TypeError):
                    continue
        
        if not categories:
            logger.warning("Could not find OLO categories in API response")
            return None
        
        # Process each category
        for category in categories:
            if not isinstance(category, dict):
                continue
            
            # Extract category name
            category_name = category.get('name') or category.get('displayName') or category.get('title') or 'Unknown Category'
            category_name = str(category_name).strip()
            
            # Initialize category in menu_data
            if category_name not in menu_data['categories']:
                menu_data['categories'][category_name] = []
            
            # Find products in category - OLO uses various key names
            products_keys = ['products', 'items', 'menuItems', 'choices', 'options']
            products = None
            
            for key in products_keys:
                if key in category and isinstance(category[key], list):
                    products = category[key]
                    break
            
            if not products:
                # Category might directly be a list of items
                continue
            
            # Process each product
            for product in products:
                if not isinstance(product, dict):
                    continue
                
                item = self._extract_olo_product(product, category_name)
                if item:
                    menu_data['items'].append(item)
                    menu_data['categories'][category_name].append(item['name'])
        
        total_items = len(menu_data['items'])
        total_categories = len([c for c in menu_data['categories'] if menu_data['categories'][c]])
        
        # Check if prices were found
        items_with_prices = sum(1 for item in menu_data['items'] if item.get('price'))
        
        # Add metadata about the extraction
        menu_data['_extraction_info'] = {
            'source': 'olo_api',
            'total_items': total_items,
            'total_categories': total_categories,
            'items_with_prices': items_with_prices,
        }
        
        # Note about dynamic pricing if no prices found
        if items_with_prices == 0 and total_items > 0:
            menu_data['_extraction_info']['price_note'] = 'OLO dynamic pricing - prices not in API (require store location)'
            menu_data['_extraction_info']['price_status'] = 'unavailable'
            logger.info(f"OLO extraction complete: {total_items} items in {total_categories} categories (no prices from API)")
        else:
            logger.info(f"OLO extraction complete: {total_items} items in {total_categories} categories ({items_with_prices} with prices)")
        
        return menu_data if total_items > 0 else None
    
    def _enrich_olo_with_dom_prices(self, menu_data: Dict[str, Any], menu_url: str) -> Dict[str, Any]:
        """
        Enrich OLO menu data with prices scraped from the DOM.
        
        OLO API returns menu structure without prices (dynamic pricing).
        This method uses Selenium to render the menu page and extract prices
        from the DOM, then matches them to OLO items by name.
        
        Note: Many OLO-powered sites (like Bubba's 33) require store location
        selection before prices are shown. This method works best on sites
        that display prices directly on the menu page.
        """
        if not menu_data or not menu_data.get('items'):
            return menu_data
        
        # Check if we already have prices
        items_with_prices = sum(1 for item in menu_data['items'] if item.get('price'))
        if items_with_prices > len(menu_data['items']) * 0.5:
            logger.info(f"Already have {items_with_prices} prices, skipping DOM enrichment")
            return menu_data
        
        logger.info(f"Attempting to enrich {len(menu_data['items'])} OLO items with DOM prices...")
        
        try:
            import time
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import undetected_chromedriver as uc
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = None
            try:
                driver = uc.Chrome(options=options)
                driver.get(menu_url)
                
                # Wait for page to load
                time.sleep(5)
                
                # Try to wait for menu items to appear
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='price'], [class*='cost'], [class*='menu-item']"))
                    )
                except:
                    pass
                
                time.sleep(2)  # Additional wait for dynamic content
                
                # Extract price data from DOM
                dom_prices = driver.execute_script("""
                    const priceData = [];
                    const pricePattern = /\\$\\d+(?:\\.\\d{2})?/g;
                    
                    // Method 1: Look for elements with price classes
                    const priceSelectors = [
                        '[class*="price"]',
                        '[class*="cost"]',
                        '[class*="amount"]',
                        '[data-price]',
                        '.menu-item-price',
                        '.product-price'
                    ];
                    
                    // Method 2: Look for menu item containers with name and price
                    const itemContainers = document.querySelectorAll(
                        '.menu-item, .product-item, .food-item, ion-item, ion-card, ' +
                        '[class*="menu-item"], [class*="product"], [class*="item-card"]'
                    );
                    
                    itemContainers.forEach(container => {
                        const text = container.textContent || '';
                        const prices = text.match(pricePattern);
                        
                        if (prices && prices.length > 0) {
                            // Try to find the item name
                            const nameSelectors = ['h1', 'h2', 'h3', 'h4', '.name', '.title', '[class*="name"]', '[class*="title"]'];
                            let name = null;
                            
                            for (const sel of nameSelectors) {
                                const nameEl = container.querySelector(sel);
                                if (nameEl && nameEl.textContent.trim().length > 2) {
                                    name = nameEl.textContent.trim();
                                    break;
                                }
                            }
                            
                            // If no name element, try to extract from text
                            if (!name) {
                                // Remove price from text and use first part as name
                                const cleanText = text.replace(pricePattern, '').trim();
                                const lines = cleanText.split('\\n').filter(l => l.trim().length > 2);
                                if (lines.length > 0) {
                                    name = lines[0].trim().substring(0, 100);
                                }
                            }
                            
                            if (name && name.length > 2 && name.length < 120) {
                                priceData.push({
                                    name: name,
                                    price: prices[0],  // Use first price found
                                    allPrices: prices
                                });
                            }
                        }
                    });
                    
                    // Method 3: Also try to find prices near text elements
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach(el => {
                        if (el.children.length === 0) {  // Leaf elements only
                            const text = el.textContent || '';
                            const prices = text.match(pricePattern);
                            if (prices && text.length < 200) {
                                // Look for nearby name
                                let parent = el.parentElement;
                                for (let i = 0; i < 5 && parent; i++) {
                                    const parentText = parent.textContent || '';
                                    if (parentText.length > text.length && parentText.length < 500) {
                                        const nameMatch = parentText.replace(pricePattern, '').trim();
                                        if (nameMatch.length > 3 && nameMatch.length < 100) {
                                            const exists = priceData.some(p => 
                                                p.name.toLowerCase().includes(nameMatch.toLowerCase().substring(0, 20))
                                            );
                                            if (!exists) {
                                                priceData.push({
                                                    name: nameMatch.split('\\n')[0].substring(0, 80),
                                                    price: prices[0],
                                                    source: 'leaf_element'
                                                });
                                            }
                                            break;
                                        }
                                    }
                                    parent = parent.parentElement;
                                }
                            }
                        }
                    });
                    
                    // Deduplicate by name
                    const seen = new Set();
                    const unique = [];
                    priceData.forEach(item => {
                        const key = item.name.toLowerCase().substring(0, 30);
                        if (!seen.has(key)) {
                            seen.add(key);
                            unique.push(item);
                        }
                    });
                    
                    return unique;
                """)
                
                logger.info(f"DOM price extraction found {len(dom_prices)} price entries")
                
                if not dom_prices:
                    logger.warning("No prices found in DOM")
                    return menu_data
                
                # Build a lookup dict for fuzzy matching
                price_lookup = {}
                for entry in dom_prices:
                    name = entry.get('name', '').lower().strip()
                    price = entry.get('price', '')
                    if name and price:
                        # Add variations for matching
                        price_lookup[name] = price
                        # Also add shortened version
                        if len(name) > 10:
                            price_lookup[name[:10]] = price
                
                # Match prices to OLO items
                prices_matched = 0
                for item in menu_data['items']:
                    if item.get('price'):  # Already has price
                        continue
                    
                    item_name = item.get('name', '').lower().strip()
                    
                    # Try exact match first
                    if item_name in price_lookup:
                        item['price'] = price_lookup[item_name]
                        prices_matched += 1
                        continue
                    
                    # Try partial matches
                    matched = False
                    for dom_name, dom_price in price_lookup.items():
                        # Check if names are similar (one contains the other)
                        if len(dom_name) > 5 and len(item_name) > 5:
                            if dom_name in item_name or item_name in dom_name:
                                item['price'] = dom_price
                                prices_matched += 1
                                matched = True
                                break
                            # Check word overlap
                            dom_words = set(dom_name.split())
                            item_words = set(item_name.split())
                            overlap = dom_words & item_words
                            if len(overlap) >= 2 or (len(overlap) >= 1 and len(dom_words) <= 2):
                                item['price'] = dom_price
                                prices_matched += 1
                                matched = True
                                break
                
                logger.info(f"DOM price enrichment: matched {prices_matched} prices to OLO items")
                
                # Update metadata
                if '_extraction_info' in menu_data:
                    menu_data['_extraction_info']['dom_prices_found'] = len(dom_prices)
                    menu_data['_extraction_info']['dom_prices_matched'] = prices_matched
                    menu_data['_extraction_info']['items_with_prices'] = sum(1 for item in menu_data['items'] if item.get('price'))
                    if prices_matched > 0:
                        menu_data['_extraction_info']['price_source'] = 'dom_enriched'
                
                return menu_data
                
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"DOM price enrichment failed: {e}")
            return menu_data
    
    def _extract_olo_product(self, product: Dict[str, Any], category_name: str) -> Dict[str, Any]:
        """Extract a single product from OLO API format"""
        
        # Extract name - OLO uses various field names
        name = None
        name_fields = ['name', 'displayName', 'title', 'productName', 'itemName']
        for field in name_fields:
            if field in product and product[field]:
                name = str(product[field]).strip()
                break
        
        if not name or len(name) < 2:
            return None
        
        # Extract price - OLO uses baseprice, cost, price
        # Note: OLO's /menu endpoint often returns cost=0 because prices are dynamic
        # and require a specific store location to be selected
        price = None
        price_fields = ['baseprice', 'basePrice', 'cost', 'price', 'amount', 'unitPrice']
        for field in price_fields:
            if field in product and product[field] is not None:
                price_val = product[field]
                if isinstance(price_val, (int, float)):
                    # Skip zero prices (OLO dynamic pricing)
                    if price_val == 0:
                        continue
                    # OLO sometimes stores prices in cents
                    if price_val > 1000:  # Likely in cents
                        price = price_val / 100
                    else:
                        price = float(price_val)
                elif isinstance(price_val, str):
                    try:
                        cleaned = price_val.replace('$', '').replace(',', '').strip()
                        if cleaned and float(cleaned) > 0:
                            price = float(cleaned)
                    except ValueError:
                        continue
                if price and price > 0:
                    break
        
        # Extract description
        description = ''
        desc_fields = ['description', 'desc', 'details', 'shortDescription', 'longDescription']
        for field in desc_fields:
            if field in product and product[field]:
                description = str(product[field]).strip()
                break
        
        # Extract image URL
        image_url = None
        if 'images' in product and isinstance(product['images'], list) and product['images']:
            first_image = product['images'][0]
            if isinstance(first_image, dict):
                image_url = first_image.get('url') or first_image.get('uri') or first_image.get('src')
            elif isinstance(first_image, str):
                image_url = first_image
        elif 'image' in product:
            img = product['image']
            if isinstance(img, dict):
                image_url = img.get('url') or img.get('uri') or img.get('src')
            elif isinstance(img, str):
                image_url = img
        elif 'imageUrl' in product:
            image_url = product['imageUrl']
        
        # Extract modifiers/options count (for complexity indication)
        modifiers_count = 0
        modifier_fields = ['optiongroups', 'modifiers', 'options', 'choices']
        for field in modifier_fields:
            if field in product and isinstance(product[field], list):
                modifiers_count = len(product[field])
                break
        
        # Extract availability
        available = True
        if 'availability' in product and isinstance(product['availability'], dict):
            available = product['availability'].get('available', True)
        elif 'isAvailable' in product:
            available = bool(product['isAvailable'])
        elif 'available' in product:
            available = bool(product['available'])
        
        # Build the menu item
        item = {
            'name': name,
            'price': f"${price:.2f}" if price else '',
            'description': description[:500] if description else '',  # Limit description length
            'category': category_name,
            'available': available,
        }
        
        # Add optional fields if present
        if image_url:
            item['image_url'] = image_url
        if modifiers_count > 0:
            item['has_modifiers'] = True
            item['modifiers_count'] = modifiers_count
        
        # Add OLO-specific IDs if present
        if 'id' in product:
            item['olo_product_id'] = product['id']
        
        return item

    def _extract_item_from_api_data(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized menu item from API item data"""
        
        if not isinstance(item_data, dict):
            return None
        
        # Common field mappings
        name_fields = ['name', 'title', 'itemName', 'productName', 'dishName']
        price_fields = ['price', 'cost', 'amount', 'basePrice', 'unitPrice']
        desc_fields = ['description', 'desc', 'details', 'summary', 'info']
        
        name = None
        price = None
        description = ''
        
        # Extract name
        for field in name_fields:
            if field in item_data and item_data[field]:
                name = str(item_data[field]).strip()
                break
        
        # Extract price
        for field in price_fields:
            if field in item_data and item_data[field] is not None:
                price_val = item_data[field]
                if isinstance(price_val, (int, float)):
                    price = f"${price_val:.2f}"
                elif isinstance(price_val, str) and price_val.strip():
                    price = price_val.strip()
                break
        
        # Extract description
        for field in desc_fields:
            if field in item_data and item_data[field]:
                description = str(item_data[field]).strip()
                break
        
        # Validate extracted data
        if name and len(name) >= 3 and len(name) <= 100:
            return {
                'name': name,
                'price': price or '',
                'description': description
            }
        
        return None
    
    def _discover_js_api_endpoints(self, base_url: str) -> List[str]:
        """Discover API endpoints by monitoring network requests in browser"""
        endpoints = []
        
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            import json
            
            logger.info(f"Starting dynamic API discovery for: {base_url}")
            
            # Use the orchestrator's selenium driver if available
            response = self._get_with_orchestrator_bypass(base_url)
            if hasattr(response, 'driver') and response.driver:
                driver = response.driver
            else:
                # Fallback: create temporary driver
                from src.bypass.strategies.selenium_stealth import SeleniumStealthStrategy
                strategy = SeleniumStealthStrategy(max_retries=1, timeout=30)
                temp_response = strategy.get(base_url)
                if not hasattr(temp_response, 'driver'):
                    return endpoints
                driver = temp_response.driver
            
            # Enable logging for network requests
            logs_available = False
            try:
                # Try to get network logs
                driver.execute_script("console.log('Testing console access');")
                logs_available = True
            except Exception:
                pass
            
            if logs_available:
                # Method 1: Monitor XHR/Fetch requests through JavaScript injection
                monitor_script = """
                window.apiEndpoints = [];
                
                // Override XMLHttpRequest
                const originalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    const xhr = new originalXHR();
                    const originalOpen = xhr.open;
                    xhr.open = function(method, url) {
                        if (url.includes('menu') || url.includes('food') || url.includes('item') || 
                            url.includes('api') || url.includes('data') || url.includes('product')) {
                            window.apiEndpoints.push({method: method, url: url, type: 'xhr'});
                        }
                        return originalOpen.apply(this, arguments);
                    };
                    return xhr;
                };
                
                // Override fetch
                const originalFetch = window.fetch;
                window.fetch = function(input, init) {
                    const url = typeof input === 'string' ? input : input.url;
                    if (url.includes('menu') || url.includes('food') || url.includes('item') || 
                        url.includes('api') || url.includes('data') || url.includes('product')) {
                        window.apiEndpoints.push({method: (init && init.method) || 'GET', url: url, type: 'fetch'});
                    }
                    return originalFetch.apply(this, arguments);
                };
                """
                
                driver.execute_script(monitor_script)
                
                # Wait for page interactions and API calls
                time.sleep(3)
                
                # Try to trigger menu loading by clicking menu-related elements
                try:
                    menu_selectors = [
                        "[data-cy*='menu']", "[class*='menu']", "[id*='menu']",
                        "[data-cy*='food']", "[class*='food']", "[id*='food']",
                        ".category", ".menu-category", ".food-category",
                        "button[data-test*='menu']", "a[href*='menu']"
                    ]
                    
                    for selector in menu_selectors[:3]:  # Try first 3 selectors
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                driver.execute_script("arguments[0].click();", elements[0])
                                time.sleep(1)
                                break
                        except Exception:
                            continue
                            
                except Exception:
                    pass
                
                # Wait for additional API calls
                time.sleep(2)
                
                # Extract discovered endpoints
                discovered = driver.execute_script("return window.apiEndpoints || [];")
                
                for endpoint_info in discovered:
                    url = endpoint_info.get('url', '')
                    if url:
                        # Convert relative URLs to absolute
                        if url.startswith('/'):
                            url = urljoin(base_url, url)
                        elif not url.startswith(('http://', 'https://')):
                            url = urljoin(base_url, url)
                        
                        endpoints.append(url)
                        logger.info(f"Discovered API endpoint: {url} (method: {endpoint_info.get('method', 'unknown')})")
            
            # Method 2: Look for API calls in page source and JavaScript
            try:
                page_source = driver.page_source
                
                # Extract API URLs from JavaScript code
                js_api_patterns = [
                    r"['\"]([^'\"]*(?:api|data|rest)[^'\"]*(?:menu|food|item|product)[^'\"]*)['\"]",
                    r"['\"]([^'\"]*(?:menu|food|item|product)[^'\"]*(?:api|data|rest)[^'\"]*)['\"]",
                    r"fetch\s*\(['\"]([^'\"]+)['\"]\)",
                    r"\$\.(?:get|post)\(['\"]([^'\"]+)['\"]\)",
                    r"axios\.(?:get|post)\(['\"]([^'\"]+)['\"]\)"
                ]
                
                for pattern in js_api_patterns:
                    matches = re.findall(pattern, page_source, re.IGNORECASE)
                    for match in matches:
                        if any(keyword in match.lower() for keyword in ['menu', 'food', 'item', 'product', 'api']):
                            if match.startswith('/'):
                                url = urljoin(base_url, match)
                            elif match.startswith(('http://', 'https://')):
                                url = match
                            else:
                                continue
                            
                            endpoints.append(url)
                            logger.debug(f"Found API pattern in JS: {url}")
            
            except Exception as e:
                logger.debug(f"JavaScript API pattern extraction failed: {e}")
            
        except Exception as e:
            logger.warning(f"Dynamic API discovery failed: {e}")
        
        return list(set(endpoints))
    
    def _discover_js_api_endpoints(self, base_url: str) -> List[str]:
        """Discover API endpoints by monitoring network requests in browser"""
        endpoints = []
        
        try:
            import time
            logger.info(f"Starting dynamic API discovery for: {base_url}")
            
            # Get page with selenium to monitor network requests
            response = self._get_with_orchestrator_bypass(base_url)
            if hasattr(response, 'driver') and response.driver:
                driver = response.driver
                
                # Method 1: Monitor network requests through JavaScript injection
                monitor_script = """
                window.discoveredEndpoints = [];
                
                // Override XMLHttpRequest
                const originalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    const xhr = new originalXHR();
                    const originalOpen = xhr.open;
                    xhr.open = function(method, url) {
                        if (url && (url.includes('menu') || url.includes('food') || url.includes('item') || 
                            url.includes('api') || url.includes('data') || url.includes('product'))) {
                            window.discoveredEndpoints.push({method: method, url: url, type: 'xhr'});
                        }
                        return originalOpen.apply(this, arguments);
                    };
                    return xhr;
                };
                
                // Override fetch
                const originalFetch = window.fetch;
                window.fetch = function(input, init) {
                    const url = typeof input === 'string' ? input : (input.url || '');
                    if (url && (url.includes('menu') || url.includes('food') || url.includes('item') || 
                        url.includes('api') || url.includes('data') || url.includes('product'))) {
                        window.discoveredEndpoints.push({method: (init && init.method) || 'GET', url: url, type: 'fetch'});
                    }
                    return originalFetch.apply(this, arguments);
                };
                """
                
                driver.execute_script(monitor_script)
                
                # Wait for initial page load and API calls
                time.sleep(3)
                
                # Try to trigger menu loading by interacting with menu elements
                try:
                    menu_selectors = [
                        "[data-cy*='menu']", "[class*='menu']", "[id*='menu']",
                        ".menu-category", ".category", ".nav-menu",
                        "button[data-test*='menu']", "a[href*='menu']"
                    ]
                    
                    for selector in menu_selectors[:3]:  # Try first 3 selectors
                        try:
                            elements = driver.find_elements("css selector", selector)
                            if elements:
                                driver.execute_script("arguments[0].click();", elements[0])
                                time.sleep(1.5)
                                break
                        except Exception:
                            continue
                            
                except Exception:
                    pass
                
                # Wait for API calls triggered by interactions
                time.sleep(3)
                
                # Extract discovered endpoints
                discovered = driver.execute_script("return window.discoveredEndpoints || [];")
                
                for endpoint_info in discovered:
                    url = endpoint_info.get('url', '')
                    if url:
                        # Convert relative URLs to absolute
                        if url.startswith('/'):
                            url = urljoin(base_url, url)
                        elif not url.startswith(('http://', 'https://')):
                            url = urljoin(base_url, url)
                        
                        endpoints.append(url)
                        logger.info(f"Discovered API endpoint: {url} (method: {endpoint_info.get('method', 'GET')})")
                
                # Method 2: Extract API patterns from page source
                try:
                    page_source = driver.page_source
                    
                    # Look for API URLs in JavaScript
                    js_api_patterns = [
                        r"['\"]([^'\"]*(?:api|data|rest)[^'\"]*(?:menu|food|item|product)[^'\"]*)['\"]",
                        r"['\"]([^'\"]*(?:menu|food|item|product)[^'\"]*(?:api|data|rest)[^'\"]*)['\"]",
                        r"fetch\s*\(['\"]([^'\"]+)['\"]\)",
                        r"axios\.(?:get|post)\(['\"]([^'\"]+)['\"]\)"
                    ]
                    
                    for pattern in js_api_patterns:
                        matches = re.findall(pattern, page_source, re.IGNORECASE)
                        for match in matches:
                            if any(keyword in match.lower() for keyword in ['menu', 'food', 'item', 'product', 'api']):
                                if match.startswith('/'):
                                    url = urljoin(base_url, match)
                                elif match.startswith(('http://', 'https://')):
                                    url = match
                                else:
                                    continue
                                
                                endpoints.append(url)
                                logger.debug(f"Found API pattern in JS: {url}")
                
                except Exception as e:
                    logger.debug(f"JS pattern extraction failed: {e}")
            
        except Exception as e:
            logger.warning(f"Dynamic API discovery failed: {e}")
        
        return list(set(endpoints))
    
    def _extract_js_menu_data(self, menu_url: str) -> Dict[str, Any]:
        """Extract menu data directly from JavaScript execution and DOM"""
        
        try:
            logger.info(f"Attempting JavaScript menu data extraction from: {menu_url}")
            
            response = self._get_with_orchestrator_bypass(menu_url)
            if hasattr(response, 'driver') and response.driver:
                driver = response.driver
                
                # Wait for JavaScript to fully load menu data
                time.sleep(5)
                
                # Enhanced DOM-based menu extraction with JavaScript execution
                extraction_script = """
                function extractMenuData() {
                    const menuData = { items: [], categories: [] };
                    
                    // Look for Angular components or React elements
                    const menuContainers = document.querySelectorAll(
                        '[data-cy*="menu"], [class*="menu"], [class*="food"], ' +
                        '.menu-items, .food-items, .menu-container, .items-container, ' +
                        '[ng-reflect-router-link*="menu"], [data-testid*="menu"]'
                    );
                    
                    let foundItems = false;
                    
                    menuContainers.forEach(container => {
                        // Look for item elements
                        const itemSelectors = [
                            '[data-cy*="item"], .menu-item, .food-item, .item, .product',
                            '.card, .menu-card, .food-card',
                            '[class*="dish"], [class*="meal"]',
                            'li[class*="menu"], li[class*="food"]'
                        ];
                        
                        itemSelectors.forEach(selector => {
                            const items = container.querySelectorAll(selector);
                            
                            items.forEach(item => {
                                const nameSelectors = ['.name', '.title', 'h1', 'h2', 'h3', 'h4', '.item-name', '.dish-name', '.product-name'];
                                const priceSelectors = ['.price', '.cost', '.amount', '[class*="price"]', '[data-cy*="price"]'];
                                const descSelectors = ['.description', '.desc', '.details', 'p', '.summary'];
                                
                                let nameEl = null;
                                let priceEl = null;
                                let descEl = null;
                                
                                // Find name element
                                for (let nameSelector of nameSelectors) {
                                    nameEl = item.querySelector(nameSelector);
                                    if (nameEl && nameEl.textContent && nameEl.textContent.trim().length > 2) {
                                        break;
                                    }
                                }
                                
                                // Find price element
                                for (let priceSelector of priceSelectors) {
                                    priceEl = item.querySelector(priceSelector);
                                    if (priceEl && priceEl.textContent && /[$£€¥]|\d+\.\d{2}/.test(priceEl.textContent)) {
                                        break;
                                    }
                                }
                                
                                // Find description element
                                for (let descSelector of descSelectors) {
                                    descEl = item.querySelector(descSelector);
                                    if (descEl && descEl.textContent && descEl.textContent.trim().length > 10) {
                                        break;
                                    }
                                }
                                
                                if (nameEl && nameEl.textContent.trim()) {
                                    const itemData = {
                                        name: nameEl.textContent.trim(),
                                        price: priceEl ? priceEl.textContent.trim() : '',
                                        description: descEl ? descEl.textContent.trim() : ''
                                    };
                                    
                                    // Validate item data
                                    if (itemData.name.length >= 3 && itemData.name.length <= 100) {
                                        menuData.items.push(itemData);
                                        foundItems = true;
                                    }
                                }
                            });
                        });
                    });
                    
                    // Extract categories
                    const categorySelectors = [
                        '.menu-category, .food-category, .category',
                        '[class*="category"] h1, [class*="category"] h2, [class*="category"] h3',
                        '.menu-section, .food-section',
                        '[data-cy*="category"]'
                    ];
                    
                    categorySelectors.forEach(selector => {
                        const categories = document.querySelectorAll(selector);
                        categories.forEach(cat => {
                            const text = cat.textContent ? cat.textContent.trim() : '';
                            if (text && text.length > 2 && text.length <= 50 && !menuData.categories.includes(text)) {
                                menuData.categories.push(text);
                            }
                        });
                    });
                    
                    console.log('Extracted menu data:', menuData);
                    return foundItems ? menuData : null;
                }
                
                return extractMenuData();
                """
                
                result = driver.execute_script(extraction_script)
                
                if result and isinstance(result, dict) and result.get('items'):
                    logger.info(f"Successfully extracted {len(result['items'])} menu items via JavaScript DOM extraction")
                    return result
        
        except Exception as e:
            logger.warning(f"JavaScript menu extraction failed: {e}")
        
        return {}

    def _extract_angular_spa_menu(self, menu_url: str) -> Dict[str, Any]:
        """
        Enhanced extraction specifically for Angular/Ionic SPAs like Bubba's 33.
        
        This method:
        1. Waits for Angular hydration to complete
        2. Monitors XHR/Fetch requests to capture API calls
        3. Extracts data from window state objects (__INITIAL_STATE__, etc.)
        4. Navigates through category buttons to load all menu data
        """
        try:
            import time
            logger.info(f"Starting Angular SPA extraction for: {menu_url}")
            
            response = self._get_with_orchestrator_bypass(menu_url)
            driver = None
            
            if hasattr(response, 'driver') and response.driver:
                driver = response.driver
            else:
                # Need to create a selenium driver for Angular SPA
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                try:
                    import undetected_chromedriver as uc
                    options = Options()
                    options.add_argument('--headless')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    driver = uc.Chrome(options=options)
                    driver.get(menu_url)
                except ImportError:
                    logger.warning("undetected_chromedriver not available")
                    return {}
            
            if not driver:
                return {}
            
            # === STEP 1: Wait for Angular hydration ===
            angular_ready_script = """
            return new Promise((resolve) => {
                // Check for Angular readiness
                function checkAngularReady() {
                    // Check for Angular 2+
                    if (window.ng && window.getAllAngularTestabilities) {
                        const testabilities = window.getAllAngularTestabilities();
                        if (testabilities.length > 0) {
                            const stable = testabilities.every(t => t.isStable());
                            if (stable) {
                                resolve({ready: true, framework: 'angular'});
                                return;
                            }
                        }
                    }
                    
                    // Check for Ionic
                    if (window.Ionic || document.querySelector('ion-app.hydrated')) {
                        resolve({ready: true, framework: 'ionic'});
                        return;
                    }
                    
                    // Check for generic SPA readiness (content loaded)
                    const menuElements = document.querySelectorAll('[class*="menu"], [class*="item"], [class*="product"]');
                    if (menuElements.length > 5) {
                        resolve({ready: true, framework: 'generic_spa'});
                        return;
                    }
                    
                    // Retry after delay
                    setTimeout(checkAngularReady, 500);
                }
                
                // Start checking after initial delay
                setTimeout(checkAngularReady, 1000);
                
                // Timeout after 15 seconds
                setTimeout(() => resolve({ready: false, timeout: true}), 15000);
            });
            """
            
            try:
                angular_status = driver.execute_script(angular_ready_script)
                logger.info(f"Angular SPA status: {angular_status}")
            except Exception as e:
                logger.warning(f"Angular readiness check failed: {e}")
                angular_status = {'ready': False}
            
            time.sleep(2)  # Additional wait for content
            
            # === STEP 2: Capture API endpoints from network monitoring ===
            network_capture_script = """
            // Set up network monitoring
            window.__capturedApiCalls = [];
            
            // Override XMLHttpRequest
            const originalXHR = window.XMLHttpRequest.prototype.open;
            window.XMLHttpRequest.prototype.open = function(method, url) {
                if (url && (url.includes('menu') || url.includes('olo') || 
                    url.includes('restaurant') || url.includes('api'))) {
                    window.__capturedApiCalls.push({
                        type: 'xhr', method: method, url: url, timestamp: Date.now()
                    });
                }
                return originalXHR.apply(this, arguments);
            };
            
            // Override fetch
            const originalFetch = window.fetch;
            window.fetch = function(input, init) {
                const url = typeof input === 'string' ? input : input.url;
                if (url && (url.includes('menu') || url.includes('olo') || 
                    url.includes('restaurant') || url.includes('api'))) {
                    window.__capturedApiCalls.push({
                        type: 'fetch', method: (init && init.method) || 'GET', 
                        url: url, timestamp: Date.now()
                    });
                }
                return originalFetch.apply(this, arguments);
            };
            
            return 'Network monitoring enabled';
            """
            
            try:
                driver.execute_script(network_capture_script)
            except Exception as e:
                logger.warning(f"Network monitoring setup failed: {e}")
            
            # === STEP 3: Extract data from window state objects ===
            state_extraction_script = """
            const stateData = {
                found: false,
                source: null,
                data: null,
                apiCalls: window.__capturedApiCalls || []
            };
            
            // Check for common state storage patterns
            const stateKeys = [
                '__INITIAL_STATE__',
                '__PRELOADED_STATE__',
                '__NUXT__',
                '__NEXT_DATA__',
                'initialState',
                'appState',
                '__APP_STATE__',
                'window.state'
            ];
            
            for (const key of stateKeys) {
                try {
                    const value = eval(key.startsWith('window.') ? key : 'window.' + key);
                    if (value && typeof value === 'object') {
                        // Look for menu data in the state
                        const stateStr = JSON.stringify(value);
                        if (stateStr.includes('menu') || stateStr.includes('categories') || 
                            stateStr.includes('products') || stateStr.includes('items')) {
                            stateData.found = true;
                            stateData.source = key;
                            stateData.data = value;
                            break;
                        }
                    }
                } catch (e) {
                    // Key doesn't exist, continue
                }
            }
            
            // Also try to find menu data in any window property
            if (!stateData.found) {
                for (const key of Object.keys(window)) {
                    try {
                        const value = window[key];
                        if (value && typeof value === 'object' && !Array.isArray(value)) {
                            const valStr = JSON.stringify(value).toLowerCase();
                            if (valStr.includes('menu') && valStr.includes('price') && 
                                (valStr.includes('categories') || valStr.includes('items'))) {
                                stateData.found = true;
                                stateData.source = 'window.' + key;
                                stateData.data = value;
                                break;
                            }
                        }
                    } catch (e) {
                        // Continue on error
                    }
                }
            }
            
            return stateData;
            """
            
            state_data = None
            try:
                state_data = driver.execute_script(state_extraction_script)
                if state_data and state_data.get('found'):
                    logger.info(f"Found state data in: {state_data.get('source')}")
            except Exception as e:
                logger.warning(f"State extraction failed: {e}")
            
            # === STEP 4: Navigate through categories to load all menu data ===
            category_navigation_script = """
            return new Promise(async (resolve) => {
                const allMenuItems = [];
                const categoriesFound = new Set();
                
                // Find category buttons/tabs
                const categorySelectors = [
                    'ion-segment-button',
                    '[class*="category"][class*="button"]',
                    '[class*="menu"][class*="tab"]',
                    '.category-button',
                    '.menu-category',
                    '[role="tab"]',
                    'button[class*="category"]',
                    '[data-category]'
                ];
                
                let categoryButtons = [];
                for (const selector of categorySelectors) {
                    const buttons = document.querySelectorAll(selector);
                    if (buttons.length > 0) {
                        categoryButtons = Array.from(buttons);
                        console.log(`Found ${buttons.length} category buttons with selector: ${selector}`);
                        break;
                    }
                }
                
                // Extract current visible items
                function extractCurrentItems() {
                    const items = [];
                    const itemSelectors = [
                        'ion-item', '.menu-item', '.food-item', '.product-item',
                        '[class*="menu-item"]', '[class*="product"]', 'ion-card'
                    ];
                    
                    for (const selector of itemSelectors) {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const text = el.textContent || '';
                            // Look for price pattern
                            const priceMatch = text.match(/\\$\\d+(?:\\.\\d{2})?/);
                            if (priceMatch && text.length > 10 && text.length < 500) {
                                const price = priceMatch[0];
                                let name = text.replace(/\\$\\d+(?:\\.\\d{2})?/g, '')
                                    .replace(/\\n+/g, ' ')
                                    .replace(/\\s+/g, ' ')
                                    .trim()
                                    .substring(0, 100);
                                
                                if (name.length >= 3) {
                                    items.push({ name, price, source: selector });
                                }
                            }
                        });
                        
                        if (items.length > 0) break;
                    }
                    
                    return items;
                }
                
                // Click each category and extract items
                for (let i = 0; i < Math.min(categoryButtons.length, 15); i++) {
                    const btn = categoryButtons[i];
                    const categoryName = btn.textContent?.trim() || `Category ${i+1}`;
                    
                    try {
                        btn.click();
                        categoriesFound.add(categoryName);
                        
                        // Wait for content to load
                        await new Promise(r => setTimeout(r, 1500));
                        
                        // Extract items
                        const items = extractCurrentItems();
                        items.forEach(item => {
                            item.category = categoryName;
                            allMenuItems.push(item);
                        });
                        
                        console.log(`Category "${categoryName}": found ${items.length} items`);
                        
                    } catch (e) {
                        console.log(`Error clicking category ${categoryName}: ${e}`);
                    }
                }
                
                // If no category buttons, just extract current items
                if (categoryButtons.length === 0) {
                    const items = extractCurrentItems();
                    allMenuItems.push(...items);
                }
                
                // Deduplicate
                const seen = new Set();
                const uniqueItems = allMenuItems.filter(item => {
                    const key = item.name.toLowerCase().substring(0, 30);
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                });
                
                resolve({
                    items: uniqueItems,
                    totalItems: uniqueItems.length,
                    categories: Array.from(categoriesFound),
                    categoryButtonsFound: categoryButtons.length
                });
            });
            """
            
            try:
                navigation_result = driver.execute_script(category_navigation_script)
                logger.info(f"Category navigation result: {navigation_result.get('totalItems', 0)} items from {len(navigation_result.get('categories', []))} categories")
            except Exception as e:
                logger.warning(f"Category navigation failed: {e}")
                navigation_result = {}
            
            # === Compile results ===
            menu_data = {'items': [], 'categories': {}}
            
            # Add items from navigation
            if navigation_result and navigation_result.get('items'):
                for item in navigation_result['items']:
                    menu_data['items'].append({
                        'name': item.get('name', ''),
                        'price': item.get('price', ''),
                        'category': item.get('category', 'Menu'),
                        'description': ''
                    })
                    
                    cat = item.get('category', 'Menu')
                    if cat not in menu_data['categories']:
                        menu_data['categories'][cat] = []
                    menu_data['categories'][cat].append(item.get('name', ''))
            
            # Add API endpoints for later use
            if state_data and state_data.get('apiCalls'):
                menu_data['_api_calls'] = state_data['apiCalls']
            
            total_items = len(menu_data['items'])
            total_cats = len(menu_data['categories'])
            
            logger.info(f"Angular SPA extraction complete: {total_items} items, {total_cats} categories")
            
            return menu_data if total_items > 0 else {}
            
        except Exception as e:
            logger.error(f"Angular SPA extraction failed: {e}")
            return {}

    def _extract_js_menu_with_navigation(self, menu_url: str) -> Dict[str, Any]:
        """Enhanced JavaScript extraction with multi-step navigation for sites like Bubba's 33"""
        if not hasattr(self, 'destroyer') or not self.destroyer:
            return {'success': False, 'error': 'CloudDestroyer not initialized'}
            
        try:
            logger.info(f"Attempting enhanced JavaScript extraction with navigation for: {menu_url}")
            
            # Get the page
            response = self.destroyer.get(menu_url)
            if not response or response.status_code != 200:
                return {'success': False, 'error': f'Failed to load page: {response.status_code if response else "No response"}'}
            
            # Use selenium to interact with dynamic content
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            import undetected_chromedriver as uc
            import time
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            driver = None
            try:
                driver = uc.Chrome(options=options)
                driver.get(menu_url)
                time.sleep(4)  # Wait for JS to load
                
                # First, try to find menu items on the current page
                menu_data = self._extract_menu_items_from_current_page(driver)
                
                # If no items found, try clicking "Order" or category buttons
                if menu_data.get('totalFound', 0) == 0:
                    logger.info("No items on main page, trying navigation...")
                    clicked_result = self._try_clicking_order_buttons(driver)
                    if clicked_result.get('success'):
                        time.sleep(4)  # Wait for navigation/loading
                        menu_data = self._extract_menu_items_from_current_page(driver)
                
                # If still no items, try clicking individual categories
                if menu_data.get('totalFound', 0) == 0:
                    logger.info("No items on order page, trying category navigation...")
                    category_results = self._try_category_by_category_extraction(driver)
                    if category_results.get('items'):
                        menu_data = category_results
                
                if menu_data.get('totalFound', 0) > 0:
                    return {
                        'success': True,
                        'items': menu_data['items'],
                        'total_items': menu_data['totalFound'],
                        'extraction_method': 'javascript_multi_step_navigation'
                    }
                else:
                    return {'success': False, 'error': 'No menu items found after trying multiple navigation approaches'}
                    
            except Exception as e:
                logger.error(f"JavaScript navigation extraction failed: {str(e)}")
                return {'success': False, 'error': f'JavaScript extraction failed: {str(e)}'}
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Menu data extraction with navigation failed: {str(e)}")
            return {'success': False, 'error': f'Menu data extraction failed: {str(e)}'}
    
    def _extract_menu_items_from_current_page(self, driver) -> Dict[str, Any]:
        """Extract menu items from the current page with enhanced Angular support"""
        import time
        
        # Wait for Angular to load
        time.sleep(2)
        
        # Try to wait for any loading indicators to disappear
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Wait for any ion-loading or loading spinners to disappear
            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ion-loading"))
            )
        except:
            pass
            
        time.sleep(1)  # Additional wait for content to render
        
        return driver.execute_script("""
            console.log('Starting enhanced menu item extraction...');
            
            // Wait for Angular/Ionic to finish loading
            function waitForContent(maxAttempts = 30) {
                let attempts = 0;
                return new Promise((resolve) => {
                    function check() {
                        attempts++;
                        const menuItemElements = document.querySelectorAll(
                            'ion-item, .menu-item, .food-item, .item, [class*="item"], ' +
                            '[class*="menu"], [class*="food"], [class*="product"]'
                        );
                        
                        if (menuItemElements.length > 10 || attempts >= maxAttempts) {
                            resolve();
                        } else {
                            setTimeout(check, 200);
                        }
                    }
                    check();
                });
            }
            
            // Enhanced price pattern that matches various formats
            const pricePattern = /\\$\\d+(?:\\.\\d{2})?|\\d+\\.\\d{2}\\s*\\$|price[:\\s]*\\$?\\d+/gi;
            
            const menuItems = [];
            const processedElements = new Set();
            
            // Look for structured menu items in Angular/Ionic components
            const potentialItemSelectors = [
                'ion-item',
                '.menu-item', 
                '.food-item',
                '.item-card',
                '.product-item',
                '[class*="menu-item"]',
                '[class*="food-item"]',
                '[class*="product"]',
                '.category-item',
                'ion-card'
            ];
            
            potentialItemSelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                console.log(`Checking ${selector}: found ${elements.length} elements`);
                
                elements.forEach(el => {
                    if (processedElements.has(el)) return;
                    processedElements.add(el);
                    
                    const text = el.textContent || '';
                    const html = el.innerHTML || '';
                    
                    // Check if this element or its children contain prices
                    const hasPriceInText = pricePattern.test(text);
                    const hasPriceInHTML = pricePattern.test(html);
                    
                    if ((hasPriceInText || hasPriceInHTML) && text.length > 8 && text.length < 800) {
                        // Extract price information
                        const priceMatches = text.match(pricePattern) || [];
                        
                        if (priceMatches.length > 0) {
                            const price = priceMatches[0];
                            
                            // Try to extract a clean item name
                            let itemName = text
                                .replace(pricePattern, '')  // Remove price
                                .replace(/^\\s*[\\d\\.\\$]+\\s*/, '')  // Remove leading numbers/prices
                                .replace(/\\s*[\\d\\.\\$]+\\s*$/, '')  // Remove trailing numbers/prices
                                .replace(/\\n+/g, ' ')  // Replace newlines with spaces
                                .replace(/\\s+/g, ' ')  // Normalize whitespace
                                .trim();
                            
                            // Clean up common unwanted text
                            itemName = itemName
                                .replace(/^(order|add to cart|select|choose|view|details?|more info)\\s*/i, '')
                                .replace(/\\s*(order|add to cart|select|choose|view|details?|more info)$/i, '')
                                .replace(/^\\d+\\.\\s*/, '')  // Remove leading numbers like "1. "
                                .trim();
                            
                            if (itemName.length >= 3 && itemName.length <= 120 && 
                                !/^\\s*[\\d\\.\\$\\s]+$/.test(itemName)) {  // Not just numbers and prices
                                
                                // Try to extract description from surrounding elements
                                let description = '';
                                const descEl = el.querySelector('.description, .desc, [class*="desc"]');
                                if (descEl) {
                                    description = descEl.textContent.trim();
                                }
                                
                                menuItems.push({
                                    name: itemName,
                                    price: price,
                                    description: description || text.substring(0, 300).trim(),
                                    category: 'Menu Item',
                                    source: selector,
                                    elementText: text.substring(0, 200)
                                });
                            }
                        }
                    }
                });
            });
            
            // Also try generic text-based extraction as fallback
            const allTextElements = Array.from(document.querySelectorAll('p, div, span, li, td, h1, h2, h3, h4, h5, h6'));
            
            allTextElements.forEach(el => {
                if (processedElements.has(el)) return;
                
                const text = el.textContent || '';
                if (pricePattern.test(text) && text.length > 10 && text.length < 300 && 
                    !text.toLowerCase().includes('total') && !text.toLowerCase().includes('subtotal')) {
                    
                    const priceMatches = text.match(pricePattern) || [];
                    if (priceMatches.length > 0) {
                        const price = priceMatches[0];
                        let itemName = text.replace(pricePattern, '').trim();
                        
                        if (itemName.length >= 3 && itemName.length <= 80 && 
                            !/^\\s*[\\d\\.\\$\\s]+$/.test(itemName)) {
                            
                            menuItems.push({
                                name: itemName,
                                price: price,
                                description: text.trim(),
                                category: 'Menu Item',
                                source: 'text-fallback'
                            });
                        }
                    }
                }
            });
            
            // Deduplicate items based on name similarity
            const uniqueItems = [];
            const seenNames = new Set();
            
            menuItems.forEach(item => {
                // Normalize name for comparison
                const normalizedName = item.name.toLowerCase()
                    .replace(/[^a-z0-9\\s]/g, '')
                    .replace(/\\s+/g, ' ')
                    .trim();
                
                if (!seenNames.has(normalizedName) && normalizedName.length > 2) {
                    seenNames.add(normalizedName);
                    uniqueItems.push(item);
                }
            });
            
            console.log(`Extracted ${uniqueItems.length} unique menu items`);
            
            return {
                items: uniqueItems,
                totalFound: uniqueItems.length,
                pageTitle: document.title,
                url: window.location.href,
                debug: {
                    totalElementsProcessed: processedElements.size,
                    rawItemsFound: menuItems.length
                }
            };
        """)
    
    def _try_clicking_order_buttons(self, driver) -> Dict[str, Any]:
        """Try clicking Order or menu-related buttons to navigate to menu page"""
        return driver.execute_script("""
            // Look for Order buttons or menu navigation
            const allClickable = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            
            const orderButtons = allClickable.filter(el => {
                const text = (el.textContent || '').toLowerCase();
                return text.includes('order') || text.includes('menu') || text.includes('order online');
            });
            
            if (orderButtons.length > 0) {
                const btn = orderButtons[0];
                console.log('Clicking order button:', btn.textContent);
                btn.click();
                return { success: true, clicked: btn.textContent.trim() };
            }
            
            return { success: false, reason: 'No order buttons found' };
        """)
    
    def _try_category_by_category_extraction(self, driver) -> Dict[str, Any]:
        """Try navigating to category-specific URLs to find menu items"""
        import time
        
        # Ensure we're on a menu page first and wait for full load
        current_url = driver.current_url
        logger.info(f"Category extraction called from URL: {current_url}")
        
        if '/menu' not in current_url:
            logger.info("Not on menu page, navigating to menu...")
            menu_url = current_url.replace(current_url.split('/')[-1], 'menu')
            if 'bubbas33.com' in current_url:
                menu_url = current_url.split('/')[0] + '//' + current_url.split('/')[2] + '/menu'
            driver.get(menu_url)
            time.sleep(8)  # Increased wait
        else:
            # Even if we're on the menu page, wait for Angular/React to fully load
            logger.info("Already on menu page, waiting for full load...")
            time.sleep(5)
        
        # Wait for specific elements to be present
        logger.info("Waiting for page elements to load...")
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            # Wait for menu content to be present
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete" and
                         len(d.find_elements(By.TAG_NAME, "a")) > 10
            )
            logger.info("Page elements loaded successfully")
        except Exception as e:
            logger.warning(f"Wait for elements failed: {e}, proceeding anyway")
            
        # Get available category URLs directly (like Bubba's 33 pattern)
        categories = driver.execute_script("""
            // Look for direct category navigation links
            const categoryLinks = Array.from(document.querySelectorAll('a')).filter(link => {
                const href = link.href || '';
                const text = (link.textContent || '').toLowerCase().trim();
                
                // Look for menu category patterns in URLs and text
                const hasMenuInUrl = href.includes('/menu/') && (href.includes('bubbas33.com') || href.includes(window.location.hostname) || link.getAttribute('href')?.startsWith('/menu/'));
                const hasCategory = /appetizer|wing|pizza|burger|pasta|salad|dinner|dessert|beverage|handhold|side|kid|meal|feast/i.test(text);
                
                return hasMenuInUrl && hasCategory && text.length > 3 && text.length < 50;
            });
            
            console.log('Found category URLs:', categoryLinks.length);
            console.log('Current page:', window.location.href);
            console.log('Hostname:', window.location.hostname);
            
            const categoryData = categoryLinks.map((link, i) => ({
                index: i,
                text: link.textContent.trim(),
                href: link.href,
                url: link.href
            }));
            
            categoryData.forEach((cat, i) => {
                if (i < 10) {
                    console.log(`Category ${i}: ${cat.text} -> ${cat.url}`);
                }
            });
            
            return categoryData;
        """)
        
        logger.info(f"JavaScript returned {len(categories)} categories from {driver.current_url}")
        for i, cat in enumerate(categories[:5]):
            logger.info(f"  Category {i}: {cat['text']} -> {cat['url']}")
        
        all_items = []
        successful_categories = 0
        
        logger.info(f"Found {len(categories)} potential category buttons")
        
        # Try navigating to category URLs directly
        for i, category in enumerate(categories[:5]):  # Try up to 5 categories
            try:
                logger.info(f"Trying category {i+1}: {category['text']} -> {category.get('url', 'No URL')}")
                
                # Navigate directly to the category URL if available
                if category.get('url'):
                    logger.info(f"Navigating to category URL: {category['url']}")
                    driver.get(category['url'])
                    
                    # Wait for Angular/Ionic to load
                    time.sleep(4)
                    
                    # Additional wait for Angular content to render
                    try:
                        # Wait for either menu items to appear OR a reasonable timeout
                        driver.execute_script("""
                            return new Promise((resolve) => {
                                let attempts = 0;
                                function checkContent() {
                                    attempts++;
                                    const hasContent = document.querySelectorAll('ion-item, .menu-item, .food-item').length > 0 ||
                                                     document.body.textContent.includes('$');
                                    if (hasContent || attempts > 20) {
                                        resolve(true);
                                    } else {
                                        setTimeout(checkContent, 300);
                                    }
                                }
                                checkContent();
                            });
                        """)
                    except Exception as e:
                        logger.warning(f"Error waiting for Angular content: {e}")
                    
                    # Extract items from this category page
                    category_items = self._extract_menu_items_from_current_page(driver)
                    if category_items.get('totalFound', 0) > 0:
                        logger.info(f"Found {category_items['totalFound']} items in category: {category['text']}")
                        for item in category_items['items']:
                            item['category'] = category['text']
                        all_items.extend(category_items['items'])
                        successful_categories += 1
                    else:
                        logger.info(f"No items found on category page: {category['url']}")
                        # Log some debug info
                        page_info = driver.execute_script("""
                            return {
                                title: document.title,
                                url: window.location.href,
                                bodyTextLength: document.body.textContent.length,
                                hasPrices: document.body.textContent.includes('$'),
                                ionItems: document.querySelectorAll('ion-item').length,
                                menuItems: document.querySelectorAll('.menu-item, .food-item').length
                            };
                        """)
                        logger.info(f"Page debug info: {page_info}")
                else:
                    logger.warning(f"No URL available for category: {category['text']}")
                
            except Exception as e:
                logger.warning(f"Failed to navigate to category {category['text']}: {e}")
                continue  # Skip failed categories
        
        logger.info(f"Successfully extracted from {successful_categories} categories, total items: {len(all_items)}")
        
        return {
            'items': all_items,
            'totalFound': len(all_items),
            'categoriesProcessed': successful_categories
        }

    def _score_menu_content(self, content: str, url: str) -> int:
        """Comprehensive menu content scoring with 7+ item validation"""
        if not content:
            return 0
            
        content_lower = content.lower()
        score = 0
        
        # URL-based scoring (0-5 points)
        url_lower = url.lower()
        if '/menu' in url_lower: score += 4
        if '/food' in url_lower: score += 3
        if '/order' in url_lower: score += 3
        if '/dining' in url_lower: score += 2
        if '/eat' in url_lower: score += 2
        
        # Title and heading indicators (0-6 points)
        title_indicators = [
            ('menu', 3), ('our menu', 4), ('food menu', 4), 
            ('restaurant menu', 4), ('order online', 3), ('takeout', 2)
        ]
        for indicator, points in title_indicators:
            if indicator in content_lower:
                score += points
                break  # Only count the highest scoring title indicator
        
        # Food category detection (0-12 points) - Critical for success validation
        food_categories = [
            'appetizer', 'starter', 'entree', 'main course', 'dessert', 
            'beverage', 'drink', 'burger', 'pizza', 'sandwich', 'salad', 
            'pasta', 'steak', 'chicken', 'seafood', 'soup', 'wings', 
            'nachos', 'tacos', 'burrito', 'wrap', 'fries', 'sides'
        ]
        
        category_count = sum(1 for category in food_categories if category in content_lower)
        score += min(category_count * 2, 12)  # Up to 12 points for categories
        
        # Price pattern detection (0-15 points) - Essential for success threshold
        import re
        price_patterns = [
            r'\$\d+\.\d{2}',  # $12.99
            r'\$\d+',         # $12
            r'\d+\.\d{2}\s*\$', # 12.99$
            r'price[:\s]*\$\d+',  # Price: $12
            r'\$\d+[\s]*-[\s]*\$\d+'  # $10 - $15
        ]
        
        total_price_matches = 0
        for pattern in price_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_price_matches += len(matches)
        
        # Award points based on price pattern density
        if total_price_matches >= 15: score += 15  # Excellent price coverage
        elif total_price_matches >= 10: score += 12
        elif total_price_matches >= 7: score += 10   # Meets success threshold
        elif total_price_matches >= 5: score += 8
        elif total_price_matches >= 3: score += 5
        elif total_price_matches >= 1: score += 3
        
        # Menu item structure detection (0-8 points)
        item_structure_patterns = [
            r'[a-zA-Z\s]{10,50}[\s]*\$\d+',  # Item name followed by price
            r'<h[3-6][^>]*>[^<]+</h[3-6]>[\s\S]*?\$\d+',  # Header + price
            r'class=["\'][^"\'>]*item[^"\'>]*["\'][\s\S]*?\$\d+'  # Item class + price
        ]
        
        structured_items = 0
        for pattern in item_structure_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            structured_items += len(matches)
        
        # Success threshold validation: 7+ structured menu items
        if structured_items >= 10: score += 8
        elif structured_items >= 7: score += 6   # Meets minimum success threshold
        elif structured_items >= 5: score += 4
        elif structured_items >= 3: score += 2
        elif structured_items >= 1: score += 1
        
        # Content quality indicators (0-5 points)
        quality_indicators = ['description', 'ingredient', 'served with', 'choice of', 'add-on']
        quality_count = sum(1 for indicator in quality_indicators if indicator in content_lower)
        score += min(quality_count, 5)
        
        # Negative indicators (subtract points)
        negative_indicators = [
            ('about us', -3), ('contact', -2), ('location', -2), 
            ('careers', -2), ('privacy policy', -3), ('terms of service', -3),
            ('login', -2), ('sign up', -2), ('register', -2)
        ]
        for indicator, penalty in negative_indicators:
            if indicator in content_lower:
                score += penalty
        
        # Content length penalty/bonus
        content_length = len(content)
        if content_length < 500: score -= 3  # Too short for comprehensive menu
        elif content_length > 5000: score += 2  # Good content depth
        elif content_length > 10000: score += 3  # Excellent content depth
        
        # Navigation/promotional content penalty
        if content_lower.count('click') > 10: score -= 2
        if content_lower.count('learn more') > 5: score -= 2
        if 'promotional' in content_lower: score -= 2
        
        return max(0, score)  # Ensure non-negative score
    
    def _is_successful_response(self, response) -> bool:
        """Check if response indicates successful content retrieval"""
        if not response:
            return False
            
        try:
            # Handle different response formats
            if hasattr(response, 'status_code'):
                return response.status_code == 200 and hasattr(response, 'text') and len(response.text) > 100
            elif isinstance(response, dict):
                status = response.get('status_code', 0)
                content = response.get('text', response.get('content', ''))
                return status == 200 and len(str(content)) > 100
            else:
                # Try to extract content from unknown response types
                content = str(response)
                return len(content) > 100
        except Exception as e:
            logger.debug(f"Error checking response success: {e}")
            return False
    
    def _extract_content_from_response(self, response) -> str:
        """Extract text content from response object or dict"""
        if hasattr(response, 'text'):
            return response.text
        elif isinstance(response, dict):
            return response.get('text', response.get('content', ''))
        return ''
    
    def _extract_json_from_html(self, content: str) -> Optional[str]:
        """
        Extract JSON from HTML-wrapped content.
        
        When Selenium navigates to an API endpoint, the browser renders 
        the JSON response inside HTML tags (typically <pre> tags).
        This method extracts the raw JSON string.
        """
        if not content:
            return None
        
        # Check if content looks like HTML
        content_stripped = content.strip()
        if not content_stripped.startswith('<'):
            # Not HTML, might be raw JSON already
            if content_stripped.startswith('{') or content_stripped.startswith('['):
                return content_stripped
            return None
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Method 1: Look for <pre> tag (common for JSON in browsers)
            pre_tag = soup.find('pre')
            if pre_tag:
                json_text = pre_tag.get_text().strip()
                if json_text.startswith('{') or json_text.startswith('['):
                    logger.debug("Extracted JSON from <pre> tag")
                    return json_text
            
            # Method 2: Look for body content that might be JSON
            body = soup.find('body')
            if body:
                body_text = body.get_text().strip()
                if body_text.startswith('{') or body_text.startswith('['):
                    logger.debug("Extracted JSON from <body> tag")
                    return body_text
            
            # Method 3: Try the entire text content
            all_text = soup.get_text().strip()
            if all_text.startswith('{') or all_text.startswith('['):
                logger.debug("Extracted JSON from page text")
                return all_text
            
            # Method 4: Look for JSON in any tag
            for tag in soup.find_all(['pre', 'code', 'div', 'span']):
                tag_text = tag.get_text().strip()
                if len(tag_text) > 100 and (tag_text.startswith('{') or tag_text.startswith('[')):
                    # Validate it looks like JSON
                    if '"categories"' in tag_text or '"items"' in tag_text or '"products"' in tag_text:
                        logger.debug(f"Extracted JSON from <{tag.name}> tag")
                        return tag_text
                        
        except Exception as e:
            logger.debug(f"HTML JSON extraction failed: {e}")
        
        return None
    
    def _parse_sitemap(self, base_domain: str) -> List[str]:
        """Parse sitemap.xml for potential menu URLs"""
        sitemap_urls = []
        
        try:
            # Add timeout to prevent infinite loops
            import time
            start_time = time.time()
            timeout = 30  # 30 seconds max
            
            # Try common sitemap locations
            initial_locations = [
                f'{base_domain}/sitemap.xml',
                f'{base_domain}/sitemap_index.xml',
                f'{base_domain}/sitemaps/sitemap.xml',
                f'{base_domain}/robots.txt'  # Check robots.txt for sitemap reference
            ]
            
            # Use separate list for additional sitemaps to prevent infinite loop
            additional_sitemaps = []
            all_locations = initial_locations.copy()
            
            for sitemap_url in all_locations:
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Sitemap parsing timeout after {timeout}s")
                    break
                    
                # Limit total sitemaps processed
                if len(all_locations) > 10:
                    logger.warning("Too many sitemaps found, limiting processing")
                    break
                    
                try:
                    response = self._get_with_orchestrator_bypass(sitemap_url)
                    if not self._is_successful_response(response):
                        continue
                        
                    content = self._extract_content_from_response(response)
                    
                    # Prevent processing huge files
                    if len(content) > 1000000:  # 1MB limit
                        logger.warning(f"Sitemap too large, skipping: {sitemap_url}")
                        continue
                    
                    if sitemap_url.endswith('robots.txt'):
                        # Extract sitemap URLs from robots.txt
                        import re
                        sitemap_matches = re.findall(r'Sitemap:\s*(.+)', content, re.IGNORECASE)
                        for match in sitemap_matches[:3]:  # Limit to 3 additional sitemaps
                            new_sitemap = match.strip()
                            if new_sitemap not in all_locations:
                                additional_sitemaps.append(new_sitemap)
                        continue
                    
                    # Parse XML sitemap
                    from xml.etree import ElementTree as ET
                    try:
                        root = ET.fromstring(content)
                        
                        # Handle different sitemap formats
                        namespaces = {'': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                        
                        # Look for URLs containing menu-related terms
                        menu_terms = ['menu', 'food', 'order', 'dining', 'eat']
                        
                        for url_elem in root.findall('.//loc', namespaces) or root.findall('.//url/loc'):
                            url = url_elem.text if url_elem.text else ''
                            url_lower = url.lower()
                            
                            # Score potential menu URLs from sitemap
                            if any(term in url_lower for term in menu_terms):
                                sitemap_urls.append(url)
                                
                        # Limit results to avoid excessive requests
                        if len(sitemap_urls) >= 5:
                            break
                            
                    except ET.ParseError:
                        logger.warning(f"Failed to parse sitemap XML: {sitemap_url}")
                        continue
                        
                except Exception as e:
                    logger.debug(f"Sitemap parsing failed for {sitemap_url}: {e}")
                    continue
            
            # Process additional sitemaps found in robots.txt (after initial processing)
            if additional_sitemaps and len(sitemap_urls) < 5:
                for additional_sitemap in additional_sitemaps:
                    if time.time() - start_time > timeout:
                        break
                    if additional_sitemap not in all_locations:
                        all_locations.append(additional_sitemap)
                    
        except Exception as e:
            logger.warning(f"Sitemap discovery failed: {e}")
        
        return sitemap_urls[:5]  # Return top 5 candidates
    
    def _extract_menu_links_from_main_page(self, base_url: str) -> List[tuple]:
        """Extract and score potential menu links from main page"""
        menu_links = []
        
        try:
            response = self._get_with_orchestrator_bypass(base_url)
            if not self._is_successful_response(response):
                return menu_links
                
            content = self._extract_content_from_response(response)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.get_text().lower().strip()
                
                # Skip invalid links
                if not href or href.startswith(('javascript:', '#', 'mailto:', 'tel:')):
                    continue
                
                score = 0
                
                # Score based on href
                href_scores = [
                    ('menu', 5), ('food', 4), ('order', 4), ('dining', 3),
                    ('eat', 3), ('takeout', 3), ('delivery', 2)
                ]
                for term, points in href_scores:
                    if term in href:
                        score += points
                        break
                
                # Score based on link text
                text_scores = [
                    ('menu', 5), ('order', 4), ('food', 4), ('dine', 3),
                    ('eat', 3), ('takeout', 3), ('catering', 2)
                ]
                for term, points in text_scores:
                    if term in text:
                        score += points
                        break
                
                # Penalty for non-menu links
                non_menu_terms = [
                    'about', 'contact', 'location', 'home', 'news', 'event', 
                    'career', 'job', 'press', 'investor', 'legal'
                ]
                if any(term in href or term in text for term in non_menu_terms):
                    score -= 3
                
                if score > 0:
                    full_url = urljoin(base_url, link['href'])
                    menu_links.append((score, full_url))
            
            # Sort by score and return top candidates
            menu_links.sort(reverse=True)
            return menu_links[:10]
            
        except Exception as e:
            logger.warning(f"Link extraction failed: {e}")
            return []
    
    def _analyze_schema_markup(self, base_url: str) -> List[str]:
        """Analyze structured data for menu-related URLs"""
        schema_urls = []
        
        try:
            response = self._get_with_orchestrator_bypass(base_url)
            if not self._is_successful_response(response):
                return schema_urls
                
            content = self._extract_content_from_response(response)
            
            # Look for JSON-LD structured data
            import re
            json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>'
            json_matches = re.findall(json_ld_pattern, content, re.IGNORECASE)
            
            for json_content in json_matches:
                try:
                    import json
                    data = json.loads(json_content.strip())
                    
                    # Look for Restaurant schema with menu references
                    if isinstance(data, dict):
                        schema_type = data.get('@type', '')
                        if 'restaurant' in schema_type.lower():
                            # Look for menu URL in hasMenu property
                            has_menu = data.get('hasMenu', {})
                            if isinstance(has_menu, dict):
                                menu_url = has_menu.get('url') or has_menu.get('@id')
                                if menu_url:
                                    full_menu_url = urljoin(base_url, menu_url)
                                    schema_urls.append(full_menu_url)
                    
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            # Look for microdata menu references
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find elements with menu-related microdata
            menu_microdata = soup.find_all(attrs={'itemtype': re.compile(r'.*Menu.*', re.I)})
            for element in menu_microdata:
                url_elem = element.find(attrs={'itemprop': 'url'})
                if url_elem and url_elem.get('href'):
                    full_url = urljoin(base_url, url_elem['href'])
                    schema_urls.append(full_url)
            
        except Exception as e:
            logger.warning(f"Schema markup analysis failed: {e}")
        
        return schema_urls[:3]  # Return top 3 candidates
    
    def _needs_js_rendering(self, base_url: str) -> bool:
        """Detect if website requires JavaScript rendering"""
        try:
            response = self._get_with_orchestrator_bypass(base_url)
            if not self._is_successful_response(response):
                return True  # Assume JS needed if we can't get basic content
                
            content = self._extract_content_from_response(response)
            content_lower = content.lower()
            
            # Indicators that JavaScript rendering is needed
            js_indicators = [
                'react', 'angular', 'vue.js', 'spa', 'single page application',
                'loading...', 'please wait', 'javascript required',
                'noscript', 'enable javascript', 'js-enabled'
            ]
            
            js_score = sum(1 for indicator in js_indicators if indicator in content_lower)
            
            # Check for heavy JavaScript frameworks
            framework_patterns = [
                r'react[\-\.]', r'angular[\-\.]', r'vue[\-\.]', 
                r'ember[\-\.]', r'backbone[\-\.]'
            ]
            
            import re
            for pattern in framework_patterns:
                if re.search(pattern, content_lower):
                    js_score += 2
            
            # Check content-to-script ratio
            script_content = len(re.findall(r'<script[\s\S]*?</script>', content, re.IGNORECASE))
            text_content = len(re.sub(r'<[^>]*>', '', content))
            
            if script_content > 0 and text_content / max(script_content, 1) < 10:
                js_score += 1
            
            return js_score >= 3
            
        except Exception:
            return False
    
    def _discover_js_menu_urls(self, base_url: str) -> List[str]:
        """Discover menu URLs that require JavaScript rendering"""
        # This would integrate with Selenium/Playwright for full JS rendering
        # For now, return enhanced path variations for SPA applications
        parsed_url = urlparse(base_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        js_menu_paths = [
            '/#/menu', '/#/food', '/#/order', '/#/dining',
            '/app/menu', '/app/food', '/app/order',
            '/menu.html', '/food.html', '/order.html'
        ]
        
        return [urljoin(base_domain, path) for path in js_menu_paths]
    
    def _detect_third_party_menu_services(self, base_url: str) -> Dict[str, str]:
        """Detect integration with third-party menu services"""
        third_party_services = {}
        
        try:
            response = self._get_with_orchestrator_bypass(base_url)
            if not self._is_successful_response(response):
                return third_party_services
                
            content = self._extract_content_from_response(response)
            content_lower = content.lower()
            
            # Detect common third-party integrations
            service_patterns = {
                'DoorDash': [r'doordash\.com', r'dd\.ddb', 'doordash'],
                'UberEats': [r'ubereats\.com', r'uber-eats', 'ubereats'],
                'GrubHub': [r'grubhub\.com', r'seamless\.com', 'grubhub'],
                'Postmates': [r'postmates\.com', 'postmates'],
                'ChowNow': [r'chownow\.com', 'chownow'],
                'Toast': [r'toasttab\.com', 'toast pos', 'toastpos'],
                'Square': [r'squareup\.com', 'square online', 'weebly'],
                'OpenTable': [r'opentable\.com', 'opentable']
            }
            
            import re
            for service_name, patterns in service_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content_lower):
                        # Extract the actual URL if possible
                        url_match = re.search(fr'https?://[^"\s]*{pattern}[^"\s]*', content, re.IGNORECASE)
                        if url_match:
                            third_party_services[service_name] = url_match.group()
                        else:
                            third_party_services[service_name] = f"Detected {service_name} integration"
                        break
            
        except Exception as e:
            logger.warning(f"Third-party service detection failed: {e}")
        
        return third_party_services
    
    def _crawl_internal_links(self, base_url: str, max_depth: int = 2) -> List[str]:
        """Intelligently crawl internal links for menu pages"""
        crawl_urls = []
        
        try:
            response = self._get_with_orchestrator_bypass(base_url)
            if not self._is_successful_response(response):
                return crawl_urls
                
            content = self._extract_content_from_response(response)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            parsed_base = urlparse(base_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            # Find internal links with menu potential
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                
                # Skip external, invalid, or non-menu links
                if not href or href.startswith(('http', 'mailto:', 'tel:', '#')):
                    if href.startswith('http') and base_domain not in href:
                        continue  # Skip external links
                
                full_url = urljoin(base_url, href)
                url_path = urlparse(full_url).path.lower()
                
                # Only crawl paths that might contain menus
                menu_indicators = [
                    'menu', 'food', 'order', 'dining', 'eat', 'restaurant',
                    'cafe', 'bar', 'kitchen', 'cuisine', 'dish'
                ]
                
                if any(indicator in url_path for indicator in menu_indicators):
                    crawl_urls.append(full_url)
                
                # Limit crawl results
                if len(crawl_urls) >= 10:
                    break
            
        except Exception as e:
            logger.warning(f"Internal link crawling failed: {e}")
        
        return crawl_urls[:5]  # Return top 5 candidates
    
    def _log_discovery_success(self, original_url: str, found_url: str, attempts: int, method: str, log_data: List[Dict]):
        """Log successful menu discovery for analysis"""
        try:
            logger.info(f"✅ Menu discovery successful: {original_url} -> {found_url}")
            logger.info(f"   Method: {method}, Attempts: {attempts}")
            
            # This could integrate with database logging
            # For now, just log to file/console
            
        except Exception:
            pass  # Don't fail extraction due to logging issues
    
    def _save_discovery_log(self, base_url: str, discovery_log: List[Dict], final_url: str, final_score: int):
        """Save comprehensive discovery log for debugging"""
        try:
            import json
            log_entry = {
                'base_url': base_url,
                'final_url': final_url,
                'final_score': final_score,
                'total_attempts': len(discovery_log),
                'discovery_log': discovery_log,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to debug file (if debug mode enabled)
            debug_file = 'menu_discovery_debug.jsonl'
            try:
                with open(debug_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception:
                pass  # Don't fail extraction due to debug file issues
                
        except Exception:
            pass  # Don't fail extraction due to logging issues

    def scrape_dom_content(self, page_content: str, base_url: str) -> Dict[str, Any]:
        """Scrape menu content from DOM with support for modern Angular/Ionic apps"""
        
        soup = BeautifulSoup(page_content, 'html.parser')
        
        menu_data = {
            'categories': {},
            'items': [],
            'metadata': {}
        }
        
        # First, try to extract from Angular/Ionic components (like Bubba's 33)
        category_cards = soup.find_all('app-category-card')
        if category_cards:
            logger.info(f"Found {len(category_cards)} Angular category cards")
            for card in category_cards:
                category_name = "Unknown"
                
                # Look for category name in h5 or similar
                header = card.find(['h5', 'h4', 'h3', 'h2'])
                if header:
                    category_name = header.get_text().strip()
                    
                # For now, create placeholder items since this is a category overview page
                # The actual items would be on individual category pages
                menu_data['categories'][category_name] = []
                
                logger.info(f"Found category: {category_name}")
        
        # Look for category links in navigation
        category_links = soup.find_all('a', href=re.compile(r'/menu/'))
        if category_links:
            logger.info(f"Found {len(category_links)} category links")
            for link in category_links:
                href = link.get('href', '')
                category_name = link.get_text().strip()
                
                # Skip generic menu links
                if category_name and category_name.lower() not in ['our menu', 'menu']:
                    if category_name not in menu_data['categories']:
                        menu_data['categories'][category_name] = []
                    logger.info(f"Found category from link: {category_name}")
        
        # Traditional DOM parsing fallback
        if not menu_data['categories']:
            # Remove navigation, footer, and header elements first
            for element in soup.find_all(['nav', 'footer', 'header']):
                element.decompose()
                
            # Remove elements with navigation-related classes/ids
            nav_selectors = ['[class*="nav"]', '[class*="footer"]', '[class*="header"]', '[id*="nav"]', '[id*="footer"]']
            for selector in nav_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Look for menu sections with stronger indicators
            menu_sections = soup.find_all(['div', 'section', 'ul', 'main'], 
                                        class_=re.compile(r'menu|food|category|item|product', re.I))
        
            for section in menu_sections:
                category_name = "General"
                
                # Look for category headers
                header = section.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                if header:
                    header_text = header.get_text().strip()
                    # Skip navigation headers
                    nav_headers = ['experience', 'locations', 'contact', 'careers', 'about']
                    if not any(nav in header_text.lower() for nav in nav_headers):
                        category_name = header_text
                
                items = self._extract_items_from_section(section)
                
                if items:
                    if category_name not in menu_data['categories']:
                        menu_data['categories'][category_name] = []
                    
                    menu_data['categories'][category_name].extend(items)
                    menu_data['items'].extend(items)
        
        # Enhanced fallback extraction
        if not menu_data['items']:
            all_items = self._extract_items_fallback(soup)
            if all_items:
                menu_data['items'] = all_items
                menu_data['categories']['General'] = all_items
        
        menu_data['metadata'] = {
            'source_url': base_url,
            'total_items': len(menu_data['items']),
            'categories_found': len(menu_data['categories'])
        }
        
        logger.info(f"Menu extraction results: {len(menu_data['items'])} items, {len(menu_data['categories'])} categories")
        logger.info(f"Categories found: {list(menu_data['categories'].keys())}")
        
        return menu_data
    
    def _extract_items_from_section(self, section):
        """Extract items from a menu section with Angular/Ionic support"""
        items = []
        
        # Skip navigation, footer, and header sections
        section_class = ' '.join(section.get('class', [])).lower()
        section_id = section.get('id', '').lower()
        
        skip_indicators = ['nav', 'footer', 'header', 'sidebar', 'breadcrumb', 'social']
        if any(indicator in section_class or indicator in section_id for indicator in skip_indicators):
            return items
        
        # Look for Angular/Ionic menu item components first
        item_components = section.find_all(['app-menu-item', 'ion-item', 'app-product-card'])
        if item_components:
            logger.info(f"Found {len(item_components)} Angular/Ionic item components")
            for component in item_components:
                item_name = ""
                item_price = ""
                item_desc = ""
                
                # Look for name in common elements
                name_elem = component.find(['h1', 'h2', 'h3', 'h4', 'h5', '.item-name', '.product-name'])
                if name_elem:
                    item_name = name_elem.get_text().strip()
                
                # Look for price
                price_elem = component.find(text=re.compile(r'\$\d+'))
                if price_elem:
                    item_price = self._extract_price(price_elem)
                    
                # Look for description
                desc_elem = component.find(['.description', '.item-desc', 'p'])
                if desc_elem:
                    item_desc = desc_elem.get_text().strip()
                    
                if item_name:
                    items.append({
                        'name': item_name,
                        'description': item_desc or item_name,
                        'price': item_price
                    })
                    
        # Fallback to traditional parsing
        if not items:
            # Look for potential item containers
            item_elements = section.find_all(['div', 'li', 'tr'], 
                                           class_=re.compile(r'item|product|dish|food', re.I))
            
            for element in item_elements:
                text = element.get_text().strip()
                
                # Filter out navigation-like items
                nav_words = ['login', 'sign up', 'contact', 'careers', 'privacy', 'terms', 'locations', 'gift cards', 'fan club']
                if any(nav_word in text.lower() for nav_word in nav_words):
                    continue
                    
                # Look for actual menu item indicators
                if text and 10 <= len(text) <= 200:  # Reasonable item length
                    # Check if it looks like a food item
                    food_words = ['burger', 'pizza', 'sandwich', 'salad', 'chicken', 'beef', 'pasta', 'soup', 'wings', 'fries']
                    has_food_word = any(food_word in text.lower() for food_word in food_words)
                    has_price = bool(self._extract_price(text))
                    
                    if has_food_word or has_price:
                        items.append({
                            'name': text[:50],  # Truncate long names
                            'description': text,
                            'price': self._extract_price(text)
                        })
        
        return items
    
    def _extract_items_fallback(self, soup):
        """Enhanced fallback item extraction"""
        items = []
        
        # Look for elements with price indicators
        price_elements = soup.find_all(text=re.compile(r'\$\d+\.\d{2}|\$\d+'))
        
        for element in price_elements:
            parent = element.parent
            if parent:
                text = parent.get_text().strip()
                
                # Filter out navigation and non-food items
                nav_words = ['gift', 'card', 'location', 'contact', 'career', 'login', 'sign']
                if any(nav_word in text.lower() for nav_word in nav_words):
                    continue
                
                # Look for food-related words
                food_words = ['burger', 'pizza', 'sandwich', 'salad', 'chicken', 'beef', 'pasta', 
                             'wings', 'fries', 'appetizer', 'entree', 'dessert', 'drink']
                
                if 10 <= len(text) <= 150 and any(food_word in text.lower() for food_word in food_words):
                    items.append({
                        'name': text[:50],
                        'description': text,
                        'price': self._extract_price(text)
                    })
        
        # If still no items, look for common menu item patterns
        if not items:
            potential_items = soup.find_all(['p', 'div', 'span'], 
                                          text=re.compile(r'(burger|pizza|sandwich|salad|chicken|wings)', re.I))
            
            for item in potential_items[:10]:  # Limit attempts
                text = item.get_text().strip()
                if 10 <= len(text) <= 150:
                    items.append({
                        'name': text[:50],
                        'description': text,
                        'price': None
                    })
        
        return items[:15]  # Limit to 15 items for fallback
    
    def _extract_price(self, text):
        """Extract price from text"""
        price_match = re.search(r'\$[\d,]+\.?\d*', text)
        return price_match.group() if price_match else None
    
    def _validate_menu_api_data(self, data):
        """Validate if API data looks like menu data"""
        if not isinstance(data, dict):
            return False
        
        # Check for common menu data indicators
        menu_keys = ['menu', 'items', 'products', 'food', 'categories']
        return any(key in str(data).lower() for key in menu_keys)
    
    def _calculate_confidence_score(self, items_found: int, categories_found: int, menu_data: Dict) -> float:
        """Calculate confidence score"""
        
        score = 0.0
        
        # Item count scoring
        if items_found >= 20:
            score += 0.5
        elif items_found >= 10:
            score += 0.4
        elif items_found >= 5:
            score += 0.3
        elif items_found > 0:
            score += 0.2
        
        # Category organization
        if categories_found >= 3:
            score += 0.3
        elif categories_found >= 2:
            score += 0.2
        
        # Data quality check
        if menu_data.get('items'):
            items_with_prices = sum(1 for item in menu_data['items'] 
                                  if item.get('price') or '$' in str(item))
            if items_with_prices > 0:
                score += 0.2
        
        return min(1.0, score)
    
    def _extract_restaurant_name(self, page_content: str, website_url: str) -> str:
        """Extract restaurant name"""
        
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Try title tag first
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            for suffix in [' - Menu', ' | Menu', ' Menu', ' | Home', ' - Home']:
                if suffix in title_text:
                    return title_text.split(suffix)[0].strip()
            return title_text
        
        # Try h1 tags
        h1_tags = soup.find_all('h1')
        if h1_tags:
            return h1_tags[0].get_text().strip()
        
        # Fallback to domain
        parsed = urlparse(website_url)
        domain = parsed.netloc.replace('www.', '')
        return domain.split('.')[0].title()
    
    def _get_with_orchestrator_bypass(self, url: str):
        """Get URL using sophisticated bypass orchestrator"""
        
        try:
            # Use orchestrator for intelligent strategy selection and escalation
            response, metadata = self.orchestrator.bypass_cloudflare(url)
            
            # Handle both response object and dict formats
            status_code = None
            if hasattr(response, 'status_code'):
                status_code = response.status_code
            elif isinstance(response, dict):
                status_code = response.get('status_code', 200)
            
            if response and status_code == 200:
                strategy_used = metadata.get('strategy', 'unknown')
                challenge_type = metadata.get('challenge_type', 'none')
                logger.info(f"Bypass successful for {url} using strategy: {strategy_used}")
                logger.info(f"Challenge detected: {challenge_type}")
                return response
            else:
                logger.warning(f"Orchestrator bypass failed for {url} - status: {status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Orchestrator bypass error for {url}: {e}")
            return None
    
    def extract_menu(self, website_url: str, restaurant_name: Optional[str] = None, force_menu_url: Optional[str] = None) -> MenuExtractionResult:
        """Main menu extraction method with authentication bypass"""

        start_time = datetime.now()

        try:
            # STEP 1: Try API-first extraction (check database, then discovery)
            logger.info("=" * 80)
            logger.info("STEP 1: Attempting API-first extraction")
            logger.info("=" * 80)

            api_result = self._try_api_extraction(website_url, restaurant_name)

            if api_result and api_result.success:
                logger.success(f"API extraction successful! Extracted {api_result.items_found} items in {api_result.processing_time_seconds:.1f}s")
                return api_result

            # STEP 2: Fallback to traditional scraping
            logger.info("=" * 80)
            logger.info("STEP 2: Falling back to traditional scraping")
            logger.info("=" * 80)

            # Use forced URL or find menu page
            if force_menu_url:
                menu_url = force_menu_url
                menu_score = 10  # Assume forced URL is high quality
            else:
                menu_url, menu_score = self.find_menu_page(website_url)
                logger.info(f"Found menu page: {menu_url} (score: {menu_score})")
            
            # Use orchestrator bypass for intelligent strategy selection
            response = self._get_with_orchestrator_bypass(menu_url)
            
            if not response:
                raise Exception("Failed to fetch page content")
            
            # Handle both response object and dict formats for text content
            page_content = ""
            if hasattr(response, 'text'):
                page_content = response.text
            elif isinstance(response, dict):
                page_content = response.get('text', response.get('content', ''))
            
            if not page_content:
                raise Exception("Empty page content received")
            
            # Orchestrator handles all authentication bypass automatically
            
            # If we have a high-scoring menu page, try direct extraction first
            menu_data = None
            
            if menu_score >= 8:
                logger.info(f"High-scoring menu page found (score: {menu_score}), attempting direct extraction")
                try:
                    menu_data = self._extract_js_menu_with_navigation(menu_url)
                    if menu_data and menu_data.get('items') and len(menu_data.get('items', [])) > 0:
                        logger.info(f"Direct extraction successful with {len(menu_data.get('items', []))} items")
                        return self._format_extraction_result(menu_data, menu_url)
                except Exception as e:
                    logger.warning(f"Direct extraction failed: {e}, falling back to API discovery")
            
            # Enhanced API detection with dynamic discovery
            api_endpoints = self.detect_api_endpoints(page_content, menu_url)
            
            # Try API endpoints if direct extraction didn't work
            if api_endpoints:
                logger.info(f"Testing {len(api_endpoints)} discovered API endpoints")
                
                # Prioritize OLO endpoints (sort them first)
                olo_endpoints = [ep for ep in api_endpoints if 'olo' in ep.lower() or '/restaurants/' in ep.lower()]
                other_endpoints = [ep for ep in api_endpoints if ep not in olo_endpoints]
                sorted_endpoints = olo_endpoints + other_endpoints
                
                for i, endpoint in enumerate(sorted_endpoints[:8], 1):  # Try top 8 endpoints
                    try:
                        # Handle direct extraction results
                        if endpoint == "DIRECT_EXTRACTION_AVAILABLE":
                            logger.info(f"Processing direct JavaScript extraction result")
                            if hasattr(self, '_direct_extraction_result'):
                                menu_data = self._direct_extraction_result
                                if menu_data.get('success'):
                                    logger.info(f"Direct extraction successful with {menu_data.get('total_items', 0)} items")
                                    break
                            continue
                        
                        is_olo_endpoint = 'olo' in endpoint.lower() or '/restaurants/' in endpoint.lower()
                        logger.info(f"Testing {'OLO ' if is_olo_endpoint else ''}API endpoint {i}: {endpoint}")
                        api_response = self._get_with_orchestrator_bypass(endpoint)
                        
                        # Check status for both response object and dict formats
                        status_code = None
                        if hasattr(api_response, 'status_code'):
                            status_code = api_response.status_code
                        elif isinstance(api_response, dict):
                            status_code = api_response.get('status_code', 200)
                        
                        if api_response and status_code == 200:
                            # Extract JSON data properly - handle Selenium HTML-wrapped responses
                            api_data = None
                            try:
                                if hasattr(api_response, 'json'):
                                    try:
                                        api_data = api_response.json()
                                    except Exception:
                                        pass
                                
                                if not api_data and isinstance(api_response, dict) and 'json' in api_response:
                                    api_data = api_response['json']
                                
                                if not api_data:
                                    # Get text content and try to extract JSON
                                    content = self._extract_content_from_response(api_response)
                                    
                                    if content:
                                        # Handle Selenium HTML-wrapped JSON (browser renders JSON in <pre> tag)
                                        json_str = self._extract_json_from_html(content)
                                        if json_str:
                                            api_data = json.loads(json_str)
                                        else:
                                            # Try parsing content directly as JSON
                                            api_data = json.loads(content)
                                            
                            except json.JSONDecodeError as e:
                                logger.debug(f"JSON decode failed for {endpoint}: {e}")
                                continue
                            except Exception as e:
                                logger.debug(f"Error extracting JSON from {endpoint}: {e}")
                                continue
                            
                            if not api_data:
                                continue
                                
                            logger.info(f"Successfully parsed JSON from API endpoint: {endpoint}")
                            
                            # Try OLO-specific extraction first for OLO endpoints
                            if is_olo_endpoint:
                                logger.info("Attempting OLO-specific menu extraction...")
                                olo_menu = self._extract_olo_menu(api_data)
                                if olo_menu and len(olo_menu.get('items', [])) >= 10:
                                    menu_data = olo_menu
                                    items_count = len(menu_data.get('items', []))
                                    cats_count = len(menu_data.get('categories', {}))
                                    logger.info(f"OLO extraction successful: {items_count} items in {cats_count} categories")
                                    
                                    # Check if we need to enrich with DOM prices
                                    items_with_prices = sum(1 for item in menu_data['items'] if item.get('price'))
                                    if items_with_prices == 0:
                                        logger.info("OLO returned no prices, attempting DOM price enrichment...")
                                        menu_data = self._enrich_olo_with_dom_prices(menu_data, menu_url)
                                        items_with_prices = sum(1 for item in menu_data['items'] if item.get('price'))
                                        if items_with_prices > 0:
                                            logger.info(f"DOM enrichment added {items_with_prices} prices")
                                    
                                    logger.info(f"EARLY EXIT: Valid OLO data found, skipping remaining extraction methods")

                                    # Save discovered OLO API endpoint to database
                                    try:
                                        parsed_url = urlparse(website_url)
                                        domain = parsed_url.netloc
                                        self._save_discovered_api_endpoint(
                                            domain=domain,
                                            endpoint=endpoint,
                                            endpoint_type='olo',
                                            requires_location=False,
                                            site_type='api_driven'
                                        )
                                    except Exception as e:
                                        logger.warning(f"Failed to save OLO endpoint: {e}")

                                    # === EARLY EXIT - Return immediately with OLO data ===
                                    processing_time = (datetime.now() - start_time).total_seconds()
                                    confidence_score = self._enhanced_confidence_score(
                                        items_count, cats_count, menu_data, 'olo_api', processing_time
                                    )

                                    if not restaurant_name:
                                        restaurant_name = self._extract_restaurant_name(page_content, website_url)

                                    return MenuExtractionResult(
                                        success=True,
                                        restaurant_name=restaurant_name or "Unknown Restaurant",
                                        website_url=website_url,
                                        menu_url=endpoint,  # Use the OLO API endpoint as menu URL
                                        items_found=items_count,
                                        categories_found=cats_count,
                                        processing_time_seconds=processing_time,
                                        menu_data=menu_data,
                                        confidence_score=confidence_score
                                    )
                                elif olo_menu and len(olo_menu.get('items', [])) > 0:
                                    # Some items found but less than threshold, keep trying
                                    menu_data = olo_menu
                                    logger.info(f"OLO extraction found {len(menu_data.get('items', []))} items (below threshold, continuing)")
                            
                            # Fall back to generic API extraction
                            if not menu_data:
                                generic_menu = self._validate_and_extract_api_menu(api_data)
                                if generic_menu and len(generic_menu.get('items', [])) >= 10:
                                    menu_data = generic_menu
                                    items_count = len(menu_data.get('items', []))
                                    logger.info(f"Generic API extraction successful: {items_count} items - EARLY EXIT")

                                    # Save discovered generic API endpoint to database
                                    try:
                                        parsed_url = urlparse(website_url)
                                        domain = parsed_url.netloc
                                        # Determine if this is a REST, GraphQL, or custom API
                                        api_type = 'custom'
                                        if 'graphql' in endpoint.lower():
                                            api_type = 'graphql'
                                        elif '/api/' in endpoint.lower():
                                            api_type = 'rest'

                                        self._save_discovered_api_endpoint(
                                            domain=domain,
                                            endpoint=endpoint,
                                            endpoint_type=api_type,
                                            requires_location=False,
                                            site_type='api_driven'
                                        )
                                    except Exception as e:
                                        logger.warning(f"Failed to save generic API endpoint: {e}")

                                    # === EARLY EXIT - Return immediately with generic API data ===
                                    processing_time = (datetime.now() - start_time).total_seconds()
                                    cats_count = len(menu_data.get('categories', {}))
                                    confidence_score = self._enhanced_confidence_score(
                                        items_count, cats_count, menu_data, 'generic_api', processing_time
                                    )

                                    if not restaurant_name:
                                        restaurant_name = self._extract_restaurant_name(page_content, website_url)

                                    return MenuExtractionResult(
                                        success=True,
                                        restaurant_name=restaurant_name or "Unknown Restaurant",
                                        website_url=website_url,
                                        menu_url=endpoint,
                                        items_found=items_count,
                                        categories_found=cats_count,
                                        processing_time_seconds=processing_time,
                                        menu_data=menu_data,
                                        confidence_score=confidence_score
                                    )
                                elif generic_menu and len(generic_menu.get('items', [])) > 0:
                                    menu_data = generic_menu
                                    logger.info(f"Generic API found {len(menu_data.get('items', []))} items (continuing)")
                            
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode failed for {endpoint}: {e}")
                        continue
                    except Exception as e:
                        logger.debug(f"API endpoint {endpoint} failed: {e}")
                        continue
            
            # Enhanced JavaScript menu extraction fallback
            if not menu_data:
                logger.info("No valid API data found, trying JavaScript extraction...")
                js_menu_data = self._extract_js_menu_data(menu_url)
                if js_menu_data and js_menu_data.get('items'):
                    menu_data = js_menu_data
                    logger.info(f"JavaScript extraction successful: {len(menu_data.get('items', []))} items")
            
            # Try Angular SPA extraction for sites like Bubba's 33
            if not menu_data or len(menu_data.get('items', [])) < 10:
                # Check if this looks like an Angular/Ionic SPA
                angular_indicators = ['ng-', 'ion-', 'angular', '_ngcontent', 'hydrated']
                is_angular = any(indicator in page_content.lower() for indicator in angular_indicators)
                
                if is_angular:
                    logger.info("Detected Angular/Ionic SPA, trying specialized extraction...")
                    angular_menu_data = self._extract_angular_spa_menu(menu_url)
                    if angular_menu_data and len(angular_menu_data.get('items', [])) > len(menu_data.get('items', []) if menu_data else []):
                        menu_data = angular_menu_data
                        logger.info(f"Angular SPA extraction successful: {len(menu_data.get('items', []))} items")
            
            # If still no data, continue with existing DOM scraping
            if not menu_data or len(menu_data.get('items', [])) == 0:
                logger.info("Falling back to DOM scraping...")
                menu_data = self.scrape_dom_content(page_content, menu_url)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            items_found = len(menu_data.get('items', []))
            categories_found = len(menu_data.get('categories', {}))
            
            # Enhanced confidence scoring with comprehensive validation
            confidence_score = self._enhanced_confidence_score(
                items_found, categories_found, menu_data, 'dom_structured', processing_time
            )
            
            # Validate success threshold (7+ menu items with structured pricing)
            meets_threshold, validation_details = self._validate_success_threshold(menu_data)
            
            # Save raw HTML for debugging if enabled or if extraction fails threshold
            if not meets_threshold or logger.isEnabledFor(10):  # DEBUG level
                self._save_raw_html(menu_url, page_content, 
                                    restaurant_name or 'unknown', confidence_score)
            
            if not restaurant_name:
                restaurant_name = self._extract_restaurant_name(page_content, website_url)
            
            return MenuExtractionResult(
                success=True,
                restaurant_name=restaurant_name,
                website_url=website_url,
                menu_url=menu_url,
                items_found=items_found,
                categories_found=categories_found,
                processing_time_seconds=processing_time,
                menu_data=menu_data,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Menu extraction failed: {e}")
            
            return MenuExtractionResult(
                success=False,
                restaurant_name=restaurant_name or "Unknown",
                website_url=website_url,
                menu_url=website_url,
                items_found=0,
                categories_found=0,
                processing_time_seconds=processing_time,
                menu_data={},
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _save_raw_html(self, url: str, content: str, restaurant_id: str = None, confidence_score: float = 0.0):
        """Save raw HTML content for debugging and manual analysis"""
        try:
            import hashlib
            import os
            from datetime import datetime
            
            # Create debug directory if it doesn't exist
            debug_dir = 'debug_html'
            os.makedirs(debug_dir, exist_ok=True)
            
            # Generate filename based on URL and timestamp
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{debug_dir}/menu_extraction_{url_hash}_{timestamp}.html'
            
            # Add metadata as HTML comments
            metadata = f"""
<!-- 
DEBUG INFORMATION
URL: {url}
Restaurant ID: {restaurant_id or 'Unknown'}
Confidence Score: {confidence_score}
Extraction Time: {datetime.now().isoformat()}
Content Length: {len(content)} characters
-->

"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(metadata + content)
            
            logger.info(f"Raw HTML saved for debugging: {filename}")
            
        except Exception as e:
            logger.warning(f"Failed to save raw HTML for debugging: {e}")
    
    def _validate_success_threshold(self, menu_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate if extraction meets 7+ menu items with structured pricing threshold"""
        validation_result = {
            'meets_threshold': False,
            'total_items': 0,
            'items_with_prices': 0,
            'categories_found': 0,
            'avg_confidence': 0.0,
            'validation_details': {}
        }
        
        try:
            items = menu_data.get('items', [])
            categories = menu_data.get('categories', {})
            
            validation_result['total_items'] = len(items)
            validation_result['categories_found'] = len(categories)
            
            # Count items with structured pricing
            items_with_prices = 0
            confidence_scores = []
            
            for item in items:
                if isinstance(item, dict):
                    # Check for price information
                    has_price = (
                        item.get('price') is not None or 
                        item.get('price_text') is not None or 
                        '$' in str(item.get('name', '')) or 
                        '$' in str(item.get('description', ''))
                    )
                    
                    if has_price:
                        items_with_prices += 1
                    
                    # Collect confidence scores if available
                    if 'confidence' in item:
                        confidence_scores.append(float(item['confidence']))
            
            validation_result['items_with_prices'] = items_with_prices
            
            # Calculate average confidence
            if confidence_scores:
                validation_result['avg_confidence'] = sum(confidence_scores) / len(confidence_scores)
            
            # Determine if meets success threshold
            meets_threshold = (
                validation_result['total_items'] >= 7 and
                validation_result['items_with_prices'] >= 5 and  # At least 5 items with pricing
                validation_result['categories_found'] >= 2 and   # At least 2 menu categories
                validation_result['avg_confidence'] >= 0.5       # Reasonable confidence
            )
            
            validation_result['meets_threshold'] = meets_threshold
            
            # Add detailed validation information
            validation_result['validation_details'] = {
                'threshold_criteria': {
                    'min_items': 7,
                    'min_items_with_prices': 5,
                    'min_categories': 2,
                    'min_avg_confidence': 0.5
                },
                'actual_values': {
                    'items': validation_result['total_items'],
                    'items_with_prices': validation_result['items_with_prices'],
                    'categories': validation_result['categories_found'],
                    'avg_confidence': validation_result['avg_confidence']
                },
                'passes_criteria': {
                    'items': validation_result['total_items'] >= 7,
                    'pricing': validation_result['items_with_prices'] >= 5,
                    'categories': validation_result['categories_found'] >= 2,
                    'confidence': validation_result['avg_confidence'] >= 0.5
                }
            }
            
            return meets_threshold, validation_result
            
        except Exception as e:
            logger.error(f"Success threshold validation failed: {e}")
            validation_result['error'] = str(e)
            return False, validation_result
    
    def _enhanced_confidence_score(self, items_found: int, categories_found: int, menu_data: Dict, 
                                   extraction_method: str, response_time: float) -> float:
        """Calculate enhanced confidence score with comprehensive factors"""
        try:
            base_score = 0.0
            
            # Item count scoring (0-0.4)
            if items_found >= 15: base_score += 0.4
            elif items_found >= 10: base_score += 0.35
            elif items_found >= 7: base_score += 0.3   # Meets threshold
            elif items_found >= 5: base_score += 0.25
            elif items_found >= 3: base_score += 0.15
            elif items_found >= 1: base_score += 0.1
            
            # Category diversity scoring (0-0.2)
            if categories_found >= 6: base_score += 0.2
            elif categories_found >= 4: base_score += 0.15
            elif categories_found >= 2: base_score += 0.1
            elif categories_found >= 1: base_score += 0.05
            
            # Content quality scoring (0-0.2)
            items = menu_data.get('items', [])
            quality_indicators = 0
            
            for item in items:
                if isinstance(item, dict):
                    # Award points for structured data
                    if item.get('price'): quality_indicators += 2
                    if item.get('description'): quality_indicators += 1
                    if item.get('name') and len(item['name']) > 5: quality_indicators += 1
            
            quality_score = min(quality_indicators / max(items_found * 2, 1), 0.2)
            base_score += quality_score
            
            # Extraction method scoring (0-0.1)
            method_scores = {
                'api_discovery': 0.1,
                'dom_structured': 0.08,
                'sitemap_discovery': 0.06,
                'link_analysis': 0.04,
                'fallback': 0.02
            }
            base_score += method_scores.get(extraction_method, 0.02)
            
            # Performance scoring (0-0.1)
            if response_time < 5.0: base_score += 0.1
            elif response_time < 10.0: base_score += 0.05
            elif response_time > 30.0: base_score -= 0.05
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, base_score))
            
            return final_score
            
        except Exception as e:
            logger.error(f"Enhanced confidence calculation failed: {e}")
            return 0.5  # Return neutral score on error

# API Authentication
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key"""
    valid_keys = ["prod_key_12345", "dev_key_67890", "test_key_abc123"]
    
    if credentials.credentials not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return credentials.credentials

# API Endpoints
@app.get("/")
async def root():
    """API information"""
    return {
        "service": "CloudDestroyer Production API",
        "version": "2.0.0",
        "status": "production",
        "endpoints": {
            "restaurant": "POST /restaurant/extract",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.post("/restaurant/extract")
async def extract_restaurant_menu(
    request: RestaurantScrapeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Extract restaurant menu data

    Main endpoint for restaurant menu extraction:
    - Automatically finds menu page (e.g., bubbas33.com -> bubbas33.com/menu)  
    - Bypasses protection with CloudDestroyer
    - Returns structured menu data
    """
    
    try:
        # Create scraper instance for this request
        with RestaurantMenuScraper() as scraper:
            result = scraper.extract_menu(
                website_url=str(request.website_url),
                restaurant_name=request.restaurant_name,
                force_menu_url=request.force_menu_url
            )
        
        logger.info(f"Restaurant extraction: {result.success}, {result.items_found} items")
        return result
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return error response
        return {
            "success": False,
            "restaurant_name": request.restaurant_name or "Unknown",
            "website_url": str(request.website_url),
            "menu_url": str(request.website_url),
            "items_found": 0,
            "categories_found": 0,
            "processing_time_seconds": 0.0,
            "confidence_score": 0.0,
            "menu_data": {},
            "error_message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")