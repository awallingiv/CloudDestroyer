"""
Test the smart API-first extraction with automatic fallback
This should work for both Chipotle (API-driven) and any restaurant (traditional scraping)
"""

from api import RestaurantMenuScraper
import json
from datetime import datetime

def test_smart_extraction(url: str, name: str):
    """
    Test smart extraction - API first, then fallback
    """
    print("=" * 80)
    print(f"TESTING SMART EXTRACTION: {name}")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Started: {datetime.now()}")
    print()

    scraper = RestaurantMenuScraper(save_api_endpoints=True)

    try:
        result = scraper.extract_menu(url, restaurant_name=name)

        print("\n" + "=" * 80)
        print("EXTRACTION RESULT")
        print("=" * 80)
        print(f"Success: {result.success}")
        print(f"Restaurant: {result.restaurant_name}")
        print(f"Menu URL: {result.menu_url}")
        print(f"Items Found: {result.items_found}")
        print(f"Categories Found: {result.categories_found}")
        print(f"Processing Time: {result.processing_time_seconds:.1f}s")
        print(f"Confidence Score: {result.confidence_score}")

        if result.menu_data and 'extraction_method' in result.menu_data:
            print(f"Extraction Method: {result.menu_data['extraction_method']}")

        if result.error_message:
            print(f"Error: {result.error_message}")

        # Save result
        filename = f"{name.lower().replace(' ', '_')}_extraction_result.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        print(f"\n+ Saved result to: {filename}")

        # Show sample items
        if result.menu_data and 'items' in result.menu_data:
            items = result.menu_data['items']
            print(f"\nSample Items (first 5):")
            print("-" * 80)
            for item in items[:5]:
                name = item.get('name', 'Unnamed')
                cat = item.get('category', 'Unknown')
                cal = item.get('calories')
                cal_str = f" - {cal} cal" if cal else ""
                print(f"  [{cat}] {name}{cal_str}")

        return result

    except Exception as e:
        print(f"\n- ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CLOUD DESTROYER - SMART EXTRACTION TEST")
    print("Testing API-first with automatic fallback")
    print("=" * 80)
    print()

    # Test 1: Chipotle (should use saved API endpoint)
    print("\nTest 1: Chipotle (should use saved API endpoint)\n")
    chipotle_result = test_smart_extraction(
        "https://www.chipotle.com",
        "Chipotle"
    )

    # Test 2: Bubba's 33 (should use OLO detection)
    print("\n\n" + "=" * 80)
    print("Test 2: Bubba's 33 (should use OLO detection)")
    print("=" * 80)
    print()

    bubbas_result = test_smart_extraction(
        "https://www.bubbas33.com",
        "Bubba's 33"
    )

    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if chipotle_result:
        print(f"\nChipotle:")
        print(f"  Items: {chipotle_result.items_found}")
        print(f"  Time: {chipotle_result.processing_time_seconds:.1f}s")
        print(f"  Method: {chipotle_result.menu_data.get('extraction_method', 'unknown')}")

    if bubbas_result:
        print(f"\nBubba's 33:")
        print(f"  Items: {bubbas_result.items_found}")
        print(f"  Time: {bubbas_result.processing_time_seconds:.1f}s")
        print(f"  Method: {bubbas_result.menu_data.get('extraction_method', 'unknown')}")

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)
