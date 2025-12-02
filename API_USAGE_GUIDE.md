# CloudDestroyer API - Usage Guide

## Quick Start

CloudDestroyer has a production-ready FastAPI service that you can call from any application.

---

## Starting the API Service

### Option 1: Using Uvicorn

```bash
# Start the API server on port 8000
uvicorn api:app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: Using Python Script

Create `start_api.py`:
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        workers=1     # Number of worker processes
    )
```

Then run:
```bash
python start_api.py
```

---

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/restaurant/extract` | POST | Extract restaurant menu |
| `/docs` | GET | Interactive API documentation (Swagger UI) |
| `/redoc` | GET | Alternative API documentation (ReDoc) |

---

## Authentication

The API uses **Bearer token authentication**.

### Setting API Key

Check [api.py](api.py:4001) for the `verify_api_key()` function. By default, it may require an API key in the Authorization header.

**Example Header:**
```
Authorization: Bearer your-api-key-here
```

---

## Extract Restaurant Menu

### Endpoint
```
POST /restaurant/extract
```

### Request Body

```json
{
  "website_url": "https://www.chipotle.com",
  "restaurant_name": "Chipotle",  // Optional
  "force_menu_url": null           // Optional - force specific menu page
}
```

### Response

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
    "extraction_method": "api_discovery",
    "categories": [
      {
        "name": "Burrito",
        "description": "Your choice of freshly grilled meat..."
      }
    ],
    "items": [
      {
        "item_id": "CMG-1",
        "name": "Chicken Burrito",
        "category": "Burrito",
        "description": "...",
        "calories": "180",
        "price": null,
        "dietary_tags": ["pale", "keto"]
      }
    ]
  },
  "error_message": null
}
```

---

## Client Examples

### Python

```python
import requests

# API configuration
API_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"

# Make request
response = requests.post(
    f"{API_URL}/restaurant/extract",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "website_url": "https://www.chipotle.com",
        "restaurant_name": "Chipotle"
    }
)

# Parse response
if response.status_code == 200:
    result = response.json()
    print(f"Success! Found {result['items_found']} items")
    print(f"Categories: {len(result['menu_data']['categories'])}")

    # Access menu items
    for item in result['menu_data']['items'][:5]:
        print(f"  - {item['name']} ({item['category']})")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### JavaScript / Node.js

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000';
const API_KEY = 'your-api-key-here';

async function extractMenu(websiteUrl, restaurantName) {
  try {
    const response = await axios.post(
      `${API_URL}/restaurant/extract`,
      {
        website_url: websiteUrl,
        restaurant_name: restaurantName
      },
      {
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const result = response.data;
    console.log(`Success! Found ${result.items_found} items`);
    console.log(`Processing time: ${result.processing_time_seconds}s`);

    return result;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    throw error;
  }
}

// Usage
extractMenu('https://www.chipotle.com', 'Chipotle')
  .then(result => {
    console.log('Menu extracted successfully');
    console.log(`Items: ${result.items_found}`);
  });
```

### cURL

```bash
curl -X POST "http://localhost:8000/restaurant/extract" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "website_url": "https://www.chipotle.com",
    "restaurant_name": "Chipotle"
  }'
```

### C# / .NET

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class CloudDestroyerClient
{
    private readonly HttpClient _httpClient;
    private const string API_URL = "http://localhost:8000";
    private const string API_KEY = "your-api-key-here";

    public CloudDestroyerClient()
    {
        _httpClient = new HttpClient();
        _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {API_KEY}");
    }

    public async Task<MenuExtractionResult> ExtractMenuAsync(
        string websiteUrl,
        string restaurantName = null)
    {
        var request = new
        {
            website_url = websiteUrl,
            restaurant_name = restaurantName
        };

        var json = JsonSerializer.Serialize(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync(
            $"{API_URL}/restaurant/extract",
            content
        );

        response.EnsureSuccessStatusCode();

        var responseJson = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<MenuExtractionResult>(responseJson);
    }
}

// Usage
var client = new CloudDestroyerClient();
var result = await client.ExtractMenuAsync(
    "https://www.chipotle.com",
    "Chipotle"
);

Console.WriteLine($"Found {result.ItemsFound} items");
```

---

## Interactive API Documentation

Once the service is running, visit:

### Swagger UI
```
http://localhost:8000/docs
```

- Interactive API explorer
- Try endpoints directly in browser
- See request/response schemas
- Test authentication

### ReDoc
```
http://localhost:8000/redoc
```

- Clean, organized API documentation
- Better for reading/reference

---

## Production Deployment

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Chrome for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t clouddestroyer-api .
docker run -p 8000:8000 clouddestroyer-api
```

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=your-secure-api-key
      - DATABASE_CONNECTION_STRING=your-db-connection
    volumes:
      - ./sessions:/app/sessions  # Persist sessions
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

---

## Environment Variables

Configure via environment variables:

```bash
# API Configuration
export API_KEY="your-secure-api-key"
export API_HOST="0.0.0.0"
export API_PORT="8000"

# Database
export DB_SERVER="localhost"
export DB_NAME="CloudDestroyer"
export DB_USER="sa"
export DB_PASSWORD="your-password"

# CloudDestroyer Settings
export HEADLESS_BROWSER="true"
export MAX_RETRIES="3"
export TIMEOUT="60"
```

---

## Rate Limiting (Recommended for Production)

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/restaurant/extract")
@limiter.limit("10/minute")  # 10 requests per minute
async def extract_restaurant_menu(...):
    ...
```

---

## Error Handling

### Common Error Responses

**400 Bad Request**
```json
{
  "detail": "Invalid website URL format"
}
```

**401 Unauthorized**
```json
{
  "detail": "Invalid or missing API key"
}
```

**500 Internal Server Error**
```json
{
  "success": false,
  "error_message": "Failed to extract menu: Connection timeout",
  "items_found": 0
}
```

### Retry Logic Example

```python
import time

def extract_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_URL}/restaurant/extract",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"website_url": url},
                timeout=120
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
                continue

            response.raise_for_status()

        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise
            time.sleep(5)

    raise Exception("Max retries exceeded")
```

---

## Monitoring & Logging

### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-02T13:45:30.123456",
  "version": "2.0.0"
}
```

### Logging

The API logs all requests. Monitor logs for:
- Extraction times
- Success/failure rates
- API vs traditional scraping usage
- Error patterns

---

## Performance Tips

1. **Use API-first extraction** - Already enabled by default
2. **Cache database connections** - Already implemented
3. **Async processing** - Use background tasks for multiple restaurants
4. **Rate limiting** - Prevent overwhelming target websites
5. **Load balancing** - Use multiple API instances for high traffic

---

## Example: Batch Processing

Extract menus for multiple restaurants:

```python
import asyncio
import aiohttp

async def extract_batch(restaurants):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for restaurant in restaurants:
            task = extract_one(session, restaurant['url'], restaurant['name'])
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results

async def extract_one(session, url, name):
    async with session.post(
        f"{API_URL}/restaurant/extract",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"website_url": url, "restaurant_name": name}
    ) as response:
        return await response.json()

# Usage
restaurants = [
    {"url": "https://www.chipotle.com", "name": "Chipotle"},
    {"url": "https://www.bubbas33.com", "name": "Bubba's 33"},
    # ... more restaurants
]

results = asyncio.run(extract_batch(restaurants))
```

---

## Security Recommendations

1. **Use HTTPS in production** - Configure SSL/TLS certificates
2. **Rotate API keys regularly** - Implement key rotation
3. **Whitelist IP addresses** - Restrict access to known clients
4. **Enable CORS properly** - Don't use wildcard in production
5. **Add request validation** - Validate all inputs
6. **Use secrets manager** - Don't hardcode credentials

---

## Support

- **API Docs**: http://localhost:8000/docs
- **Source Code**: [api.py](api.py:1)
- **GitHub Issues**: https://github.com/anthropics/claude-code/issues
