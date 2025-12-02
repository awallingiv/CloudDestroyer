#!/usr/bin/env python3
"""
CloudDestroyer Production API
Restaurant menu scraping with intelligent detection and extraction
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Dict, Any
import json
import os
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging

# Import CloudDestroyer
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.core.cloud_destroyer import CloudDestroyer

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
    """Production restaurant menu scraper using CloudDestroyer"""
    
    MENU_PATHS = [
        '/menu', '/menus', '/our-menu', '/food-menu', '/dining-menu',
        '/lunch-menu', '/dinner-menu', '/full-menu', '/menu/', '/food',
        '/order', '/order-online', '/ordering'
    ]
    
    MENU_INDICATORS = [
        'menu', 'appetizer', 'entree', 'main', 'dessert', 'beverage', 'drink',
        'pizza', 'burger', 'sandwich', 'salad', 'pasta', 'chicken', 'beef',
        'price', '$', 'order', 'delivery', 'takeout', 'dine-in'
    ]
    
    def __init__(self):
        self.destroyer = CloudDestroyer()
    
    def find_menu_page(self, base_url: str) -> str:
        """Find the actual menu page URL"""
        
        try:
            # Check if base URL contains menu content
            response = self.destroyer.get(base_url)
            if response.status_code == 200:
                content = response.text.lower()
                menu_score = sum(1 for indicator in self.MENU_INDICATORS if indicator in content)
                
                if menu_score >= 3:
                    return base_url
            
            # Try common menu paths
            parsed_url = urlparse(base_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            for path in self.MENU_PATHS:
                menu_url = urljoin(base_domain, path)
                
                try:
                    response = self.destroyer.get(menu_url)
                    if response.status_code == 200:
                        content = response.text.lower()
                        menu_score = sum(1 for indicator in self.MENU_INDICATORS if indicator in content)
                        
                        if menu_score >= 3:
                            logger.info(f"Found menu page: {menu_url}")
                            return menu_url
                            
                except Exception:
                    continue
            
            return base_url
            
        except Exception as e:
            logger.error(f"Error finding menu page: {e}")
            return base_url
    
    def detect_api_endpoints(self, page_content: str, base_url: str) -> List[str]:
        """Detect potential API endpoints for menu data"""
        
        endpoints = []
        
        api_patterns = [
            r'/api/menu', r'/api/v\d+/menu', r'/wp-json/.*menu',
            r'/rest/.*menu', r'/api/.*food', r'/menu\.json', r'/data/menu'
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                endpoints.append(urljoin(base_url, match))
        
        return list(set(endpoints))
    
    def scrape_dom_content(self, page_content: str, base_url: str) -> Dict[str, Any]:
        """Scrape menu content from DOM"""
        
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(page_content, 'html.parser')
        menu_data = {
            'categories': {},
            'items': [],
            'metadata': {}
        }
        
        # Look for menu sections
        menu_sections = soup.find_all(['div', 'section', 'ul'], class_=re.compile(r'menu|food|category', re.I))
        
        for section in menu_sections:
            category_name = "General"
            
            # Look for category headers
            header = section.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            if header:
                category_name = header.get_text().strip()
            
            items = self._extract_items_from_section(section)
            
            if items:
                if category_name not in menu_data['categories']:
                    menu_data['categories'][category_name] = []
                
                menu_data['categories'][category_name].extend(items)
                menu_data['items'].extend(items)
        
        # Fallback extraction if no structured sections
        if not menu_data['items']:
            all_items = self._extract_items_fallback(soup)
            menu_data['items'] = all_items
            menu_data['categories']['General'] = all_items
        
        menu_data['metadata'] = {
            'source_url': base_url,
            'total_items': len(menu_data['items']),
            'categories_found': len(menu_data['categories'])
        }
        
        return menu_data
    
    def _extract_items_from_section(self, section):
        """Extract items from a menu section"""
        items = []
        
        # Look for potential item containers
        item_elements = section.find_all(['div', 'li', 'tr'], 
                                       class_=re.compile(r'item|product|dish', re.I))
        
        for element in item_elements:
            text = element.get_text().strip()
            if text and len(text) > 5 and len(text) < 200:  # Reasonable item length
                items.append({
                    'name': text[:50],  # Truncate long names
                    'description': text,
                    'price': self._extract_price(text)
                })
        
        return items
    
    def _extract_items_fallback(self, soup):
        """Fallback item extraction"""
        items = []
        
        # Look for any elements with price indicators
        price_elements = soup.find_all(text=re.compile(r'\$\d+'))
        
        for element in price_elements:
            parent = element.parent
            if parent:
                text = parent.get_text().strip()
                if len(text) > 5:
                    items.append({
                        'name': text[:50],
                        'description': text,
                        'price': self._extract_price(text)
                    })
        
        return items[:20]  # Limit to 20 items for fallback
    
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
    
    def extract_menu(self, website_url: str, restaurant_name: Optional[str] = None, force_menu_url: Optional[str] = None) -> MenuExtractionResult:
        """Main menu extraction method"""
        
        start_time = datetime.now()
        
        try:
            # Use forced URL or find menu page
            menu_url = force_menu_url or self.find_menu_page(website_url)
            
            # Get page content
            response = self.destroyer.get(menu_url)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch page: {response.status_code}")
            
            page_content = response.text
            
            # Try API detection first
            api_endpoints = self.detect_api_endpoints(page_content, menu_url)
            menu_data = None
            
            if api_endpoints:
                for endpoint in api_endpoints[:3]:
                    try:
                        api_response = self.destroyer.get(endpoint)
                        if api_response.status_code == 200:
                            api_data = api_response.json()
                            if self._validate_menu_api_data(api_data):
                                menu_data = api_data
                                break
                    except Exception:
                        continue
            
            # Fall back to DOM scraping
            if not menu_data:
                menu_data = self.scrape_dom_content(page_content, menu_url)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            items_found = len(menu_data.get('items', []))
            categories_found = len(menu_data.get('categories', {}))
            
            confidence_score = self._calculate_confidence_score(
                items_found, categories_found, menu_data
            )
            
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

# Initialize the scraper instance
scraper = RestaurantMenuScraper()

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
    try:
        destroyer = CloudDestroyer()
        test_response = destroyer.get("https://httpbin.org/get")
        status = "healthy" if test_response.status_code == 200 else "degraded"
    except:
        status = "error"
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.post("/restaurant/extract", response_model=MenuExtractionResult)
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
    
    result = scraper.extract_menu(
        website_url=str(request.website_url),
        restaurant_name=request.restaurant_name,
        force_menu_url=request.force_menu_url
    )
    
    logger.info(f"Restaurant extraction: {result.success}, {result.items_found} items")
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
            
            # Step 2: Extract menu data using CloudDestroyer
            menu_data = self._scrape_menu_data(menu_url)
            
            # Step 3: Process and structure the data
            processed_data = self._process_menu_data(menu_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return MenuExtractionResult(
                success=True,
                restaurant_name=restaurant_name or self._extract_restaurant_name(menu_data),
                website_url=website_url,
                menu_url=menu_url,
                extraction_method=f"clouddestroyer_{detection_method}",
                items_found=len(processed_data.get('items', [])),
                categories_found=len(processed_data.get('categories', [])),
                processing_time_seconds=processing_time,
                menu_data=processed_data,
                confidence_score=self._calculate_confidence(processed_data)
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return MenuExtractionResult(
                success=False,
                restaurant_name=restaurant_name or "Unknown",
                website_url=website_url,
                menu_url=website_url,
                extraction_method="failed",
                items_found=0,
                categories_found=0,
                processing_time_seconds=processing_time,
                menu_data={},
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _scrape_menu_data(self, menu_url: str) -> dict:
        """Scrape menu data using CloudDestroyer"""
        
        # Try API endpoint discovery first (like Bubba's 33 success)
        api_data = self._try_api_discovery(menu_url)
        if api_data:
            return {"source": "api", "data": api_data}
        
        # Fallback to DOM scraping with CloudDestroyer
        dom_data = self._scrape_dom_menu(menu_url)
        return {"source": "dom", "data": dom_data}
    
    def _try_api_discovery(self, menu_url: str) -> Optional[dict]:
        """Try to discover API endpoints like we did with Bubba's 33"""
        
        try:
            response = self.destroyer.get(menu_url)
            if response.status_code != 200:
                return None
            
            # Look for API calls in the page source
            html_content = response.text
            
            # Common API patterns to look for
            api_patterns = [
                r'api[/\w]*menu', r'api[/\w]*product', r'api[/\w]*item',
                r'menu[/\w]*api', r'product[/\w]*api', r'item[/\w]*api',
                r'/api/v\d+/menu', r'/api/menu', r'/menu/api'
            ]
            
            base_domain = urlparse(menu_url).scheme + '://' + urlparse(menu_url).netloc
            
            for pattern in api_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    api_url = urljoin(base_domain, '/' + match.strip('/'))
                    
                    try:
                        api_response = self.destroyer.get(api_url)
                        if api_response.status_code == 200:
                            try:
                                api_json = api_response.json()
                                if self._is_menu_api_response(api_json):
                                    return api_json
                            except:
                                continue
                    except:
                        continue
                        
        except Exception:
            pass
        
        return None
    
    def _scrape_dom_menu(self, menu_url: str) -> dict:
        """Scrape menu from DOM using CloudDestroyer"""
        
        try:
            response = self.destroyer.get(menu_url)
            
            if response.status_code != 200:
                raise Exception(f"Failed to load menu page: {response.status_code}")
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for menu items using common patterns
            menu_items = []
            categories = set()
            
            # Pattern 1: Look for structured menu sections
            menu_sections = soup.find_all(['div', 'section'], 
                                        class_=re.compile(r'menu|food|item|product', re.I))
            
            for section in menu_sections:
                category = self._extract_category_name(section)
                items = self._extract_items_from_section(section)
                
                if items:
                    categories.add(category)
                    for item in items:
                        item['category'] = category
                    menu_items.extend(items)
            
            # Pattern 2: Look for list-based menus
            if not menu_items:
                menu_lists = soup.find_all(['ul', 'ol'], class_=re.compile(r'menu|food|item', re.I))
                for menu_list in menu_lists:
                    items = self._extract_items_from_list(menu_list)
                    menu_items.extend(items)
            
            # Pattern 3: Look for table-based menus
            if not menu_items:
                menu_tables = soup.find_all('table')
                for table in menu_tables:
                    if self._looks_like_menu_table(table):
                        items = self._extract_items_from_table(table)
                        menu_items.extend(items)
            
            return {
                'items': menu_items,
                'categories': list(categories),
                'raw_html_length': len(response.text)
            }
            
        except Exception as e:
            raise Exception(f"DOM scraping failed: {str(e)}")
    
    def _extract_category_name(self, section) -> str:
        """Extract category name from menu section"""
        
        # Look for headings
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
            heading = section.find(tag)
            if heading:
                text = heading.get_text().strip()
                if text and len(text) < 50:  # Reasonable category name length
                    return text
        
        # Look for class names that might indicate category
        classes = section.get('class', [])
        for cls in classes:
            if any(word in cls.lower() for word in ['category', 'section', 'menu']):
                return cls.replace('-', ' ').replace('_', ' ').title()
        
        return "Menu Items"
    
    def _extract_items_from_section(self, section) -> list:
        """Extract individual menu items from a section"""
        
        items = []
        
        # Look for item containers
        item_containers = section.find_all(['div', 'li', 'tr'], 
                                         class_=re.compile(r'item|product|dish|food', re.I))
        
        for container in item_containers:
            item_data = self._parse_menu_item(container)
            if item_data:
                items.append(item_data)
        
        return items
    
    def _extract_items_from_list(self, menu_list) -> list:
        """Extract menu items from list elements"""
        
        items = []
        list_items = menu_list.find_all('li')
        
        for li in list_items:
            item_data = self._parse_menu_item(li)
            if item_data:
                items.append(item_data)
        
        return items
    
    def _looks_like_menu_table(self, table) -> bool:
        """Check if table looks like it contains menu data"""
        
        rows = table.find_all('tr')
        if len(rows) < 2:  # Need header + at least one data row
            return False
        
        # Check if table has price-like content
        table_text = table.get_text().lower()
        price_indicators = ['$', 'price', 'cost', '.99', '.95']
        
        return any(indicator in table_text for indicator in price_indicators)
    
    def _extract_items_from_table(self, table) -> list:
        """Extract menu items from table"""
        
        items = []
        rows = table.find_all('tr')
        
        # Skip header row
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                item_data = self._parse_table_row(cells)
                if item_data:
                    items.append(item_data)
        
        return items
    
    def _parse_table_row(self, cells) -> Optional[dict]:
        """Parse menu item from table row"""
        
        try:
            name = cells[0].get_text().strip()
            price_text = cells[-1].get_text().strip()  # Assume price is last column
            
            # Extract price
            price = None
            price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
            if price_match:
                try:
                    price = float(price_match.group(1))
                except:
                    pass
            
            # Description might be in middle columns
            description = ""
            if len(cells) > 2:
                desc_parts = [cell.get_text().strip() for cell in cells[1:-1]]
                description = " ".join(desc_parts)
            
            return {
                'name': name,
                'price': price,
                'description': description,
                'category': 'Menu Items'
            }
            
        except Exception:
            return None
    
    def _parse_menu_item(self, container) -> Optional[dict]:
        """Parse individual menu item from HTML container"""
        
        try:
            # Extract item name
            name = None
            for tag in ['h3', 'h4', 'h5', 'strong', 'b']:
                name_elem = container.find(tag)
                if name_elem:
                    name = name_elem.get_text().strip()
                    break
            
            if not name:
                # Look for the first meaningful text node
                text_nodes = container.find_all(text=True)
                for text in text_nodes:
                    text = text.strip()
                    if text and len(text) > 3 and len(text) < 100:
                        name = text
                        break
            
            if not name:
                return None
            
            # Extract price
            price = None
            price_patterns = [r'\$[\d,]+\.?\d*', r'[\d,]+\.?\d*']
            
            full_text = container.get_text()
            for pattern in price_patterns:
                price_match = re.search(pattern, full_text)
                if price_match:
                    price_text = price_match.group()
                    try:
                        price = float(re.sub(r'[^\d.]', '', price_text))
                        break
                    except:
                        continue
            
            # Extract description
            description = None
            desc_elem = container.find(['p', 'span', 'div'], class_=re.compile(r'desc|detail', re.I))
            if desc_elem:
                description = desc_elem.get_text().strip()
            
            return {
                'name': name,
                'price': price,
                'description': description,
                'raw_html': str(container)[:500]  # First 500 chars for debugging
            }
            
        except Exception:
            return None
    
    def _process_menu_data(self, raw_data: dict) -> dict:
        """Process and clean extracted menu data"""
        
        if raw_data.get('source') == 'api':
            return self._process_api_data(raw_data['data'])
        else:
            return self._process_dom_data(raw_data['data'])
    
    def _process_api_data(self, api_data: dict) -> dict:
        """Process API-extracted data (like Bubba's 33 format)"""
        
        # Handle Bubba's 33 style API response
        if 'categories' in api_data:
            return {
                'categories': [cat.get('name', 'Unknown') for cat in api_data.get('categories', [])],
                'items': self._flatten_api_items(api_data.get('categories', [])),
                'source': 'api',
                'confidence': 0.95
            }
        
        # Handle direct items array
        if 'items' in api_data:
            return {
                'categories': list(set(item.get('category', 'Menu Items') for item in api_data['items'])),
                'items': api_data['items'],
                'source': 'api',
                'confidence': 0.90
            }
        
        return {'categories': [], 'items': [], 'source': 'api', 'confidence': 0.0}
    
    def _flatten_api_items(self, categories: list) -> list:
        """Flatten API category structure into items list"""
        
        items = []
        for category in categories:
            category_name = category.get('name', 'Unknown')
            
            for item in category.get('items', []):
                items.append({
                    'name': item.get('name', 'Unknown Item'),
                    'price': item.get('price', item.get('base_price')),
                    'description': item.get('description', ''),
                    'category': category_name,
                    'id': item.get('id'),
                    'source': 'api'
                })
        
        return items
    
    def _process_dom_data(self, dom_data: dict) -> dict:
        """Process DOM-scraped data"""
        
        return {
            'categories': dom_data.get('categories', []),
            'items': dom_data.get('items', []),
            'source': 'dom',
            'confidence': 0.75 if dom_data.get('items') else 0.25
        }
    
    def _calculate_confidence(self, processed_data: dict) -> float:
        """Calculate confidence score for extraction"""
        
        base_confidence = processed_data.get('confidence', 0.5)
        
        # Boost confidence based on items found
        items_count = len(processed_data.get('items', []))
        if items_count > 50:
            base_confidence += 0.2
        elif items_count > 20:
            base_confidence += 0.1
        elif items_count > 5:
            base_confidence += 0.05
        
        # Boost confidence if we have prices
        items_with_prices = sum(1 for item in processed_data.get('items', []) 
                               if item.get('price'))
        if items_with_prices > 0:
            price_ratio = items_with_prices / items_count
            base_confidence += price_ratio * 0.2
        
        return min(base_confidence, 1.0)
    
    def _extract_restaurant_name(self, menu_data: dict) -> str:
        """Extract restaurant name from menu data"""
        
        # Try to extract from API data
        if menu_data.get('source') == 'api':
            api_data = menu_data.get('data', {})
            if 'restaurant_name' in api_data:
                return api_data['restaurant_name']
            if 'name' in api_data:
                return api_data['name']
        
        return "Unknown Restaurant"
    
    def _is_menu_api_response(self, json_data: dict) -> bool:
        """Check if JSON response contains menu data"""
        
        # Check for common menu API structures
        menu_indicators = ['menu', 'items', 'categories', 'products', 'food']
        
        for indicator in menu_indicators:
            if indicator in json_data:
                data = json_data[indicator]
                if isinstance(data, list) and len(data) > 0:
                    return True
                if isinstance(data, dict) and data:
                    return True
        
        return False

# Database Integration
def connect_to_food_app_db():
    """Connect to FoodFinder database"""
    try:
        conn = pyodbc.connect(
            'DRIVER={SQL Server};'
            'SERVER=localhost\\SqlExpressDev01;'
            'DATABASE=FoodFinder;'
            'UID=SaltyUser;'
            'PWD=saltypass'
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

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
    try:
        destroyer = CloudDestroyer()
        test_response = destroyer.get("https://httpbin.org/get")
        status = "healthy" if test_response.status_code == 200 else "degraded"
    except:
        status = "error"
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.post("/restaurant/extract", response_model=MenuExtractionResult)
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
    
    scraper = RestaurantMenuScraper()
    
    result = scraper.extract_menu(
        website_url=str(request.website_url),
        restaurant_name=request.restaurant_name,
        force_menu_url=request.force_menu_url
    )
    
    logger.info(f"Restaurant extraction: {result.success}, {result.items_found} items")
    return result

@app.post("/restaurant/quick")
async def quick_menu_check(
    request: QuickMenuRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Quick check if website has extractable menu data
    Faster endpoint for menu availability checking
    """
    
    detector = RestaurantMenuDetector()
    
    try:
        menu_url, method = detector.find_menu_page(str(request.website_url))
        
        # Quick test of menu page
        response = detector.destroyer.get(menu_url)
        
        return {
            "has_menu": response.status_code == 200,
            "menu_url": menu_url,
            "detection_method": method,
            "response_code": response.status_code,
            "page_size": len(response.text) if response.status_code == 200 else 0,
            "processing_time": 0.5  # Quick check
        }
        
    except Exception as e:
        return {
            "has_menu": False,
            "menu_url": str(request.website_url),
            "detection_method": "failed",
            "response_code": 0,
            "page_size": 0,
            "error": str(e)
        }

@app.post("/restaurant/save")
async def save_menu_to_database(
    extraction_result: MenuExtractionResult,
    api_key: str = Depends(verify_api_key)
):
    """
    Save extracted menu data to FoodFinder database
    Call this after successful menu extraction
    """
    
    if not extraction_result.success:
        raise HTTPException(status_code=400, detail="Cannot save failed extraction")
    
    try:
        conn = connect_to_food_app_db()
        cursor = conn.cursor()
        
        # Insert restaurant record
        cursor.execute("""
            MERGE Restaurants AS target
            USING (VALUES (?, ?, ?)) AS source (Name, WebsiteUrl, MenuUrl)
            ON target.WebsiteUrl = source.WebsiteUrl
            WHEN MATCHED THEN
                UPDATE SET Name = source.Name, MenuUrl = source.MenuUrl, LastUpdated = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (Name, WebsiteUrl, MenuUrl, CreatedDate, LastUpdated)
                VALUES (source.Name, source.WebsiteUrl, source.MenuUrl, GETDATE(), GETDATE());
        """, 
        extraction_result.restaurant_name,
        extraction_result.website_url,
        extraction_result.menu_url)
        
        # Get restaurant ID
        cursor.execute("SELECT RestaurantId FROM Restaurants WHERE WebsiteUrl = ?", 
                      extraction_result.website_url)
        restaurant_id = cursor.fetchone()[0]
        
        # Clear existing menu items for this restaurant
        cursor.execute("DELETE FROM MenuItems WHERE RestaurantId = ?", restaurant_id)
        
        # Insert menu items
        items_inserted = 0
        for item in extraction_result.menu_data.get('items', []):
            cursor.execute("""
                INSERT INTO MenuItems (RestaurantId, ItemName, Category, Price, Description, CreatedDate)
                VALUES (?, ?, ?, ?, ?, GETDATE())
            """,
            restaurant_id,
            item.get('name', 'Unknown Item'),
            item.get('category', 'Menu Items'),
            item.get('price'),
            item.get('description', ''))
            
            items_inserted += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "restaurant_id": restaurant_id,
            "items_saved": items_inserted,
            "categories_saved": extraction_result.categories_found,
            "message": f"Successfully saved {items_inserted} menu items for {extraction_result.restaurant_name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")

# Usage Examples for Food App Integration
@app.get("/examples")
async def usage_examples():
    """
    Examples of how to integrate with your Food App
    """
    
    return {
        "integration_examples": {
            "basic_scrape": {
                "description": "Basic menu extraction from restaurant website",
                "endpoint": "POST /restaurant/extract",
                "example_request": {
                    "website_url": "https://bubbas33.com",
                    "restaurant_name": "Bubba's 33"
                },
                "curl_example": """
curl -X POST "http://localhost:8000/restaurant/extract" \\
     -H "Authorization: Bearer demo_key_123" \\
     -H "Content-Type: application/json" \\
     -d '{"website_url": "https://bubbas33.com", "restaurant_name": "Bubbas 33"}'
                """
            },
            "quick_check": {
                "description": "Quick check if restaurant has menu data",
                "endpoint": "POST /restaurant/quick",
                "example_request": {
                    "website_url": "https://example-restaurant.com"
                }
            },
            "force_menu_url": {
                "description": "Force specific menu URL if auto-detection fails",
                "endpoint": "POST /restaurant/extract", 
                "example_request": {
                    "website_url": "https://restaurant.com",
                    "force_menu_url": "https://restaurant.com/our-food-menu"
                }
            }
        },
        "food_app_workflow": {
            "step_1": "Call /restaurant/quick to check if menu exists",
            "step_2": "If menu exists, call /restaurant/extract for full data",
            "step_3": "Call /restaurant/save to store in your database",
            "step_4": "Use menu data in your Food App interface"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")