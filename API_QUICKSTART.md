# CloudDestroyer API - Quick Start

## Yes! You can call CloudDestroyer from any application using a REST API.

---

## 1. Start the API Server

```bash
# Simple start
python start_api.py

# Or using uvicorn directly
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Output:**
```
================================================================================
CLOUDDESTROYER API SERVICE
================================================================================
Starting API server...
  Host: 0.0.0.0
  Port: 8000
  Reload: True
  Workers: 1

API Documentation:
  Swagger UI: http://localhost:8000/docs
  ReDoc:      http://localhost:8000/redoc

Endpoints:
  POST http://localhost:8000/restaurant/extract
  GET  http://localhost:8000/health
================================================================================
```

---

## 2. Test the API

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/restaurant/extract",
    json={"website_url": "https://www.chipotle.com"}
)

result = response.json()
print(f"Found {result['items_found']} items in {result['processing_time_seconds']}s")
```

### Using cURL

```bash
curl -X POST "http://localhost:8000/restaurant/extract" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://www.chipotle.com"}'
```

### Using the Included Client

```bash
python example_api_client.py
```

---

## 3. View Interactive Docs

Open your browser to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can **test the API directly in the browser** using Swagger UI!

---

## API Response Example

```json
{
  "success": true,
  "restaurant_name": "Chipotle",
  "website_url": "https://www.chipotle.com",
  "menu_url": "https://services.chipotle.com/menu-metadata/v1/menu-metadata",
  "items_found": 266,
  "categories_found": 14,
  "processing_time_seconds": 25.3,
  "confidence_score": 1.0,
  "menu_data": {
    "extraction_method": "api_saved_endpoint",
    "categories": [...],
    "items": [
      {
        "item_id": "CMG-1",
        "name": "Chicken Burrito",
        "category": "Burrito",
        "calories": "180",
        "dietary_tags": ["pale", "keto"]
      }
    ]
  }
}
```

---

## What Happens Under the Hood

1. **API receives request** for www.chipotle.com
2. **Checks database** for saved API endpoint
3. **Finds saved endpoint** from previous run
4. **Extracts fresh API key** using Chrome DevTools Protocol (~10s)
5. **Calls Chipotle API directly** with key
6. **Parses 266 menu items** from JSON response
7. **Returns structured data** to your application

**Total time: ~15-25 seconds** (vs 85 seconds with traditional scraping)

---

## Call from Any Language

### JavaScript (fetch)

```javascript
fetch('http://localhost:8000/restaurant/extract', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({website_url: 'https://www.chipotle.com'})
})
.then(res => res.json())
.then(data => console.log(`Found ${data.items_found} items`));
```

### C#

```csharp
var client = new HttpClient();
var response = await client.PostAsJsonAsync(
    "http://localhost:8000/restaurant/extract",
    new { website_url = "https://www.chipotle.com" }
);
var result = await response.Content.ReadFromJsonAsync<MenuResult>();
```

### PHP

```php
$response = file_get_contents(
    'http://localhost:8000/restaurant/extract',
    false,
    stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/json',
            'content' => json_encode([
                'website_url' => 'https://www.chipotle.com'
            ])
        ]
    ])
);
$result = json_decode($response, true);
```

---

## Full Documentation

- **[API_USAGE_GUIDE.md](API_USAGE_GUIDE.md:1)** - Complete API documentation
- **[SMART_EXTRACTION_IMPLEMENTATION.md](SMART_EXTRACTION_IMPLEMENTATION.md:1)** - How the smart extraction works

---

## What You Get

✅ **REST API** - Call from any language
✅ **Automatic API detection** - Finds APIs automatically
✅ **Smart caching** - Reuses discovered endpoints
✅ **Graceful fallback** - Falls back to traditional scraping if API fails
✅ **Interactive docs** - Swagger UI at /docs
✅ **Production ready** - FastAPI with CORS, validation, error handling

No need to write custom scripts for each restaurant anymore!
