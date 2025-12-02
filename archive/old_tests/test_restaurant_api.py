#!/usr/bin/env python3
"""
Food App Integration Test - Demonstrates how to use the Restaurant API
"""

import requests
import json
from typing import Dict, Any

class FoodAppRestaurantClient:
    """Client for Food App to interact with Restaurant API"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000", api_key: str = "demo_key_123"):
        self.base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def check_menu_available(self, website_url: str) -> Dict[str, Any]:
        """Quick check if restaurant has extractable menu data"""
        
        response = requests.post(
            f"{self.base_url}/restaurant/quick",
            headers=self.headers,
            json={"website_url": website_url}
        )
        
        return response.json()
    
    def extract_restaurant_menu(self, website_url: str, restaurant_name: str = None) -> Dict[str, Any]:
        """Extract complete menu from restaurant website"""
        
        payload = {"website_url": website_url}
        if restaurant_name:
            payload["restaurant_name"] = restaurant_name
        
        response = requests.post(
            f"{self.base_url}/restaurant/extract",
            headers=self.headers,
            json=payload
        )
        
        return response.json()
    
    def save_menu_to_database(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Save extracted menu to Food App database"""
        
        response = requests.post(
            f"{self.base_url}/restaurant/save",
            headers=self.headers,
            json=extraction_result
        )
        
        return response.json()
    
    def get_api_health(self) -> Dict[str, Any]:
        """Check API service health"""
        
        response = requests.get(f"{self.base_url}/health")
        return response.json()

def demo_bubba33_extraction():
    """Demonstrate extracting Bubba's 33 menu (our success case)"""
    
    print("🍔 Food App Restaurant Integration Demo")
    print("=" * 50)
    
    # Initialize client
    client = FoodAppRestaurantClient()
    
    # Test with Bubba's 33 (we know this works)
    restaurant_url = "https://bubbas33.com"
    restaurant_name = "Bubba's 33"
    
    print(f"\n1. Testing API Health...")
    health = client.get_api_health()
    print(f"   API Status: {health.get('status')}")
    print(f"   CloudDestroyer: {health.get('clouddestroyer')}")
    
    print(f"\n2. Quick Menu Check for {restaurant_name}...")
    quick_check = client.check_menu_available(restaurant_url)
    print(f"   Has Menu: {quick_check.get('has_menu')}")
    print(f"   Menu URL: {quick_check.get('menu_url')}")
    print(f"   Detection Method: {quick_check.get('detection_method')}")
    
    if quick_check.get('has_menu'):
        print(f"\n3. Extracting Full Menu for {restaurant_name}...")
        
        extraction_result = client.extract_restaurant_menu(restaurant_url, restaurant_name)
        
        if extraction_result.get('success'):
            print(f"   ✅ Success! Extracted {extraction_result.get('items_found')} menu items")
            print(f"   📂 Categories: {extraction_result.get('categories_found')}")
            print(f"   ⏱️  Processing Time: {extraction_result.get('processing_time_seconds'):.2f}s")
            print(f"   🎯 Confidence: {extraction_result.get('confidence_score'):.2f}")
            print(f"   🔧 Method: {extraction_result.get('extraction_method')}")
            
            # Show sample menu items
            menu_data = extraction_result.get('menu_data', {})
            items = menu_data.get('items', [])
            
            print(f"\n   📋 Sample Menu Items:")
            for i, item in enumerate(items[:5]):  # Show first 5 items
                name = item.get('name', 'Unknown')
                price = item.get('price', 'N/A')
                category = item.get('category', 'Unknown')
                print(f"      {i+1}. {name} - ${price} ({category})")
            
            if len(items) > 5:
                print(f"      ... and {len(items) - 5} more items")
            
            # Demonstrate saving to database (uncomment when FoodFinder DB is ready)
            # print(f"\n4. Saving Menu to Food App Database...")
            # save_result = client.save_menu_to_database(extraction_result)
            # print(f"   Items Saved: {save_result.get('items_saved')}")
            
        else:
            print(f"   ❌ Extraction Failed: {extraction_result.get('error_message')}")
    
    else:
        print(f"   ⚠️  No menu detected for {restaurant_name}")

def demo_multiple_restaurants():
    """Test multiple restaurant websites"""
    
    print("\n" + "=" * 50)
    print("🌐 Testing Multiple Restaurant Websites")
    print("=" * 50)
    
    client = FoodAppRestaurantClient()
    
    test_restaurants = [
        ("https://bubbas33.com", "Bubba's 33"),
        ("https://mcdonalds.com", "McDonald's"),
        ("https://subway.com", "Subway"),
        ("https://pizzahut.com", "Pizza Hut"),
        ("https://dominos.com", "Domino's")
    ]
    
    results = []
    
    for url, name in test_restaurants:
        print(f"\n🔍 Testing {name} ({url})...")
        
        try:
            # Quick check first
            quick_check = client.check_menu_available(url)
            has_menu = quick_check.get('has_menu', False)
            
            print(f"   Menu Available: {has_menu}")
            
            if has_menu:
                # Try full extraction
                extraction = client.extract_restaurant_menu(url, name)
                success = extraction.get('success', False)
                items_found = extraction.get('items_found', 0)
                
                print(f"   Extraction Success: {success}")
                print(f"   Items Found: {items_found}")
                
                results.append({
                    'restaurant': name,
                    'url': url,
                    'menu_available': has_menu,
                    'extraction_success': success,
                    'items_found': items_found
                })
            else:
                results.append({
                    'restaurant': name, 
                    'url': url,
                    'menu_available': False,
                    'extraction_success': False,
                    'items_found': 0
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                'restaurant': name,
                'url': url, 
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 SUMMARY RESULTS:")
    print("=" * 30)
    successful_extractions = [r for r in results if r.get('extraction_success')]
    
    print(f"Restaurants Tested: {len(test_restaurants)}")
    print(f"Successful Extractions: {len(successful_extractions)}")
    print(f"Success Rate: {len(successful_extractions)/len(test_restaurants)*100:.1f}%")
    
    for result in successful_extractions:
        print(f"  ✅ {result['restaurant']}: {result['items_found']} items")

def food_app_integration_example():
    """Show how Food App would integrate this in production"""
    
    print("\n" + "=" * 60)
    print("📱 FOOD APP PRODUCTION INTEGRATION EXAMPLE")
    print("=" * 60)
    
    # This is how your Food App would use the API
    def add_restaurant_to_food_app(restaurant_url: str, restaurant_name: str):
        """Add new restaurant to Food App database"""
        
        client = FoodAppRestaurantClient(
            api_base_url="http://your-clouddestroyer-server:8000",
            api_key="food_app_key_prod"  # Use production key
        )
        
        print(f"🏪 Adding {restaurant_name} to Food App...")
        
        # Step 1: Check if menu is available
        menu_check = client.check_menu_available(restaurant_url)
        
        if not menu_check.get('has_menu'):
            return {
                'success': False,
                'message': f'No extractable menu found for {restaurant_name}'
            }
        
        # Step 2: Extract full menu
        extraction = client.extract_restaurant_menu(restaurant_url, restaurant_name)
        
        if not extraction.get('success'):
            return {
                'success': False,
                'message': f'Menu extraction failed: {extraction.get("error_message")}'
            }
        
        # Step 3: Save to Food App database
        # save_result = client.save_menu_to_database(extraction)
        
        return {
            'success': True,
            'restaurant_name': restaurant_name,
            'items_extracted': extraction.get('items_found'),
            'categories': extraction.get('categories_found'),
            'confidence': extraction.get('confidence_score'),
            'menu_data': extraction.get('menu_data')
        }
    
    # Example usage in your Food App
    print("\nExample: User wants to add a new restaurant to Food App")
    
    # User provides restaurant URL through your Food App interface
    user_restaurant_url = "https://bubbas33.com"
    user_restaurant_name = "Bubba's 33"
    
    # Your Food App calls the integration function
    result = add_restaurant_to_food_app(user_restaurant_url, user_restaurant_name)
    
    if result['success']:
        print(f"   ✅ Successfully added {result['restaurant_name']}")
        print(f"   📊 {result['items_extracted']} menu items imported")
        print(f"   📂 {result['categories']} categories found")
        print(f"   🎯 {result['confidence']:.2f} confidence score")
        
        # Now your Food App can display the menu items to users
        menu_items = result['menu_data']['items']
        print(f"\n   🍽️  Food App can now show these menu items:")
        for item in menu_items[:3]:
            print(f"      - {item.get('name')} (${item.get('price', 'N/A')})")
    else:
        print(f"   ❌ Failed to add restaurant: {result['message']}")

if __name__ == "__main__":
    print("Starting Restaurant API Test Suite...")
    print("Make sure to run: python restaurant_api.py first!")
    
    try:
        # Run the demos
        demo_bubba33_extraction()
        demo_multiple_restaurants() 
        food_app_integration_example()
        
        print(f"\n🎉 All tests completed!")
        print("\n💡 Integration Tips for your Food App:")
        print("   1. Use /restaurant/quick for fast menu availability checks")
        print("   2. Use /restaurant/extract for full menu data extraction") 
        print("   3. Use /restaurant/save to store data in your FoodFinder DB")
        print("   4. Handle errors gracefully - some sites may be protected")
        print("   5. Cache successful extractions to avoid re-scraping")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Restaurant API!")
        print("   Make sure to start the API server first:")
        print("   python restaurant_api.py")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")