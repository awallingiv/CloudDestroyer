#!/usr/bin/env python3
"""
Test the RestaurantMenuScraper class directly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the updated RestaurantMenuScraper from api.py
import importlib.util
spec = importlib.util.spec_from_file_location("api", "api.py")
api_module = importlib.util.module_from_spec(spec)
sys.modules["api"] = api_module
spec.loader.exec_module(api_module)

def test_scraper_directly():
    """Test the RestaurantMenuScraper class directly"""
    print("Testing RestaurantMenuScraper directly...")
    
    try:
        # Initialize scraper with context manager
        with api_module.RestaurantMenuScraper() as scraper:
            
            # Test URL
            test_url = "https://bubbas33.com"
            
            print(f"Testing menu extraction for: {test_url}")
            
            # Try menu extraction
            result = scraper.extract_menu(test_url, restaurant_name="Bubba's 33")
            
            if result:
                print(f"Success!")
                print(f"Menu URL: {result.menu_url}")
                print(f"Items found: {len(result.items)}")
                print(f"Categories: {list(result.categories.keys())}")
                print(f"Confidence: {result.confidence_score}")
                print(f"Processing time: {result.processing_time_seconds}s")
                
                # Show first few items
                if result.items:
                    print("\nFirst few items:")
                    for item in result.items[:3]:
                        print(f"  - {item['name']} - ${item.get('price', 'N/A')}")
                        
            else:
                print("Menu extraction failed - no result")
                
    except Exception as e:
        print(f"Error testing scraper: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scraper_directly()