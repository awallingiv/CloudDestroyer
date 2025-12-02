#!/usr/bin/env python3
"""
Test the restored API with Bubba's 33
"""
import requests
import json

def test_api_with_bubbas():
    """Test the API with Bubba's 33 to verify authentication bypass"""
    
    api_url = "http://localhost:8000/restaurant/extract"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_key_abc123"
    }
    
    data = {
        "website_url": "https://bubbas33.com",
        "restaurant_name": "Bubba's 33"
    }
    
    print("Testing restored API with Bubba's 33...")
    print(f"Request: POST {api_url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print()
    
    try:
        # Make API request
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS - API Request Successful!")
            print()
            print("=== API Response Summary ===")
            print(f"Restaurant: {result.get('restaurant_name', 'N/A')}")
            print(f"Menu URL: {result.get('menu_url', 'N/A')}")
            
            # Check new menu_data structure
            menu_data = result.get('menu_data', {})
            menu_items = menu_data.get('items', [])
            categories = menu_data.get('categories', {})
            
            print(f"Items Found: {len(menu_items)}")
            print(f"Categories: {len(categories)}")
            print(f"Confidence Score: {result.get('confidence_score', 'N/A')}")
            print(f"Processing Time: {result.get('processing_time_seconds', 'N/A')}s")
            print(f"Success: {result.get('success', False)}")
            
            # Show categories if found from new menu_data structure
            menu_data = result.get('menu_data', {})
            categories = menu_data.get('categories', {})
            if categories:
                print()
                print("=== Categories Found ===")
                for cat_name, items in categories.items():
                    print(f"  - {cat_name}: {len(items)} items")
            
            # Show first few menu items if found
            menu_items = menu_data.get('items', [])
            if menu_items:
                print()
                print("=== Sample Menu Items ===")
                for item in menu_items[:5]:  # Show first 5 items
                    name = item.get('name', 'Unknown')
                    price = item.get('price', 'N/A')
                    category = item.get('category', 'N/A')
                    print(f"  - {name} (${price}) - {category}")
            
            if len(menu_items) > 5:
                print(f"  ... and {len(menu_items) - 5} more items")
            
            # Assess if bypass worked
            if len(menu_items) > 10:
                print()
                print("🎉 AUTHENTICATION BYPASS RESTORED SUCCESSFULLY!")
                print("The sophisticated bypass orchestrator is working correctly.")
            else:
                print()
                print("⚠️  Limited menu items found - may need further tuning")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_api_with_bubbas()