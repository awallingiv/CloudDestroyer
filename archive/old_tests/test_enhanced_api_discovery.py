#!/usr/bin/env python3
"""
Test the enhanced JavaScript API discovery and menu extraction for Bubba's 33
"""

import sys
import time
import logging
from api import RestaurantMenuScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_menu_extraction():
    """Test enhanced menu extraction with JavaScript API discovery"""
    
    print("=" * 80)
    print("TESTING ENHANCED JAVASCRIPT API DISCOVERY & MENU EXTRACTION")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        with RestaurantMenuScraper() as scraper:
            print(f"\n1. Testing enhanced API discovery and extraction...")
            
            result = scraper.extract_menu("https://bubbas33.com", "Bubba's 33")
            
            total_time = time.time() - start_time
            
            print(f"   ✓ Extraction completed in {total_time:.1f}s")
            
            # Show detailed results
            print(f"\n2. Enhanced Extraction Results:")
            print(f"   • Success: {result.success}")
            print(f"   • Items found: {result.items_found}")
            print(f"   • Categories found: {result.categories_found}")
            print(f"   • Confidence score: {result.confidence_score}")
            print(f"   • Menu URL: {result.menu_url}")
            print(f"   • Processing time: {result.processing_time_seconds:.1f}s")
            
            if result.error_message:
                print(f"   • Error: {result.error_message}")
            
            # Show sample menu items if found
            if result.menu_data and result.menu_data.get('items'):
                print(f"\n3. Sample Menu Items:")
                items = result.menu_data['items'][:5]  # Show first 5 items
                for i, item in enumerate(items, 1):
                    name = item.get('name', 'Unknown')
                    price = item.get('price', 'No price')
                    desc = item.get('description', '')[:50] + '...' if item.get('description', '') else 'No description'
                    print(f"   {i}. {name}")
                    print(f"      Price: {price}")
                    print(f"      Desc: {desc}")
                    print()
            
            # Show categories if found
            if result.menu_data and result.menu_data.get('categories'):
                print(f"4. Categories Found:")
                categories = result.menu_data['categories']
                if isinstance(categories, dict):
                    for cat_name, count in categories.items():
                        print(f"   • {cat_name}: {count} items")
                elif isinstance(categories, list):
                    for cat in categories:
                        print(f"   • {cat}")
                print()
                        
            # Success criteria for enhanced system
            enhanced_criteria = [
                ("Process completed successfully", result.success),
                ("Reasonable processing time", total_time < 300),
                ("Found actual menu items", result.items_found >= 7),  # Enhanced requirement
                ("Good confidence score", result.confidence_score > 0.3),
                ("Found categories", result.categories_found > 0)
            ]
            
            print(f"5. Enhanced Success Criteria:")
            all_passed = True
            for criteria, passed in enhanced_criteria:
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"   {status} {criteria}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print(f"\n🎉 ALL ENHANCED TESTS PASSED!")
                print(f"   JavaScript API discovery is working correctly!")
            else:
                print(f"\n⚠️  Some enhanced tests failed.")
                if result.items_found < 7:
                    print(f"   → Need to improve menu item extraction (found {result.items_found}, need 7+)")
                if result.confidence_score <= 0.3:
                    print(f"   → Need to improve confidence scoring")
                
            return result
            
    except Exception as e:
        total_time = time.time() - start_time
        print(f"\n❌ Enhanced test failed after {total_time:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Starting enhanced JavaScript API discovery test for Bubba's 33...")
    
    try:
        result = test_enhanced_menu_extraction()
        
        if result and result.success and result.items_found >= 7:
            print(f"\n🚀 Enhanced menu extraction SUCCESS!")
            print(f"   Found {result.items_found} menu items with JavaScript API discovery!")
            sys.exit(0)
        elif result and result.success:
            print(f"\n⚠️  Partial success - found {result.items_found} items (need 7+)")
            sys.exit(1)
        else:
            print(f"\n❌ Enhanced extraction failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user (Ctrl+C)")
        sys.exit(130)