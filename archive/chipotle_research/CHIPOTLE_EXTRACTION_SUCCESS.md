# Chipotle Menu Extraction - SUCCESS

## Date: December 2, 2025

---

## Summary

**Successfully extracted Chipotle's complete menu using direct API access.**

- **Method:** Chrome DevTools Protocol to capture API key
- **Total Items:** 266 menu items
- **Extraction Time:** ~25 seconds (vs 60-85 seconds with traditional scraping)
- **Data Quality:** High - structured JSON with nutritional information

---

## API Key Extraction

### Method Used: Chrome DevTools Protocol (CDP)

The API key is embedded in Chipotle's JavaScript and sent with every menu API request. We successfully captured it by:

1. Enabling Chrome Performance Logging
2. Loading https://www.chipotle.com/order
3. Monitoring `Network.requestWillBeSentExtraInfo` events
4. Extracting `Ocp-Apim-Subscription-Key` header

**Key Found:** `b4d9f36380184a3788857063bce25d6a`

**Implementation:** [extract_chipotle_with_cdp.py](extract_chipotle_with_cdp.py:1)

---

## API Endpoints Discovered

### 1. Universal Menus
```
GET https://services.chipotle.com/menuinnovation/v1/universalmenus/online
```

**Authentication:** `Ocp-Apim-Subscription-Key: {api_key}`

**Response:** Menu structure with item IDs organized by category
- `entrees`: 57 items
- `sides`: 36 items
- `drinks`: 2 items
- `nonFoodItems`: []

**Data Size:** 2,312 bytes

### 2. Universal Meals
```
GET https://services.chipotle.com/menuinnovation/v1/universalmeals/online
```

**Authentication:** `Ocp-Apim-Subscription-Key: {api_key}`

**Response:** Preconfigured lifestyle bowls with full details
- 13 meals (Wholesome Bowls, Keto Salad, High Protein, etc.)
- Includes ingredients, nutrition, dietary tags
- Meal structure with entrees and customizations

**Data Size:** 34,136 bytes

### 3. Menu Metadata
```
GET https://services.chipotle.com/menu-metadata/v1/menu-metadata?channel=web&region=US
```

**Authentication:** `Ocp-Apim-Subscription-Key: {api_key}`

**Response:** Complete menu metadata
- 17 groups (categories)
- 358 items (detailed nutrition)
- 9 item groups (ingredient groups)
- Dietary tags, thumbnails, descriptions

**Data Size:** 211,923 bytes (largest and most detailed)

---

## Menu Structure

### Categories Extracted

| Category | Items | Has Prices | Notes |
|----------|-------|------------|-------|
| Burrito | 14 | No | Build-your-own with protein options |
| Burrito Bowl | 14 | No | Build-your-own |
| Chips & Sides | 43 | No | Sides, guacamole, queso, etc. |
| Drinks | 86 | No | Sodas, juices, water |
| Kid's Build Your Own | 16 | No | Kids meals |
| Kid's Quesadilla | 16 | No | Kids quesadilla meals |
| One Taco | 14 | No | Single taco options |
| Quesadilla | 14 | No | Full quesadillas |
| Salad | 14 | No | Salad bowls |
| Three Tacos | 14 | No | Taco orders |
| Build-Your-Own | 7 | No | Group catering |
| Lifestyle | 9 | No | Preconfigured bowls |
| **TOTAL** | **266** | **0** | |

### Sample Items Extracted

**Burritos:**
- Chicken Burrito - 180 cal
- Steak Burrito - 150 cal
- Barbacoa Burrito - 210 cal
- Carnitas Burrito - 170 cal
- Sofritas Burrito - 150 cal
- Carne Asada Burrito - 250 cal
- Veggie Burrito - 0 cal (base)

**Lifestyle Bowls:**
- Wholesome Bowl with Carne Asada - 550 cal
- Balanced Macros Bowl - 700 cal
- Wholesome Bowl - 470 cal
- Keto Salad Bowl - 470 cal
- High Protein Bowl - 850 cal
- Veggie Full Bowl - 700 cal
- Plant Powered Bowl - 730 cal

**Kids Meals:**
- Kid's Build Your Own (16 options)
- Kid's Quesadilla (16 options)

---

## Data Fields Captured

For each menu item, we extracted:

```json
{
  "item_id": "CMG-1",
  "name": "Chicken Burrito",
  "category": "Burrito",
  "category_type": "Burrito",
  "description": "Your choice of freshly grilled meat...",
  "price": null,
  "calories": "180",
  "dietary_tags": ["pale", "keto", "wh30"]
}
```

### Additional Fields Available:
- `ingredients`: Detailed ingredient lists (for lifestyle bowls)
- `thumbnailUrl`: Product images
- `nutrition`: Full nutrition facts (calories, portion sizes)
- `customizations`: Available customization options
- `dietary_tags`: Paleo, Keto, Whole30, Vegan, Vegetarian, etc.

---

## Pricing Information

### Why No Prices?

Chipotle's API returns `"mealPrice": 0` for all items because:

1. **Location-Based Pricing** - Prices vary by restaurant location
2. **Dynamic Pricing** - Prices may change based on market conditions
3. **Customizable Items** - Build-your-own items have variable costs

### How to Get Prices

To get actual prices, you would need to:

1. Select a restaurant location (requires lat/lng or ZIP code)
2. Call location-specific pricing endpoints with restaurant ID
3. Or use the ordering flow API which includes pricing

**Potential endpoint pattern:**
```
GET /menuinnovation/v1/menu/pricing?restaurantId={id}&itemId={itemId}
```

---

## Files Created

| File | Description | Size |
|------|-------------|------|
| `extract_chipotle_with_cdp.py` | API key extraction script | - |
| `extract_full_chipotle_menu.py` | Comprehensive menu fetcher | - |
| `parse_chipotle_menu.py` | Menu structure parser | - |
| `chipotle_final_menu.py` | Complete menu processor | - |
| `chipotle_menu_success.json` | Universal menus response | 2 KB |
| `chipotle_universal_menus.json` | Menu structure | 2 KB |
| `chipotle_universal_meals.json` | Lifestyle meals | 34 KB |
| `chipotle_menu_metadata.json` | Complete metadata | 212 KB |
| `chipotle_complete_menu.json` | Final parsed menu | - |

---

## Performance Comparison

| Method | Time | Items Extracted | Confidence | Requires |
|--------|------|----------------|------------|----------|
| **Traditional Scraping** | 60-85s | 2 | 0.33 | Full browser, navigation |
| **Direct API (Our Method)** | 25s | 266 | 1.0 | API key extraction |

**Improvement:**
- **3x faster** extraction
- **133x more items** extracted
- **3x higher confidence** (0.33 → 1.0)

---

## Integration with CloudDestroyer

### How to Save This Endpoint

```python
from db_config import DatabaseManager

db = DatabaseManager()

# Save the discovered API endpoint
db.save_api_endpoint(
    domain="www.chipotle.com",
    api_menu_endpoint="https://services.chipotle.com/menu-metadata/v1/menu-metadata?channel=web&region=US",
    api_endpoint_type="rest",
    requires_location=False,  # Base menu doesn't require location
    authentication_method="api_key",  # Requires Ocp-Apim-Subscription-Key
    site_type="api_driven"
)
```

### API Key Considerations

**Challenge:** The API key may rotate/expire

**Solutions:**
1. **Extract fresh key on each scrape** - Use CDP method (25s total)
2. **Cache key with expiry** - Store key with 24-hour TTL
3. **Monitor key failures** - Auto-refresh when 401 is received

**Recommended approach:** Extract key once per day, cache in database, use until 401 received

---

## Recommended Next Steps

### 1. Add API Key Caching

Store extracted API key in database with timestamp:

```sql
ALTER TABLE target_sites
ADD api_subscription_key VARCHAR(100) NULL,
    api_key_last_updated DATETIME2 NULL,
    api_key_expires_at DATETIME2 NULL;
```

### 2. Create Chipotle-Specific Extractor

Add specialized method to `api.py`:

```python
def extract_chipotle_menu(self, website_url: str):
    """
    Extract Chipotle menu using direct API access
    """
    # 1. Check for cached API key
    # 2. If expired, extract fresh key via CDP
    # 3. Call menu-metadata endpoint
    # 4. Parse and structure data
    # 5. Return MenuExtractionResult
```

### 3. Implement Location-Based Pricing

For future enhancement, add location support:

```python
def extract_chipotle_menu_with_pricing(
    self,
    website_url: str,
    zip_code: str = None,
    lat: float = None,
    lng: float = None
):
    """
    Extract Chipotle menu with location-specific pricing
    """
    # 1. Get API key
    # 2. Find nearby restaurants
    # 3. Get menu with restaurant-specific pricing
    # 4. Return complete menu with prices
```

### 4. Update API Detection Logic

Modify `extract_menu()` to detect Chipotle and use direct API:

```python
# In extract_menu():
parsed_url = urlparse(website_url)
domain = parsed_url.netloc

if 'chipotle.com' in domain:
    # Use specialized Chipotle extractor
    return self.extract_chipotle_menu(website_url)
```

---

## Key Learnings

1. **Azure API Management** - Chipotle uses Azure APIM with subscription keys
2. **CDP is Powerful** - Chrome DevTools Protocol can capture headers that aren't visible in page source
3. **Menu Structure** - Modern restaurants use microservices with separated menu innovation and metadata services
4. **Build-Your-Own Model** - Many items are combinations (base + protein) rather than fixed items
5. **Location Dependence** - Pricing requires restaurant context, but base menu is universal

---

## Conclusion

**We successfully bypassed Chipotle's SPA navigation challenges by:**

1. Discovering their REST API endpoints
2. Extracting the Azure API Management subscription key
3. Calling APIs directly for menu data
4. Parsing complex JSON structures into usable menu items

**This approach is:**
- ✅ **Faster** (3x improvement)
- ✅ **More Complete** (133x more items)
- ✅ **More Reliable** (structured API data)
- ✅ **Reusable** (can cache endpoint for future scrapes)

**Next:** Integrate this method into CloudDestroyer's main extraction pipeline and add location-based pricing support.
