#!/usr/bin/env python3
"""
Quick test to validate the timeout and loop fixes for Bubba's 33 menu discovery
"""

import sys
import time
import logging
from api import RestaurantMenuScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_bubbas_with_timeout():
    """Test Bubba's 33 with timeout protection"""
    
    print("=" * 80)
    print("TESTING BUBBA'S 33 WITH TIMEOUT AND LOOP FIXES")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        with RestaurantMenuScraper() as scraper:
            print(f"\n1. Testing menu discovery with timeout protection...")
            
            # This should not hang indefinitely
            menu_url = scraper.find_menu_page("https://bubbas33.com")
            
            discovery_time = time.time() - start_time
            print(f"   ✓ Discovery completed in {discovery_time:.1f}s")
            print(f"   ✓ Menu URL found: {menu_url}")
            
            # Validate it didn't take too long
            if discovery_time > 360:  # 6 minutes max
                print(f"   ⚠️  WARNING: Discovery took {discovery_time:.1f}s (longer than expected)")
            else:
                print(f"   ✅ Discovery time is reasonable: {discovery_time:.1f}s")
                
            print(f"\n2. Testing menu extraction...")
            extraction_start = time.time()
            
            result = scraper.extract_menu("https://bubbas33.com", "Bubba's 33")
            
            extraction_time = time.time() - extraction_start
            total_time = time.time() - start_time
            
            print(f"   ✓ Extraction completed in {extraction_time:.1f}s")
            print(f"   ✓ Total process time: {total_time:.1f}s")
            
            # Show results
            print(f"\n3. Results Summary:")
            print(f"   • Success: {result.success}")
            print(f"   • Items found: {result.items_found}")
            print(f"   • Categories found: {result.categories_found}")
            print(f"   • Confidence score: {result.confidence_score}")
            print(f"   • Menu URL: {result.menu_url}")
            
            if result.error_message:
                print(f"   • Error: {result.error_message}")
                
            # Success criteria
            success_criteria = [
                ("Process completed", True),
                ("Reasonable timing", total_time < 360),
                ("Found menu items", result.items_found > 0),
                ("No infinite loops", discovery_time < 300)
            ]
            
            print(f"\n4. Success Criteria Check:")
            all_passed = True
            for criteria, passed in success_criteria:
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"   {status} {criteria}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print(f"\n🎉 ALL TESTS PASSED! Timeout and loop fixes are working.")
            else:
                print(f"\n⚠️  Some tests failed. Review results above.")
                
            return result
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
        return None
        
    except Exception as e:
        total_time = time.time() - start_time
        print(f"\n❌ Test failed after {total_time:.1f}s: {e}")
        
        # Check if it's a timeout-related error
        if total_time > 300:
            print("   This appears to be a timeout/hanging issue")
        
        return None

if __name__ == "__main__":
    print("Starting Bubba's 33 timeout fix validation test...")
    
    try:
        result = test_bubbas_with_timeout()
        
        if result:
            print(f"\nTest completed successfully!")
            sys.exit(0)
        else:
            print(f"\nTest failed or was interrupted!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user (Ctrl+C)")
        sys.exit(130)