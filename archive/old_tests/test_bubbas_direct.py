#!/usr/bin/env python3
"""
Direct test of Bubba's 33 menu extraction without API

Enhanced with validation against expected benchmarks:
- Target items: ~102
- Target categories: ~13
- Target confidence: >= 0.85
"""

import sys
import os

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from api import RestaurantMenuScraper
import json

# Validation benchmarks
BENCHMARKS = {
    'min_items': 80,
    'target_items': 102,
    'min_categories': 10,
    'target_categories': 13,
    'min_confidence': 0.70,
    'target_confidence': 0.85,
}

def test_bubbas_directly():
    """Test Bubba's 33 extraction directly without API"""
    
    print("Testing Bubba's 33 menu extraction directly...")
    print("=" * 60)
    print(f"Benchmarks: {BENCHMARKS['target_items']} items, {BENCHMARKS['target_categories']} categories")
    print("=" * 60)
    
    try:
        # Create scraper instance
        with RestaurantMenuScraper() as scraper:
            
            # Test the direct extraction
            result = scraper.extract_menu(
                website_url="https://bubbas33.com",
                restaurant_name="Bubba's 33"
            )
            
            print("✅ Extraction completed!")
            print()
            print("=== RESULTS ===")
            
            # Items validation
            items_status = "✅" if result.items_found >= BENCHMARKS['min_items'] else "❌"
            items_target = "✓" if result.items_found >= BENCHMARKS['target_items'] else ""
            print(f"{items_status} Items Found: {result.items_found} (target: {BENCHMARKS['target_items']}) {items_target}")
            
            # Categories validation
            cats_status = "✅" if result.categories_found >= BENCHMARKS['min_categories'] else "❌"
            cats_target = "✓" if result.categories_found >= BENCHMARKS['target_categories'] else ""
            print(f"{cats_status} Categories Found: {result.categories_found} (target: {BENCHMARKS['target_categories']}) {cats_target}")
            
            # Confidence validation
            conf_status = "✅" if result.confidence_score >= BENCHMARKS['min_confidence'] else "❌"
            conf_target = "✓" if result.confidence_score >= BENCHMARKS['target_confidence'] else ""
            print(f"{conf_status} Confidence Score: {result.confidence_score:.2f} (target: {BENCHMARKS['target_confidence']}) {conf_target}")
            
            print(f"   Processing Time: {result.processing_time_seconds:.1f}s")
            print(f"   Menu URL: {result.menu_url}")
            print(f"   Success: {result.success}")
            
            # Show menu data structure
            menu_data = result.menu_data
            print()
            print("=== MENU DATA STRUCTURE ===")
            print(f"Menu data type: {type(menu_data)}")
            if isinstance(menu_data, dict):
                print(f"Keys: {list(menu_data.keys())}")
                
                # Show items if they exist
                items = menu_data.get('items', [])
                print(f"Items count: {len(items)}")
                
                # Count items with prices
                items_with_prices = sum(1 for i in items if i.get('price'))
                print(f"Items with prices: {items_with_prices}")
                
                # Show price status note if available
                extraction_info = menu_data.get('_extraction_info', {})
                if extraction_info.get('price_status') == 'unavailable':
                    print(f"  Note: {extraction_info.get('price_note', 'Prices not available')}")
                
                if items:
                    print()
                    print("=== SAMPLE ITEMS (first 10) ===")
                    for i, item in enumerate(items[:10]):
                        name = item.get('name', 'Unknown')[:50]
                        price = item.get('price', 'N/A')
                        cat = item.get('category', 'N/A')
                        print(f"  {i+1}. {name} - {price} [{cat}]")
                
                # Show categories
                categories = menu_data.get('categories', {})
                if categories:
                    print()
                    print("=== CATEGORIES ===")
                    if isinstance(categories, dict):
                        for cat_name, cat_items in categories.items():
                            count = len(cat_items) if isinstance(cat_items, list) else cat_items
                            print(f"  - {cat_name}: {count} items")
                    elif isinstance(categories, list):
                        for cat in categories:
                            print(f"  - {cat}")
            
            # Show error if any
            if hasattr(result, 'error_message') and result.error_message:
                print()
                print(f"⚠️ Error: {result.error_message}")
            
            # Final assessment
            print()
            print("=" * 60)
            passed = (
                result.items_found >= BENCHMARKS['min_items'] and
                result.categories_found >= BENCHMARKS['min_categories'] and
                result.confidence_score >= BENCHMARKS['min_confidence']
            )
            
            if passed:
                if (result.items_found >= BENCHMARKS['target_items'] and 
                    result.categories_found >= BENCHMARKS['target_categories'] and
                    result.confidence_score >= BENCHMARKS['target_confidence']):
                    print("🎉 EXCELLENT! All targets met!")
                else:
                    print("✅ PASSED! Minimum requirements met.")
            else:
                print("❌ FAILED! Minimum requirements not met.")
            print("=" * 60)
            
            return passed
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bubbas_directly()
    sys.exit(0 if success else 1)