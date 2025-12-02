#!/usr/bin/env python3
"""
Simple test to check if API starts correctly
"""
import requests
import json
import time

def simple_test():
    """Simple test without full extraction"""
    
    # Wait a moment for server startup
    time.sleep(2)
    
    try:
        # Test basic server health first
        response = requests.get("http://localhost:8000/", timeout=10)
        print(f"Server health check: {response.status_code}")
        
    except Exception as e:
        print(f"Server not responding: {e}")
        return
    
    # Now test the API endpoint
    api_url = "http://localhost:8000/restaurant/extract"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_key_abc123"
    }
    
    data = {
        "website_url": "https://bubbas33.com",
        "restaurant_name": "Bubba's 33"
    }
    
    print("Testing API endpoint...")
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Request Successful!")
            print(f"Response keys: {list(result.keys())}")
            
            if 'menu_data' in result:
                menu_data = result['menu_data']
                categories = menu_data.get('categories', {})
                items = menu_data.get('items', [])
                
                print(f"Categories found: {len(categories)}")
                print(f"Category names: {list(categories.keys())}")
                print(f"Total items: {len(items)}")
                
                if categories:
                    print("🎉 Angular/Ionic parsing worked!")
                else:
                    print("⚠️ No categories extracted yet")
                    
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    simple_test()