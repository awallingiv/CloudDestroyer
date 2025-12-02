#!/usr/bin/env python3
"""
Test just the extract_menu method directly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the API module
import importlib.util
spec = importlib.util.spec_from_file_location("api", "api.py")
api_module = importlib.util.module_from_spec(spec)
sys.modules["api"] = api_module
spec.loader.exec_module(api_module)

def test_extract_menu_directly():
    """Test the extract_menu method directly"""
    print("Testing extract_menu method directly...")
    
    try:
        # Create scraper instance
        scraper = api_module.RestaurantMenuScraper()
        
        print("✓ Scraper created successfully")
        
        # Test extract_menu method
        print("Calling extract_menu...")
        result = scraper.extract_menu(
            website_url="https://bubbas33.com",
            restaurant_name="Bubba's 33"
        )
        
        print("✓ extract_menu completed successfully")
        print(f"Result type: {type(result)}")
        print(f"Success: {result.success}")
        print(f"Items found: {result.items_found}")
        print(f"Menu URL: {result.menu_url}")
        print(f"Processing time: {result.processing_time_seconds}")
        
        # Check menu data
        menu_data = result.menu_data
        if menu_data and isinstance(menu_data, dict):
            items = menu_data.get('items', [])
            categories = menu_data.get('categories', [])
            print(f"Menu items: {len(items)}")
            print(f"Categories: {categories}")
            
            # Show first few items
            if items:
                print("\nFirst few items:")
                for item in items[:3]:
                    print(f"  - {item}")
        
        return result
        
    except Exception as e:
        print(f"✗ Error in extract_menu: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_extract_menu_directly()