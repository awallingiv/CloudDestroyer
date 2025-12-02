#!/usr/bin/env python3
"""
Debug API endpoint to identify exactly where the crash occurs
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_extract_menu_step_by_step():
    """Debug each step of the menu extraction process"""
    
    try:
        # Import the API components
        from api import RestaurantMenuScraper
        
        logger.info("=== DEBUGGING MENU EXTRACTION ===")
        
        # Step 1: Initialize scraper
        logger.info("Step 1: Initializing scraper...")
        scraper = RestaurantMenuScraper()
        logger.info("✓ Scraper initialized successfully")
        
        # Step 2: Test URL and basic bypass
        test_url = "https://bubbas33.com"
        logger.info(f"Step 2: Testing basic bypass for {test_url}")
        response = scraper._get_with_orchestrator_bypass(test_url)
        
        if response:
            logger.info("✓ Basic bypass successful")
            # Check response type and content
            logger.info(f"Response type: {type(response)}")
            
            if hasattr(response, 'text'):
                content_length = len(response.text)
                logger.info(f"Response.text length: {content_length}")
                page_content = response.text
            elif isinstance(response, dict):
                content_length = len(response.get('text', ''))
                logger.info(f"Response dict text length: {content_length}")
                page_content = response.get('text', response.get('content', ''))
            else:
                logger.error(f"Unknown response format: {type(response)}")
                return
                
            if content_length > 1000:
                logger.info("✓ Substantial content retrieved")
            else:
                logger.warning(f"⚠ Limited content: {content_length} chars")
        else:
            logger.error("✗ Basic bypass failed")
            return
            
        # Step 3: Test find_menu_page
        logger.info("Step 3: Testing find_menu_page...")
        try:
            menu_url = scraper.find_menu_page(test_url)
            logger.info(f"✓ Found menu URL: {menu_url}")
        except Exception as e:
            logger.error(f"✗ find_menu_page failed: {e}")
            return
            
        # Step 4: Test detect_api_endpoints
        logger.info("Step 4: Testing detect_api_endpoints...")
        try:
            api_endpoints = scraper.detect_api_endpoints(page_content, test_url)
            logger.info(f"✓ API endpoints detected: {len(api_endpoints)} endpoints")
            for endpoint in api_endpoints[:3]:
                logger.info(f"  - {endpoint}")
        except Exception as e:
            logger.error(f"✗ detect_api_endpoints failed: {e}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Continue without API endpoints
            api_endpoints = []
            
        # Step 5: Test scrape_dom_content
        logger.info("Step 5: Testing scrape_dom_content...")
        try:
            menu_data = scraper.scrape_dom_content(page_content, test_url)
            logger.info(f"✓ DOM scraping completed")
            logger.info(f"Menu data type: {type(menu_data)}")
            logger.info(f"Menu data keys: {menu_data.keys() if isinstance(menu_data, dict) else 'Not a dict'}")
            
            if isinstance(menu_data, dict):
                items = menu_data.get('items', [])
                categories = menu_data.get('categories', [])
                logger.info(f"Items found: {len(items)}")
                logger.info(f"Categories found: {len(categories)}")
                
                # Show sample items
                if items:
                    logger.info("Sample items:")
                    for item in items[:3]:
                        if isinstance(item, dict):
                            name = item.get('name', 'Unknown')
                            price = item.get('price', 'N/A')
                            logger.info(f"  - {name}: ${price}")
                        
        except Exception as e:
            logger.error(f"✗ scrape_dom_content failed: {e}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return
            
        # Step 6: Test full extract_menu
        logger.info("Step 6: Testing full extract_menu method...")
        try:
            result = scraper.extract_menu(test_url, restaurant_name="Bubba's 33")
            logger.info(f"✓ Full extraction completed")
            logger.info(f"Result type: {type(result)}")
            
            if hasattr(result, 'success'):
                logger.info(f"Success: {result.success}")
                logger.info(f"Items found: {result.items_found}")
                logger.info(f"Categories found: {result.categories_found}")
                logger.info(f"Menu URL: {result.menu_url}")
            else:
                logger.info(f"Result content: {result}")
                
        except Exception as e:
            logger.error(f"✗ Full extract_menu failed: {e}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return
            
        logger.info("=== DEBUG COMPLETE - ALL STEPS PASSED ===")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR during debug: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    debug_extract_menu_step_by_step()