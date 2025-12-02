"""
Extract Chipotle menu using Chrome DevTools Protocol to capture API headers
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json
import time
from datetime import datetime

def test_chipotle_with_network_capture():
    """
    Use Chrome DevTools Protocol to capture network requests with full headers
    """
    print("=" * 80)
    print("CHIPOTLE MENU EXTRACTION - CDP METHOD")
    print("=" * 80)
    print(f"Started: {datetime.now()}\n")

    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')

    # Enable Performance Logging with Network domain
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = webdriver.Chrome(options=options)

    try:
        print("Step 1: Loading Chipotle order page...")
        driver.get("https://www.chipotle.com/order")

        print("+ Page loaded, waiting for API calls...")
        time.sleep(10)  # Wait for menu APIs to be called

        print("\nStep 2: Analyzing network logs for API requests...")

        # Get performance logs
        logs = driver.get_log('performance')

        api_requests = []
        api_key_found = None

        for log in logs:
            try:
                log_message = json.loads(log['message'])
                message = log_message.get('message', {})

                # Look for Network.requestWillBeSentExtraInfo (has headers)
                if message.get('method') == 'Network.requestWillBeSentExtraInfo':
                    headers = message.get('params', {}).get('headers', {})

                    # Check for API key in headers
                    for header_name, header_value in headers.items():
                        if 'subscription' in header_name.lower() or 'api' in header_name.lower():
                            print(f"  Found header: {header_name} = {header_value[:20]}...")
                            if header_name.lower() == 'ocp-apim-subscription-key':
                                api_key_found = header_value
                                print(f"  + API KEY FOUND: {header_value[:8]}...{header_value[-8:]}")

                # Look for menu API requests
                if message.get('method') == 'Network.requestWillBeSent':
                    request = message.get('params', {}).get('request', {})
                    url = request.get('url', '')

                    if 'services.chipotle.com' in url and 'menu' in url.lower():
                        request_info = {
                            'url': url,
                            'method': request.get('method', 'GET'),
                            'headers': request.get('headers', {})
                        }
                        api_requests.append(request_info)
                        print(f"  Found menu API request: {url}")

                        # Check for API key in request headers
                        req_headers = request.get('headers', {})
                        for h_name, h_value in req_headers.items():
                            if 'subscription' in h_name.lower():
                                api_key_found = h_value
                                print(f"  + API KEY in request: {h_value[:8]}...{h_value[-8:]}")

            except Exception as e:
                continue

        print(f"\nFound {len(api_requests)} menu API requests")

        if api_key_found:
            print(f"\n+ SUCCESS! Extracted API Key: {api_key_found[:8]}...{api_key_found[-8:]}")
            print(f"\nFull API Key: {api_key_found}")

            # Now try to use the API key
            import requests

            print("\nStep 3: Testing API key with menu endpoint...")

            headers = {
                'Ocp-Apim-Subscription-Key': api_key_found,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            endpoint = "https://services.chipotle.com/menuinnovation/v1/universalmenus/online"

            try:
                response = requests.get(endpoint, headers=headers, timeout=15)
                print(f"  Status: {response.status_code}")

                if response.status_code == 200:
                    menu_data = response.json()
                    print("  + SUCCESS! Retrieved menu data")

                    # Save raw data
                    with open('chipotle_menu_success.json', 'w', encoding='utf-8') as f:
                        json.dump(menu_data, f, indent=2, ensure_ascii=False)

                    print(f"  + Saved to: chipotle_menu_success.json")
                    print(f"  + Data size: {len(json.dumps(menu_data))} bytes")

                    # Show structure
                    if isinstance(menu_data, dict):
                        print(f"  + Top-level keys: {list(menu_data.keys())}")

                    # Try to parse items
                    items_count = 0
                    categories_count = 0

                    if 'menus' in menu_data:
                        for menu in menu_data.get('menus', []):
                            categories_count += len(menu.get('categories', []))
                            for cat in menu.get('categories', []):
                                items_count += len(cat.get('items', []))

                    print(f"\n  Estimated Categories: {categories_count}")
                    print(f"  Estimated Items: {items_count}")

                    return menu_data
                else:
                    print(f"  - Failed: {response.text[:200]}")
            except Exception as e:
                print(f"  - Error: {e}")
        else:
            print("\n- API key not found in network logs")
            print("  The key might be:")
            print("  1. Added by a service worker")
            print("  2. Generated dynamically by JavaScript")
            print("  3. Embedded in a different way")

            # Try GraphQL endpoints as alternative
            print("\nStep 3: Trying GraphQL endpoints (no key required)...")

            try:
                graphql_url = "https://www.chipotle.com/graphql/execute.json/chipotle/nutrition-facts;region=en-us;"
                response = requests.get(graphql_url, headers={'Accept': 'application/json'})

                print(f"  GraphQL Status: {response.status_code}")

                if response.status_code == 200:
                    graphql_data = response.json()
                    print(f"  + GraphQL works! Data size: {len(json.dumps(graphql_data))} bytes")

                    with open('chipotle_graphql_data.json', 'w', encoding='utf-8') as f:
                        json.dump(graphql_data, f, indent=2, ensure_ascii=False)

                    print(f"  + Saved to: chipotle_graphql_data.json")

                    return graphql_data
            except Exception as e:
                print(f"  - GraphQL error: {e}")

        # Save captured API requests
        if api_requests:
            with open('chipotle_api_requests.json', 'w', encoding='utf-8') as f:
                json.dump(api_requests, f, indent=2, ensure_ascii=False)
            print(f"\n+ Captured API requests saved to: chipotle_api_requests.json")

        return None

    finally:
        print("\nClosing browser...")
        driver.quit()
        print("+ Browser closed")
        print("\n" + "=" * 80)
        print(f"Test completed: {datetime.now()}")
        print("=" * 80)

if __name__ == "__main__":
    test_chipotle_with_network_capture()
