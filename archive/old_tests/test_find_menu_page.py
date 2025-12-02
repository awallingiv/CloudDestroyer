#!/usr/bin/env python3

import sys
sys.path.insert(0, 'C:\\Dev\\CloudDestroyer')

from api import RestaurantMenuScraper

def test_menu_page_discovery():
    print("Testing find_menu_page method directly...")
    
    api = RestaurantMenuScraper()
    try:
        result = api.find_menu_page("https://bubbas33.com")
        print(f"find_menu_page returned: {result}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        api.cleanup()

if __name__ == "__main__":
    test_menu_page_discovery()