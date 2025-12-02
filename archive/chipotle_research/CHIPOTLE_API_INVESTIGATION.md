# Chipotle API Investigation

## Objective
Investigate Chipotle's menu API endpoints to enable direct API access instead of complex SPA navigation.

## Date: December 2, 2025

---

## Background

Previous scraping test results:
- **Items Extracted:** 2 (catering info only)
- **Confidence Score:** 0.33 (Low)
- **Issue:** Location-dependent menu loading, Angular/Ionic SPA architecture

The website requires:
1. Location selection (ZIP code or address)
2. Restaurant selection from nearby locations
3. Menu only loads after restaurant is selected

---

## Investigation Steps

### Step 1: Manual Navigation Flow

**User Journey:**
```
chipotle.com
  → Enter location (ZIP/Address)
    → Select restaurant
      → View menu
        → Select category
          → View items
```

### Step 2: Browser DevTools Network Analysis

**What to Capture:**
1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Filter by "Fetch/XHR"
4. Navigate through Chipotle's ordering flow
5. Look for API calls containing menu data

**Expected API Patterns:**
- `/api/v1/restaurants?lat=...&lng=...`
- `/api/v1/menu?restaurantId=...`
- `/api/v1/locations/...`
- GraphQL endpoints (common for modern SPAs)

---

## API Discovery Script

Below is a Python script to automatically discover Chipotle's API endpoints by simulating the user flow:

```python
"""
Chipotle API Discovery Script
Captures network traffic during order flow to identify menu API endpoints
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumwire import webdriver as wire_webdriver  # pip install selenium-wire
import json
import time

def discover_chipotle_api():
    """
    Use Selenium Wire to capture API calls during Chipotle ordering flow
    """

    print("=" * 80)
    print("CHIPOTLE API DISCOVERY")
    print("=" * 80)
    print()

    # Setup Selenium Wire (captures network traffic)
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = wire_webdriver.Chrome(options=options)

    try:
        print("Step 1: Loading Chipotle homepage...")
        driver.get("https://www.chipotle.com")
        time.sleep(3)

        print("Step 2: Looking for 'Order Now' or location entry...")
        # Look for order button or location input
        # This will trigger location-based API calls

        # Capture all API requests
        api_endpoints = []

        print("\nStep 3: Analyzing captured network requests...")
        for request in driver.requests:
            if request.response:
                # Look for API calls (JSON responses)
                if 'api' in request.url.lower() or 'graphql' in request.url.lower():
                    content_type = request.response.headers.get('Content-Type', '')

                    if 'json' in content_type.lower():
                        endpoint_info = {
                            'url': request.url,
                            'method': request.method,
                            'status': request.response.status_code,
                            'content_type': content_type
                        }

                        # Try to get response body
                        try:
                            body = request.response.body.decode('utf-8')
                            if len(body) < 1000:
                                endpoint_info['sample_response'] = body
                            else:
                                endpoint_info['response_size'] = len(body)
                        except:
                            pass

                        api_endpoints.append(endpoint_info)
                        print(f"  Found: {request.method} {request.url[:100]}...")

        print(f"\nTotal API endpoints discovered: {len(api_endpoints)}")

        # Save to file
        with open('chipotle_api_endpoints.json', 'w') as f:
            json.dump(api_endpoints, f, indent=2)

        print("+ API endpoints saved to: chipotle_api_endpoints.json")

        return api_endpoints

    finally:
        driver.quit()

if __name__ == "__main__":
    discover_chipotle_api()
```

---

## Known API Patterns for Chain Restaurants

Based on industry standards, Chipotle likely uses one of these patterns:

### Pattern 1: RESTful API with Location Context
```
GET /api/v1/locations?lat={lat}&lng={lng}&radius={radius}
  → Returns: List of nearby restaurants

GET /api/v1/restaurants/{restaurantId}/menu
  → Returns: Menu for specific location
```

### Pattern 2: GraphQL (Modern SPA Standard)
```
POST /graphql
Body: {
  "query": "query GetMenu($restaurantId: ID!) {
    restaurant(id: $restaurantId) {
      menu {
        categories {
          name
          items {
            name
            description
            price
          }
        }
      }
    }
  }",
  "variables": {
    "restaurantId": "12345"
  }
}
```

### Pattern 3: Microservices Architecture
```
GET /menu-service/api/restaurants/{id}
GET /location-service/api/nearby?lat={lat}&lng={lng}
GET /ordering-service/api/menu/{restaurantId}
```

---

## Expected API Response Structure

### Location API Response:
```json
{
  "restaurants": [
    {
      "id": "12345",
      "name": "Chipotle - Downtown",
      "address": "123 Main St",
      "lat": 34.0522,
      "lng": -118.2437,
      "isOpen": true,
      "distance": 1.2
    }
  ]
}
```

### Menu API Response:
```json
{
  "restaurantId": "12345",
  "menu": {
    "categories": [
      {
        "id": "burritos",
        "name": "Burritos",
        "items": [
          {
            "id": "burrito-chicken",
            "name": "Chicken Burrito",
            "description": "Freshly grilled chicken...",
            "basePrice": 8.95,
            "customizable": true,
            "options": [...]
          }
        ]
      }
    ]
  }
}
```

---

## Authentication Analysis

**Possible Authentication Methods:**
1. **None** - Public API (unlikely for menu prices)
2. **Session-based** - Cookie/session token after location selection
3. **API Key** - Client-side API key in headers
4. **OAuth** - Token-based authentication

**Headers to Check:**
- `Authorization: Bearer {token}`
- `X-API-Key: {key}`
- `Cookie: session_id={id}`
- `X-Client-Id: {client_id}`

---

## Location Requirements

Chipotle's menu API likely requires:

### Option A: Restaurant ID Only
```python
# Once we have a restaurant ID, we can call the menu API directly
endpoint = f"https://www.chipotle.com/api/menu/{restaurant_id}"
```

### Option B: Geolocation Context
```python
# API requires lat/lng in query params or headers
endpoint = "https://www.chipotle.com/api/menu"
params = {
    "restaurantId": restaurant_id,
    "lat": 34.0522,
    "lng": -118.2437
}
```

### Option C: Session-Based
```python
# Must establish session first with location
# 1. POST /api/location with ZIP code
# 2. GET /api/menu (uses session context)
```

---

## Implementation Strategy

Once API endpoints are discovered:

### Phase 1: Direct API Access
```python
def extract_chipotle_menu(restaurant_id: str, zip_code: str = None):
    """
    Extract menu using discovered API endpoint
    """
    # 1. Get restaurant ID from location (if needed)
    if not restaurant_id and zip_code:
        restaurant_id = get_nearest_restaurant(zip_code)

    # 2. Call menu API directly
    menu_data = call_menu_api(restaurant_id)

    # 3. Parse and structure data
    return parse_chipotle_menu(menu_data)
```

### Phase 2: Location Auto-Selection
```python
def auto_select_location(zip_code: str = "90210"):
    """
    Automatically select first available restaurant for a ZIP code
    """
    locations = get_locations_by_zip(zip_code)
    if locations:
        return locations[0]['id']  # Use first location
    return None
```

### Phase 3: Integration with CloudDestroyer
```python
# Save discovered endpoint to database
db.save_api_endpoint(
    domain="www.chipotle.com",
    api_menu_endpoint=discovered_endpoint,
    api_endpoint_type="rest",  # or "graphql"
    requires_location=True,     # Chipotle requires restaurant ID
    authentication_method="session",  # or "none" if public
    site_type="api_driven"
)
```

---

## Next Steps

1. **Run Discovery Script** - Capture actual API endpoints
2. **Analyze Response Structure** - Document exact JSON format
3. **Test Direct API Access** - Verify we can call endpoints directly
4. **Implement Location Handler** - Auto-select restaurant for testing
5. **Update api.py** - Add Chipotle-specific extraction logic
6. **Save to Database** - Store working endpoint with metadata

---

## Manual Investigation Checklist

Use browser DevTools to manually investigate:

- [ ] Go to www.chipotle.com
- [ ] Open DevTools (F12) → Network tab
- [ ] Clear network log
- [ ] Click "Order Now" or enter location
- [ ] Watch for API calls containing "menu", "restaurant", "location"
- [ ] Copy request URLs, headers, and response bodies
- [ ] Test if endpoints work with curl/Postman
- [ ] Document any authentication requirements
- [ ] Note if restaurant ID is in URL or POST body

---

## Expected Outcome

After investigation, we should have:

1. ✓ Direct menu API endpoint URL
2. ✓ Authentication method (if any)
3. ✓ Required parameters (restaurant ID, location, etc.)
4. ✓ Response structure documentation
5. ✓ Working curl/Python example for direct access

This will enable CloudDestroyer to:
- Skip complex SPA navigation
- Extract full menu data in 5-10 seconds
- Save endpoint for future reuse
- Handle location requirements automatically
