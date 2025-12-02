"""
Test script to extract Chipotle menu items and prices using their API
This will extract the API key from their JavaScript and use it to access menu data
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import json
import re
import time
from datetime import datetime

def setup_browser():
    """Setup Chrome browser"""
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    return driver

def extract_api_key_from_page(driver):
    """
    Extract Chipotle's API subscription key from JavaScript
    """
    print("Searching for API key in JavaScript files...")

    # Get all script elements
    scripts = driver.find_elements(By.TAG_NAME, "script")

    # Patterns to search for
    patterns = [
        r'["\'](Ocp-Apim-Subscription-Key|ocp-apim-subscription-key)["\'][\s:]+["\']([a-f0-9]{32})["\']',
        r'subscriptionKey[\s:]+["\']([a-f0-9]{32})["\']',
        r'apiKey[\s:]+["\']([a-f0-9]{32})["\']',
        r'["\'](subscription-key)["\'][\s:]+["\']([a-f0-9]{32})["\']',
        r'Ocp-Apim-Subscription-Key["\']?\s*:\s*["\']([a-f0-9]{32})["\']',
        # Azure APIM often uses this header name
        r'["\']Ocp-Apim-Subscription-Key["\']\s*,\s*["\']([a-f0-9]{32})["\']',
    ]

    for script in scripts:
        try:
            # Get script source URL
            src = script.get_attribute('src')
            content = script.get_attribute('innerHTML')

            if content:
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # Handle different match formats
                        if isinstance(matches[0], tuple):
                            key = matches[0][-1]  # Get last group (the actual key)
                        else:
                            key = matches[0]

                        if len(key) == 32:  # Typical Azure APIM key length
                            print(f"+ Found potential API key: {key[:8]}...{key[-8:]}")
                            return key

            # If script has external source, fetch and search it
            if src and 'chipotle.com' in src:
                try:
                    script_content = requests.get(src).text
                    for pattern in patterns:
                        matches = re.findall(pattern, script_content, re.IGNORECASE)
                        if matches:
                            if isinstance(matches[0], tuple):
                                key = matches[0][-1]
                            else:
                                key = matches[0]

                            if len(key) == 32:
                                print(f"+ Found API key in external script: {src}")
                                print(f"  Key: {key[:8]}...{key[-8:]}")
                                return key
                except:
                    pass
        except:
            continue

    return None

def extract_api_key_from_network(driver):
    """
    Alternative method: Extract API key from network requests
    """
    print("Checking browser's localStorage and sessionStorage...")

    # Check localStorage
    try:
        local_storage = driver.execute_script("return window.localStorage;")
        for key, value in local_storage.items():
            if 'api' in key.lower() or 'key' in key.lower() or 'subscription' in key.lower():
                print(f"  Found in localStorage: {key} = {value[:50]}...")
                # Try to extract key from value
                match = re.search(r'[a-f0-9]{32}', str(value))
                if match:
                    return match.group(0)
    except:
        pass

    # Check sessionStorage
    try:
        session_storage = driver.execute_script("return window.sessionStorage;")
        for key, value in session_storage.items():
            if 'api' in key.lower() or 'key' in key.lower():
                print(f"  Found in sessionStorage: {key} = {value[:50]}...")
                match = re.search(r'[a-f0-9]{32}', str(value))
                if match:
                    return match.group(0)
    except:
        pass

    return None

def get_menu_with_api_key(api_key):
    """
    Fetch Chipotle menu using the API key
    """
    print(f"\nTesting API key: {api_key[:8]}...{api_key[-8:]}")

    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    endpoints = [
        "https://services.chipotle.com/menuinnovation/v1/universalmenus/online",
        "https://services.chipotle.com/menuinnovation/v1/universalmeals/online",
        "https://services.chipotle.com/menu-metadata/v1/menu-metadata?channel=web&region=US"
    ]

    results = {}

    for endpoint in endpoints:
        try:
            print(f"\nTesting endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)

            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results[endpoint] = data
                print(f"  + Success! Received {len(json.dumps(data))} bytes of data")

                # Show sample of data structure
                if isinstance(data, dict):
                    print(f"  Keys in response: {list(data.keys())[:5]}")
                elif isinstance(data, list):
                    print(f"  Response is a list with {len(data)} items")
            else:
                print(f"  - Failed: {response.text[:200]}")

        except Exception as e:
            print(f"  - Error: {e}")

    return results

def parse_chipotle_menu(menu_data):
    """
    Parse Chipotle menu data and extract items with prices
    """
    items = []
    categories = {}

    # Try different data structures
    if 'menus' in menu_data:
        for menu in menu_data['menus']:
            if 'categories' in menu:
                for category in menu['categories']:
                    cat_name = category.get('name', 'Unknown')
                    categories[cat_name] = []

                    if 'items' in category:
                        for item in category['items']:
                            item_data = {
                                'name': item.get('name', item.get('itemName', 'Unknown')),
                                'description': item.get('description', ''),
                                'price': item.get('basePrice', item.get('price', None)),
                                'category': cat_name,
                                'customizable': item.get('customizable', False),
                                'id': item.get('id', item.get('itemId', ''))
                            }
                            items.append(item_data)
                            categories[cat_name].append(item_data['name'])

    elif 'categories' in menu_data:
        for category in menu_data['categories']:
            cat_name = category.get('name', category.get('categoryName', 'Unknown'))
            categories[cat_name] = []

            if 'items' in category:
                for item in category['items']:
                    item_data = {
                        'name': item.get('name', item.get('itemName', 'Unknown')),
                        'description': item.get('description', ''),
                        'price': item.get('basePrice', item.get('price', None)),
                        'category': cat_name,
                        'customizable': item.get('customizable', False)
                    }
                    items.append(item_data)
                    categories[cat_name].append(item_data['name'])

    elif 'items' in menu_data:
        for item in menu_data['items']:
            item_data = {
                'name': item.get('name', item.get('itemName', 'Unknown')),
                'description': item.get('description', ''),
                'price': item.get('basePrice', item.get('price', None)),
                'category': item.get('category', 'Uncategorized'),
                'customizable': item.get('customizable', False)
            }
            items.append(item_data)

    return items, categories

def test_chipotle_menu_extraction():
    """
    Main test function
    """
    print("=" * 80)
    print("CHIPOTLE MENU EXTRACTION TEST")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print()

    driver = None

    try:
        # Step 1: Load Chipotle website
        print("Step 1: Loading Chipotle order page...")
        driver = setup_browser()
        driver.get("https://www.chipotle.com/order")

        print("+ Page loaded, waiting for JavaScript to execute...")
        time.sleep(8)  # Wait for all scripts to load

        # Step 2: Extract API key
        print("\nStep 2: Extracting API key from JavaScript...")
        api_key = extract_api_key_from_page(driver)

        if not api_key:
            print("- API key not found in page source, trying network storage...")
            api_key = extract_api_key_from_network(driver)

        if not api_key:
            print("\n- Could not extract API key automatically")
            print("- The key may be:")
            print("  1. Dynamically generated per session")
            print("  2. Obfuscated in webpack bundles")
            print("  3. Loaded via service worker")
            print("\nTrying alternative approach: Using browser's authenticated session...")

            # Alternative: Use browser's cookies
            cookies = driver.get_cookies()
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])

            # Try to make request with session cookies
            try:
                print("\nAttempting request with browser session cookies...")
                response = session.get(
                    "https://services.chipotle.com/menuinnovation/v1/universalmenus/online",
                    headers={'Accept': 'application/json'}
                )

                if response.status_code == 200:
                    print("+ Success with session cookies!")
                    menu_data = response.json()

                    # Save raw response
                    with open('chipotle_menu_raw.json', 'w', encoding='utf-8') as f:
                        json.dump(menu_data, f, indent=2, ensure_ascii=False)
                    print("+ Raw menu data saved to: chipotle_menu_raw.json")

                    # Parse menu
                    items, categories = parse_chipotle_menu(menu_data)

                    # Display results
                    print("\n" + "=" * 80)
                    print("MENU EXTRACTION RESULTS")
                    print("=" * 80)
                    print(f"Categories Found: {len(categories)}")
                    print(f"Items Found: {len(items)}")
                    print(f"Items with Prices: {sum(1 for item in items if item.get('price'))}")
                    print()

                    if categories:
                        print("Categories:")
                        for i, (cat_name, cat_items) in enumerate(categories.items(), 1):
                            print(f"  {i}. {cat_name} ({len(cat_items)} items)")

                    if items:
                        print("\nSample Items:")
                        for i, item in enumerate(items[:15], 1):
                            price_str = f"${item['price']}" if item.get('price') else "Price varies"
                            print(f"  {i}. [{item['category']}] {item['name']} - {price_str}")
                            if item.get('description'):
                                desc = item['description'][:60] + "..." if len(item['description']) > 60 else item['description']
                                print(f"      {desc}")

                    # Save structured data
                    output = {
                        'success': True,
                        'extraction_method': 'session_cookies',
                        'categories': categories,
                        'items': items,
                        'total_items': len(items),
                        'total_categories': len(categories),
                        'extracted_at': datetime.now().isoformat()
                    }

                    output_file = f"chipotle_menu_extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(output, f, indent=2, ensure_ascii=False)

                    print(f"\n+ Structured menu data saved to: {output_file}")

                    return output
                else:
                    print(f"- Failed with status: {response.status_code}")
                    print(f"  Response: {response.text[:200]}")

            except Exception as e:
                print(f"- Session request failed: {e}")

            return None

        # Step 3: Use API key to fetch menu
        print("\nStep 3: Fetching menu data with API key...")
        menu_results = get_menu_with_api_key(api_key)

        if menu_results:
            print("\n" + "=" * 80)
            print("EXTRACTION SUCCESSFUL")
            print("=" * 80)

            # Parse and display results
            for endpoint, data in menu_results.items():
                print(f"\nEndpoint: {endpoint}")
                items, categories = parse_chipotle_menu(data)

                print(f"  Categories: {len(categories)}")
                print(f"  Items: {len(items)}")

                if categories:
                    print("  Sample categories:", list(categories.keys())[:5])

                if items:
                    print("  Sample items:")
                    for item in items[:5]:
                        print(f"    - {item['name']}: ${item.get('price', 'N/A')}")

            # Save results
            output_file = f"chipotle_menu_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(menu_results, f, indent=2, ensure_ascii=False)

            print(f"\n+ Full results saved to: {output_file}")
            return menu_results
        else:
            print("\n- No menu data retrieved")
            return None

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()
            print("+ Browser closed")

        print("\n" + "=" * 80)
        print(f"Test completed: {datetime.now()}")
        print("=" * 80)

if __name__ == "__main__":
    test_chipotle_menu_extraction()
