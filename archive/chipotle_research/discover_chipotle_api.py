"""
Chipotle API Discovery Script
Uses Selenium to navigate Chipotle's website and capture API calls
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import json
import time
from datetime import datetime

def setup_chrome():
    """Setup Chrome with network logging"""
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--start-maximized')

    # Enable performance logging to capture network requests
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = webdriver.Chrome(options=options)
    return driver

def capture_network_logs(driver):
    """Extract API calls from Chrome performance logs"""
    logs = driver.get_log('performance')
    api_calls = []

    for log in logs:
        try:
            log_message = json.loads(log['message'])
            message = log_message.get('message', {})

            # Look for network request/response events
            if message.get('method') in ['Network.requestWillBeSent', 'Network.responseReceived']:
                request_data = message.get('params', {}).get('request', {})
                response_data = message.get('params', {}).get('response', {})

                url = request_data.get('url') or response_data.get('url', '')

                # Filter for API calls
                if any(keyword in url.lower() for keyword in ['api', 'graphql', 'menu', 'restaurant', 'location']):
                    api_info = {
                        'timestamp': datetime.now().isoformat(),
                        'url': url,
                        'method': request_data.get('method', response_data.get('mimeType', '')),
                        'type': message.get('method')
                    }

                    # Get headers if available
                    headers = request_data.get('headers') or response_data.get('headers', {})
                    if headers:
                        # Filter important headers
                        important_headers = ['authorization', 'x-api-key', 'content-type', 'accept']
                        api_info['headers'] = {
                            k: v for k, v in headers.items()
                            if any(h in k.lower() for h in important_headers)
                        }

                    api_calls.append(api_info)

        except Exception as e:
            continue

    return api_calls

def discover_chipotle_api():
    """
    Navigate Chipotle website and discover API endpoints
    """

    print("=" * 80)
    print("CHIPOTLE API ENDPOINT DISCOVERY")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print()

    driver = None
    all_api_calls = []

    try:
        print("Step 1: Setting up Chrome browser with network capture...")
        driver = setup_chrome()
        print("+ Browser initialized")
        print()

        print("Step 2: Loading Chipotle homepage...")
        driver.get("https://www.chipotle.com")
        time.sleep(5)  # Wait for initial load
        print("+ Homepage loaded")

        # Capture initial API calls
        api_calls = capture_network_logs(driver)
        all_api_calls.extend(api_calls)
        print(f"+ Captured {len(api_calls)} API calls from homepage")
        print()

        print("Step 3: Looking for 'Order' or location entry...")
        try:
            # Try to find and click order button
            wait = WebDriverWait(driver, 10)

            # Common Chipotle selectors (may need adjustment based on their current site)
            possible_selectors = [
                (By.LINK_TEXT, "Order"),
                (By.PARTIAL_LINK_TEXT, "Order"),
                (By.CSS_SELECTOR, "[href*='order']"),
                (By.CSS_SELECTOR, "button[class*='order']"),
                (By.XPATH, "//a[contains(text(), 'Order')]"),
                (By.XPATH, "//button[contains(text(), 'Order')]")
            ]

            order_button = None
            for by, selector in possible_selectors:
                try:
                    order_button = wait.until(EC.element_to_be_clickable((by, selector)))
                    print(f"+ Found order button using: {selector}")
                    break
                except:
                    continue

            if order_button:
                order_button.click()
                print("+ Clicked order button")
                time.sleep(5)

                # Capture API calls after click
                api_calls = capture_network_logs(driver)
                all_api_calls.extend(api_calls)
                print(f"+ Captured {len(api_calls)} additional API calls")
            else:
                print("- Order button not found, continuing...")

        except Exception as e:
            print(f"- Could not click order button: {e}")

        print()

        print("Step 4: Trying to enter location (ZIP code)...")
        try:
            # Look for location input
            location_inputs = [
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.CSS_SELECTOR, "input[placeholder*='location']"),
                (By.CSS_SELECTOR, "input[placeholder*='zip']"),
                (By.CSS_SELECTOR, "input[placeholder*='address']"),
                (By.ID, "location"),
                (By.NAME, "location")
            ]

            location_input = None
            for by, selector in location_inputs:
                try:
                    location_input = driver.find_element(by, selector)
                    print(f"+ Found location input: {selector}")
                    break
                except:
                    continue

            if location_input:
                test_zip = "90210"  # Beverly Hills, CA
                location_input.clear()
                location_input.send_keys(test_zip)
                print(f"+ Entered test ZIP code: {test_zip}")
                time.sleep(3)

                # Try to submit
                location_input.send_keys(u'\ue007')  # Enter key
                time.sleep(5)

                # Capture API calls after location entry
                api_calls = capture_network_logs(driver)
                all_api_calls.extend(api_calls)
                print(f"+ Captured {len(api_calls)} API calls after location entry")
            else:
                print("- Location input not found")

        except Exception as e:
            print(f"- Could not enter location: {e}")

        print()

        print("Step 5: Waiting for additional page interactions...")
        time.sleep(5)

        # Final capture
        api_calls = capture_network_logs(driver)
        all_api_calls.extend(api_calls)

        print()
        print("=" * 80)
        print("DISCOVERY COMPLETE")
        print("=" * 80)

        # Deduplicate API calls by URL
        unique_apis = {}
        for call in all_api_calls:
            url = call['url']
            if url not in unique_apis:
                unique_apis[url] = call

        print(f"Total unique API endpoints discovered: {len(unique_apis)}")
        print()

        # Group by domain/path
        print("Discovered API Endpoints:")
        print("-" * 80)

        for url, call_info in list(unique_apis.items())[:20]:  # Show first 20
            method = call_info.get('method', 'GET')
            print(f"  {method} {url}")
            if call_info.get('headers'):
                print(f"      Headers: {call_info['headers']}")

        if len(unique_apis) > 20:
            print(f"  ... and {len(unique_apis) - 20} more endpoints")

        # Save to file
        output_file = f"chipotle_api_endpoints_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(list(unique_apis.values()), f, indent=2, ensure_ascii=False)

        print()
        print(f"+ Full results saved to: {output_file}")
        print()

        # Analyze for menu-related endpoints
        menu_related = [
            url for url in unique_apis.keys()
            if any(keyword in url.lower() for keyword in ['menu', 'item', 'product', 'catalog'])
        ]

        if menu_related:
            print("Menu-Related Endpoints Found:")
            print("-" * 80)
            for url in menu_related:
                print(f"  {url}")
        else:
            print("No obvious menu endpoints found in URLs.")
            print("Check the full JSON output for GraphQL or generic API endpoints.")

        return list(unique_apis.values())

    except Exception as e:
        print()
        print(f"Error during discovery: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        if driver:
            print()
            print("Closing browser...")
            driver.quit()
            print("+ Browser closed")

if __name__ == "__main__":
    discover_chipotle_api()
