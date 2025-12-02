"""
Extract complete Chipotle menu with names, descriptions, and prices
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time
import requests
from datetime import datetime

def extract_api_key():
    """
    Extract API key using Chrome DevTools Protocol
    """
    print("=" * 80)
    print("EXTRACTING CHIPOTLE API KEY")
    print("=" * 80)

    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = webdriver.Chrome(options=options)

    try:
        print("Loading Chipotle order page...")
        driver.get("https://www.chipotle.com/order")
        time.sleep(10)

        print("Analyzing network logs...")
        logs = driver.get_log('performance')

        api_key_found = None

        for log in logs:
            try:
                log_message = json.loads(log['message'])
                message = log_message.get('message', {})

                if message.get('method') == 'Network.requestWillBeSentExtraInfo':
                    headers = message.get('params', {}).get('headers', {})
                    for header_name, header_value in headers.items():
                        if header_name.lower() == 'ocp-apim-subscription-key':
                            api_key_found = header_value
                            print(f"+ API KEY FOUND: {header_value[:8]}...{header_value[-8:]}")
                            break

                if api_key_found:
                    break

            except:
                continue

        return api_key_found

    finally:
        driver.quit()


def fetch_menu_data(api_key):
    """
    Fetch complete menu data using the API key
    """
    print("\n" + "=" * 80)
    print("FETCHING CHIPOTLE MENU DATA")
    print("=" * 80)

    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    endpoints = {
        'universal_menus': 'https://services.chipotle.com/menuinnovation/v1/universalmenus/online',
        'universal_meals': 'https://services.chipotle.com/menuinnovation/v1/universalmeals/online',
        'menu_metadata': 'https://services.chipotle.com/menu-metadata/v1/menu-metadata?channel=web&region=US'
    }

    results = {}

    for name, endpoint in endpoints.items():
        try:
            print(f"\nFetching {name}...")
            response = requests.get(endpoint, headers=headers, timeout=15)
            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results[name] = data

                # Save individual file
                filename = f"chipotle_{name}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"  + Saved to: {filename}")
                print(f"  + Size: {len(json.dumps(data))} bytes")

                # Show structure preview
                if isinstance(data, dict):
                    print(f"  + Top-level keys: {list(data.keys())[:10]}")
                elif isinstance(data, list):
                    print(f"  + Array length: {len(data)}")
            else:
                print(f"  - Failed: {response.status_code}")
                print(f"  - Response: {response.text[:200]}")

        except Exception as e:
            print(f"  - Error: {e}")

    return results


def parse_menu_items(menu_data):
    """
    Parse menu data to extract items with names and prices
    """
    print("\n" + "=" * 80)
    print("PARSING MENU ITEMS")
    print("=" * 80)

    all_items = []

    # Try to parse universal_menus
    if 'universal_menus' in menu_data:
        data = menu_data['universal_menus']

        # Different possible structures
        if 'entrees' in data:
            print("\n+ Found entrees section")
            all_items.extend(parse_category(data.get('entrees', []), 'Entrees'))

        if 'sides' in data:
            print("+ Found sides section")
            all_items.extend(parse_category(data.get('sides', []), 'Sides'))

        if 'drinks' in data:
            print("+ Found drinks section")
            all_items.extend(parse_category(data.get('drinks', []), 'Drinks'))

    # Try universal_meals
    if 'universal_meals' in menu_data:
        data = menu_data['universal_meals']
        print("\n+ Processing universal_meals data")

        if isinstance(data, list):
            for meal in data:
                if isinstance(meal, dict):
                    item = {
                        'category': 'Meals',
                        'item_id': meal.get('id') or meal.get('itemId'),
                        'name': meal.get('name') or meal.get('displayName'),
                        'description': meal.get('description'),
                        'price': meal.get('price') or meal.get('basePrice')
                    }
                    all_items.append(item)

    # Try menu_metadata
    if 'menu_metadata' in menu_data:
        data = menu_data['menu_metadata']
        print("\n+ Processing menu_metadata")

        if isinstance(data, dict):
            # Look for items array
            items = data.get('items') or data.get('menuItems') or data.get('products')
            if items and isinstance(items, list):
                for item_data in items:
                    if isinstance(item_data, dict):
                        item = {
                            'category': item_data.get('category') or 'Unknown',
                            'item_id': item_data.get('id') or item_data.get('itemId'),
                            'name': item_data.get('name') or item_data.get('displayName'),
                            'description': item_data.get('description'),
                            'price': item_data.get('price') or item_data.get('basePrice')
                        }
                        all_items.append(item)

    print(f"\nTotal items parsed: {len(all_items)}")

    # Save parsed items
    if all_items:
        with open('chipotle_parsed_menu.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, indent=2, ensure_ascii=False)
        print("+ Saved to: chipotle_parsed_menu.json")

        # Show sample
        print("\nSample Items:")
        print("-" * 80)
        for item in all_items[:10]:
            name = item.get('name') or 'Unnamed'
            price = item.get('price')
            price_str = f"${price}" if price else "Price N/A"
            print(f"  {name} - {price_str}")

    return all_items


def parse_category(items, category_name):
    """Parse a category of items"""
    parsed = []

    if isinstance(items, list):
        for item_data in items:
            if isinstance(item_data, dict):
                item = {
                    'category': category_name,
                    'item_id': item_data.get('id') or item_data.get('itemId'),
                    'name': item_data.get('name') or item_data.get('displayName'),
                    'description': item_data.get('description'),
                    'price': item_data.get('price') or item_data.get('basePrice')
                }
                parsed.append(item)

    return parsed


def main():
    """
    Main execution flow
    """
    print("CHIPOTLE COMPLETE MENU EXTRACTION")
    print(f"Started: {datetime.now()}")
    print("\n")

    # Step 1: Extract API key
    api_key = extract_api_key()

    if not api_key:
        print("\n- FAILED: Could not extract API key")
        return

    print(f"\n+ SUCCESS: API Key = {api_key}")

    # Step 2: Fetch all menu data
    menu_data = fetch_menu_data(api_key)

    if not menu_data:
        print("\n- FAILED: Could not fetch menu data")
        return

    # Step 3: Parse menu items
    items = parse_menu_items(menu_data)

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Finished: {datetime.now()}")
    print(f"Total Items Extracted: {len(items)}")
    print("\nFiles created:")
    print("  - chipotle_universal_menus.json")
    print("  - chipotle_universal_meals.json")
    print("  - chipotle_menu_metadata.json")
    print("  - chipotle_parsed_menu.json")


if __name__ == "__main__":
    main()
