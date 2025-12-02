@echo off
echo 🚀 CloudDestroyer Restaurant API Demo
echo =====================================

echo.
echo Starting Restaurant API Server...
echo (This will run on http://localhost:8000)
echo.

REM Start the API server in background
start "Restaurant API Server" cmd /c "python restaurant_api.py"

echo Waiting for server to start...
timeout /t 5 /nobreak >nul

echo.
echo 🧪 Running Restaurant API Tests...
echo This will test your example: bubbas33.com
echo.

REM Run the tests
python test_restaurant_api.py

echo.
echo 📋 API Endpoints Available:
echo ========================
echo GET    http://localhost:8000/          - API Info
echo GET    http://localhost:8000/health    - Health Check  
echo POST   http://localhost:8000/restaurant/extract - Extract Menu
echo POST   http://localhost:8000/restaurant/quick   - Quick Menu Check
echo GET    http://localhost:8000/examples  - Usage Examples
echo.
echo 🔑 API Key for testing: demo_key_123
echo.
echo 💡 Your Food App Integration:
echo =============================
echo 1. POST to /restaurant/extract with {"website_url": "https://bubbas33.com"}
echo 2. API automatically detects menu at bubbas33.com/menu  
echo 3. Returns structured JSON with all menu items, prices, categories
echo 4. Your Food App saves this data to FoodFinder database
echo.

pause