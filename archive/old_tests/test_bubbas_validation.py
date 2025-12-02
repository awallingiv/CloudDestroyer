#!/usr/bin/env python3
"""
Bubba's 33 Menu Extraction Validation Test

This script validates the CloudDestroyer menu extraction against expected benchmarks:
- Expected items: ~102 menu items
- Expected categories: ~13 categories
- Target confidence score: >= 0.85
- Target processing time: < 60 seconds

Usage:
    python test_bubbas_validation.py
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from api import RestaurantMenuScraper, MenuExtractionResult

# ============================================================================
# VALIDATION BENCHMARKS
# ============================================================================

BENCHMARKS = {
    'min_items': 80,           # Minimum acceptable items (80% of 102)
    'target_items': 102,       # Target items from README
    'min_categories': 10,      # Minimum acceptable categories (77% of 13)
    'target_categories': 13,   # Target categories from README
    'min_confidence': 0.70,    # Minimum acceptable confidence
    'target_confidence': 0.85, # Target confidence score
    'max_time_seconds': 120,   # Maximum acceptable processing time
    'target_time_seconds': 60, # Target processing time
}

# Known Bubba's 33 menu categories (for validation)
KNOWN_CATEGORIES = [
    'appetizers', 'wings', 'burgers', 'sandwiches', 'pizza', 
    'tacos', 'salads', 'entrees', 'pasta', 'desserts',
    'kids', 'beverages', 'sides'
]


def print_header(text: str, char: str = "="):
    """Print a formatted header"""
    print()
    print(char * 70)
    print(f"  {text}")
    print(char * 70)


def print_metric(name: str, value: Any, target: Any = None, min_val: Any = None):
    """Print a metric with pass/fail indicator"""
    status = "✅"
    
    if target is not None:
        if isinstance(value, (int, float)) and isinstance(target, (int, float)):
            if value >= target:
                status = "✅"
            elif min_val is not None and value >= min_val:
                status = "⚠️"
            else:
                status = "❌"
        elif value == target:
            status = "✅"
        else:
            status = "⚠️"
    
    target_str = f" (target: {target})" if target is not None else ""
    print(f"  {status} {name}: {value}{target_str}")


def validate_menu_data(menu_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Validate extracted menu data structure and content"""
    issues = []
    warnings = []
    
    # Check basic structure
    if not isinstance(menu_data, dict):
        issues.append("Menu data is not a dictionary")
        return False, {'issues': issues, 'warnings': warnings}
    
    items = menu_data.get('items', [])
    categories = menu_data.get('categories', {})
    
    # Validate items
    if not items:
        issues.append("No menu items found")
    else:
        # Check item structure
        items_with_names = sum(1 for i in items if i.get('name'))
        items_with_prices = sum(1 for i in items if i.get('price'))
        items_with_categories = sum(1 for i in items if i.get('category'))
        
        if items_with_names < len(items) * 0.9:
            warnings.append(f"Only {items_with_names}/{len(items)} items have names")
        
        if items_with_prices < len(items) * 0.7:
            warnings.append(f"Only {items_with_prices}/{len(items)} items have prices")
    
    # Validate categories
    if not categories:
        warnings.append("No categories found")
    else:
        # Check for known Bubba's 33 categories
        found_known = 0
        for known_cat in KNOWN_CATEGORIES:
            for cat_name in categories.keys():
                if known_cat in cat_name.lower():
                    found_known += 1
                    break
        
        if found_known < 5:
            warnings.append(f"Only {found_known} known Bubba's 33 categories found")
    
    # Check for duplicate items
    seen_names = set()
    duplicates = 0
    for item in items:
        name = item.get('name', '').lower().strip()
        if name in seen_names:
            duplicates += 1
        seen_names.add(name)
    
    if duplicates > 5:
        warnings.append(f"Found {duplicates} potential duplicate items")
    
    is_valid = len(issues) == 0
    
    return is_valid, {
        'issues': issues,
        'warnings': warnings,
        'items_with_names': items_with_names if items else 0,
        'items_with_prices': items_with_prices if items else 0,
        'duplicates': duplicates
    }


def analyze_categories(menu_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze category distribution"""
    categories = menu_data.get('categories', {})
    items = menu_data.get('items', [])
    
    # Build category stats
    category_stats = {}
    
    if isinstance(categories, dict):
        for cat_name, cat_items in categories.items():
            if isinstance(cat_items, list):
                category_stats[cat_name] = len(cat_items)
            elif isinstance(cat_items, int):
                category_stats[cat_name] = cat_items
    
    # Also count from items
    item_categories = {}
    for item in items:
        cat = item.get('category', 'Uncategorized')
        item_categories[cat] = item_categories.get(cat, 0) + 1
    
    return {
        'from_categories_dict': category_stats,
        'from_items': item_categories,
        'total_categories': len(category_stats) or len(item_categories)
    }


def run_extraction_test() -> Tuple[bool, MenuExtractionResult, Dict[str, Any]]:
    """Run the menu extraction and return results with validation"""
    
    print_header("BUBBA'S 33 MENU EXTRACTION TEST")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  URL: https://bubbas33.com")
    print()
    
    start_time = time.time()
    result = None
    validation = {}
    
    try:
        print("  🔄 Initializing CloudDestroyer scraper...")
        
        with RestaurantMenuScraper() as scraper:
            print("  🌐 Starting menu extraction...")
            print()
            
            result = scraper.extract_menu(
                website_url="https://bubbas33.com",
                restaurant_name="Bubba's 33"
            )
            
    except Exception as e:
        print(f"  ❌ Extraction failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False, None, {'error': str(e)}
    
    total_time = time.time() - start_time
    
    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    
    print_header("EXTRACTION RESULTS")
    
    print_metric("Success", result.success, target=True)
    print_metric("Restaurant Name", result.restaurant_name)
    print_metric("Menu URL", result.menu_url)
    print_metric("Items Found", result.items_found, 
                 target=BENCHMARKS['target_items'], 
                 min_val=BENCHMARKS['min_items'])
    print_metric("Categories Found", result.categories_found,
                 target=BENCHMARKS['target_categories'],
                 min_val=BENCHMARKS['min_categories'])
    print_metric("Confidence Score", f"{result.confidence_score:.2f}",
                 target=BENCHMARKS['target_confidence'],
                 min_val=BENCHMARKS['min_confidence'])
    print_metric("Processing Time", f"{result.processing_time_seconds:.1f}s",
                 target=f"<{BENCHMARKS['target_time_seconds']}s")
    print_metric("Total Test Time", f"{total_time:.1f}s")
    
    # ========================================================================
    # VALIDATE MENU DATA
    # ========================================================================
    
    print_header("DATA VALIDATION")
    
    is_valid, validation = validate_menu_data(result.menu_data)
    
    if validation.get('issues'):
        print("  Issues:")
        for issue in validation['issues']:
            print(f"    ❌ {issue}")
    
    if validation.get('warnings'):
        print("  Warnings:")
        for warning in validation['warnings']:
            print(f"    ⚠️ {warning}")
    
    if is_valid and not validation.get('warnings'):
        print("  ✅ All validation checks passed!")
    
    # ========================================================================
    # CATEGORY ANALYSIS
    # ========================================================================
    
    print_header("CATEGORY ANALYSIS")
    
    cat_analysis = analyze_categories(result.menu_data)
    
    print(f"  Total Categories: {cat_analysis['total_categories']}")
    print()
    
    if cat_analysis['from_items']:
        print("  Items per category:")
        sorted_cats = sorted(cat_analysis['from_items'].items(), 
                            key=lambda x: x[1], reverse=True)
        for cat_name, count in sorted_cats[:15]:
            known = "✓" if any(k in cat_name.lower() for k in KNOWN_CATEGORIES) else " "
            print(f"    {known} {cat_name}: {count} items")
    
    # ========================================================================
    # SAMPLE ITEMS
    # ========================================================================
    
    print_header("SAMPLE MENU ITEMS")
    
    items = result.menu_data.get('items', [])
    
    if items:
        for i, item in enumerate(items[:10]):
            name = item.get('name', 'Unknown')
            price = item.get('price', 'N/A')
            category = item.get('category', 'N/A')
            print(f"  {i+1}. {name}")
            print(f"     Price: {price} | Category: {category}")
    else:
        print("  No items to display")
    
    # ========================================================================
    # FINAL ASSESSMENT
    # ========================================================================
    
    print_header("FINAL ASSESSMENT", char="*")
    
    # Calculate overall score
    score = 0
    max_score = 100
    
    # Items score (40 points max)
    items_ratio = min(result.items_found / BENCHMARKS['target_items'], 1.0)
    items_score = int(items_ratio * 40)
    score += items_score
    print(f"  Items Score: {items_score}/40 ({result.items_found}/{BENCHMARKS['target_items']} items)")
    
    # Categories score (20 points max)
    cats_ratio = min(result.categories_found / BENCHMARKS['target_categories'], 1.0)
    cats_score = int(cats_ratio * 20)
    score += cats_score
    print(f"  Categories Score: {cats_score}/20 ({result.categories_found}/{BENCHMARKS['target_categories']} categories)")
    
    # Confidence score (25 points max)
    conf_ratio = min(result.confidence_score / BENCHMARKS['target_confidence'], 1.0)
    conf_score = int(conf_ratio * 25)
    score += conf_score
    print(f"  Confidence Score: {conf_score}/25 ({result.confidence_score:.2f}/{BENCHMARKS['target_confidence']})")
    
    # Time score (15 points max)
    if result.processing_time_seconds <= BENCHMARKS['target_time_seconds']:
        time_score = 15
    elif result.processing_time_seconds <= BENCHMARKS['max_time_seconds']:
        time_ratio = 1 - ((result.processing_time_seconds - BENCHMARKS['target_time_seconds']) / 
                         (BENCHMARKS['max_time_seconds'] - BENCHMARKS['target_time_seconds']))
        time_score = int(time_ratio * 15)
    else:
        time_score = 0
    score += time_score
    print(f"  Time Score: {time_score}/15 ({result.processing_time_seconds:.1f}s)")
    
    print()
    print(f"  {'='*40}")
    print(f"  TOTAL SCORE: {score}/{max_score}")
    print(f"  {'='*40}")
    
    # Determine pass/fail
    passed = (
        result.items_found >= BENCHMARKS['min_items'] and
        result.categories_found >= BENCHMARKS['min_categories'] and
        result.confidence_score >= BENCHMARKS['min_confidence']
    )
    
    print()
    if passed:
        if score >= 85:
            print("  🎉 EXCELLENT! Extraction meets all targets!")
        elif score >= 70:
            print("  ✅ PASSED! Extraction meets minimum requirements.")
        else:
            print("  ⚠️ PASSED with warnings. Some targets not met.")
    else:
        print("  ❌ FAILED! Extraction does not meet minimum requirements.")
    
    # ========================================================================
    # SAVE RESULTS
    # ========================================================================
    
    output_file = f"bubbas33_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'url': 'https://bubbas33.com',
        'success': result.success,
        'items_found': result.items_found,
        'categories_found': result.categories_found,
        'confidence_score': result.confidence_score,
        'processing_time_seconds': result.processing_time_seconds,
        'total_test_time_seconds': total_time,
        'score': score,
        'passed': passed,
        'benchmarks': BENCHMARKS,
        'validation': validation,
        'category_analysis': cat_analysis,
        'menu_data': result.menu_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print()
    print(f"  📄 Results saved to: {output_file}")
    print()
    
    return passed, result, validation


def main():
    """Main entry point"""
    passed, result, validation = run_extraction_test()
    
    # Return exit code based on pass/fail
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

