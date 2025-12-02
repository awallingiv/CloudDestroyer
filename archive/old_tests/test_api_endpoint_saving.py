"""
Test script to verify API endpoint saving functionality
"""
from db_config import DatabaseManager

def test_api_endpoint_saving():
    """Test that API endpoints are being saved and retrieved correctly"""

    print("=" * 80)
    print("API ENDPOINT SAVING TEST")
    print("=" * 80)
    print()

    db = DatabaseManager()

    # Test 1: Check if www.bubbas33.com has a saved API endpoint
    print("Test 1: Checking for Bubba's 33 API endpoint...")
    endpoint_info = db.get_api_endpoint("www.bubbas33.com")

    if endpoint_info:
        print("+ Found saved API endpoint!")
        print(f"  Domain: {endpoint_info.get('domain')}")
        print(f"  Endpoint: {endpoint_info.get('api_menu_endpoint')}")
        print(f"  Type: {endpoint_info.get('api_endpoint_type')}")
        print(f"  Working: {endpoint_info.get('api_endpoint_working')}")
        print(f"  Last Verified: {endpoint_info.get('api_last_verified')}")
        print(f"  Verified Count: {endpoint_info.get('api_verified_count')}")
        print(f"  Requires Location: {endpoint_info.get('api_requires_location')}")
        print(f"  Auth Method: {endpoint_info.get('api_authentication_method')}")
        print(f"  Site Type: {endpoint_info.get('site_type')}")
    else:
        print("- No saved endpoint found for www.bubbas33.com")

    print()

    # Test 2: Get all working API endpoints
    print("Test 2: Getting all working API endpoints...")
    working_endpoints = db.get_working_api_endpoints(min_verifications=1)

    if working_endpoints:
        print(f"+ Found {len(working_endpoints)} working API endpoints:")
        for i, ep in enumerate(working_endpoints, 1):
            print(f"  {i}. {ep.get('domain')} ({ep.get('api_endpoint_type')})")
            print(f"     Endpoint: {ep.get('api_menu_endpoint')}")
            print(f"     Verified: {ep.get('api_verified_count')} times")
            print(f"     Last Verified: {ep.get('api_last_verified')}")
    else:
        print("- No working API endpoints found")

    print()

    # Test 3: Manually save a test endpoint
    print("Test 3: Testing manual endpoint save...")
    try:
        result = db.save_api_endpoint(
            domain="test.example.com",
            api_menu_endpoint="https://test.example.com/api/menu",
            api_endpoint_type="rest",
            requires_location=False,
            authentication_method="none",
            site_type="api_driven"
        )
        print(f"+ Test endpoint saved successfully: {result}")
    except Exception as e:
        print(f"- Failed to save test endpoint: {e}")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    db.close()

if __name__ == "__main__":
    test_api_endpoint_saving()
