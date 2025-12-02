#!/usr/bin/env python3
"""
Test enhanced menu extraction system on Bubba's 33
Tests the new 15-attempt discovery system and comprehensive scoring
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from api import RestaurantMenuScraper
import json

def test_enhanced_bubbas_extraction():
    """Test enhanced Bubba's 33 extraction with new discovery system"""
    
    print("🚀 Testing Enhanced CloudDestroyer Menu System")
    print("=" * 60)
    print("Target: Bubba's 33 (https://bubbas33.com)")
    print("Testing: 15-attempt discovery + enhanced scoring")
    print("Success Threshold: 7+ menu items with structured pricing")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Create scraper with context manager for cleanup
        with RestaurantMenuScraper() as scraper:
            print("✅ Scraper initialized")
            
            # Test the enhanced find_menu_page method
            print("\n📍 Phase 1: Enhanced Menu Page Discovery")
            base_url = "https://bubbas33.com"
            
            menu_url = scraper.find_menu_page(base_url)
            print(f"   Discovered menu URL: {menu_url}")
            
            # Test menu content scoring
            print("\n📊 Phase 2: Content Analysis & Scoring")
            
            # Get page content for scoring
            response = scraper._get_with_orchestrator_bypass(menu_url)
            if scraper._is_successful_response(response):
                content = scraper._extract_content_from_response(response)
                score = scraper._score_menu_content(content, menu_url)
                print(f"   Content length: {len(content):,} characters")
                print(f"   Menu confidence score: {score}/50+ (higher is better)")
                
                # Save raw HTML for debugging
                scraper._save_raw_html(menu_url, content, "bubbas33_test", score/50.0)
                print("   ✅ Raw HTML saved for debugging")
            else:
                print("   ❌ Failed to retrieve content for scoring")
            
            # Full menu extraction with validation
            print("\n🍽️ Phase 3: Complete Menu Extraction")
            
            result = scraper.extract_menu(
                website_url=base_url,
                restaurant_name="Bubba's 33",
                force_menu_url=None  # Let it use enhanced discovery
            )
            
            processing_time = time.time() - start_time
            
            print(f"\n📈 EXTRACTION RESULTS")
            print(f"   Success: {result.success}")
            print(f"   Items found: {result.items_found}")
            print(f"   Categories: {result.categories_found}")
            print(f"   Processing time: {processing_time:.2f} seconds")
            print(f"   Confidence score: {result.confidence_score:.3f}")
            print(f"   Menu URL used: {result.menu_url}")
            
            # Validate success threshold
            if hasattr(scraper, '_validate_success_threshold'):
                meets_threshold, validation_details = scraper._validate_success_threshold(result.menu_data)
                
                print(f"\n🎯 SUCCESS THRESHOLD VALIDATION")
                print(f"   Meets 7+ item threshold: {meets_threshold}")
                print(f"   Total items: {validation_details.get('total_items', 0)}")
                print(f"   Items with prices: {validation_details.get('items_with_prices', 0)}")
                print(f"   Categories found: {validation_details.get('categories_found', 0)}")
                print(f"   Average confidence: {validation_details.get('avg_confidence', 0):.3f}")
                
                if meets_threshold:
                    print("   ✅ SUCCESS: Meets quality threshold!")
                else:
                    print("   ⚠️ PARTIAL: Below quality threshold")
            
            # Display sample menu items
            if result.menu_data and 'items' in result.menu_data:
                items = result.menu_data['items']
                print(f"\n📋 SAMPLE MENU ITEMS (showing first 5 of {len(items)}):")
                
                for i, item in enumerate(items[:5]):
                    if isinstance(item, dict):
                        name = item.get('name', 'Unknown Item')
                        price = item.get('price', item.get('price_text', 'No price'))
                        description = item.get('description', '')[:50] + '...' if item.get('description') else ''
                        
                        print(f"   {i+1}. {name}")
                        print(f"      Price: {price}")
                        if description:
                            print(f"      Description: {description}")
                        print()
            
            # Test creative discovery methods
            print(f"\n🔍 TESTING CREATIVE DISCOVERY METHODS")
            
            # Test sitemap parsing
            sitemap_urls = scraper._parse_sitemap("https://bubbas33.com")
            print(f"   Sitemap URLs found: {len(sitemap_urls)}")
            for i, url in enumerate(sitemap_urls[:3]):
                print(f"     {i+1}. {url}")
            
            # Test third-party service detection
            third_party = scraper._detect_third_party_menu_services("https://bubbas33.com")
            print(f"   Third-party services: {len(third_party)}")
            for service, details in third_party.items():
                print(f"     {service}: {details}")
            
            # Test JavaScript detection
            needs_js = scraper._needs_js_rendering("https://bubbas33.com")
            print(f"   Requires JavaScript rendering: {needs_js}")
            
            print(f"\n🎉 ENHANCED EXTRACTION COMPLETE!")
            print(f"   Total processing time: {processing_time:.2f} seconds")
            
            # Summary comparison
            print(f"\n📊 SYSTEM COMPARISON")
            print(f"   Previous system: Found ~6 items (promotional content)")
            print(f"   Enhanced system: Found {result.items_found} items")
            print(f"   Quality improvement: {'+' if result.items_found > 6 else '='}{result.items_found - 6} items")
            print(f"   Success threshold (7+ items): {'✅ MET' if result.items_found >= 7 else '❌ NOT MET'}")
            
            return result
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"\n❌ EXTRACTION FAILED")
        print(f"   Error: {e}")
        print(f"   Processing time: {processing_time:.2f} seconds")
        
        import traceback
        print(f"\n🐛 FULL ERROR TRACEBACK:")
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    print("Enhanced CloudDestroyer Menu Extraction Test")
    print("Testing 15-attempt discovery system with Bubba's 33")
    print()
    
    result = test_enhanced_bubbas_extraction()
    
    if result:
        print(f"\n✨ Test completed successfully!")
        print(f"Check debug_html/ directory for saved raw HTML content")
    else:
        print(f"\n💥 Test failed - check error details above")