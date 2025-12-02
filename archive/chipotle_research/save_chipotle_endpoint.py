"""
Save Chipotle API endpoint to database
"""

from db_config import DatabaseManager

def save_chipotle_endpoint():
    """
    Save the discovered Chipotle API endpoint with metadata
    """
    print("=" * 80)
    print("SAVING CHIPOTLE API ENDPOINT TO DATABASE")
    print("=" * 80)

    db = DatabaseManager()

    # Save the menu-metadata endpoint (most comprehensive)
    result = db.save_api_endpoint(
        domain="www.chipotle.com",
        api_menu_endpoint="https://services.chipotle.com/menu-metadata/v1/menu-metadata?channel=web&region=US",
        api_endpoint_type="rest",
        requires_location=False,  # Base menu is universal (prices require location)
        authentication_method="api_key",  # Requires Ocp-Apim-Subscription-Key header
        site_type="api_driven"
    )

    print("\n+ Saved menu-metadata endpoint")
    print(f"  Site ID: {result.get('site_id')}")
    print(f"  Domain: {result.get('domain')}")
    print(f"  API Endpoint: {result.get('api_menu_endpoint')}")
    print(f"  Type: {result.get('api_endpoint_type')}")
    print(f"  Requires Location: {result.get('api_requires_location')}")
    print(f"  Authentication: {result.get('api_authentication_method')}")
    print(f"  Working: {result.get('api_endpoint_working')}")
    print(f"  Verified Count: {result.get('api_verified_count')}")

    # Now retrieve it to confirm
    print("\n" + "=" * 80)
    print("VERIFYING SAVED ENDPOINT")
    print("=" * 80)

    endpoint_info = db.get_api_endpoint("www.chipotle.com")

    if endpoint_info:
        print("\n+ Retrieved endpoint successfully:")
        print(f"  Domain: {endpoint_info['domain']}")
        print(f"  API Endpoint: {endpoint_info['api_menu_endpoint']}")
        print(f"  Type: {endpoint_info['api_endpoint_type']}")
        print(f"  Requires Location: {endpoint_info['api_requires_location']}")
        print(f"  Authentication: {endpoint_info['api_authentication_method']}")
        print(f"  Site Type: {endpoint_info['site_type']}")
        print(f"  Working: {endpoint_info['api_endpoint_working']}")
        print(f"  Last Verified: {endpoint_info['api_last_verified']}")
        print(f"  Verified Count: {endpoint_info['api_verified_count']}")

        print("\n✓ Chipotle API endpoint saved successfully!")
        print("\nNext time CloudDestroyer scrapes www.chipotle.com:")
        print("1. Check database for saved endpoint")
        print("2. Extract API key using CDP method")
        print("3. Call endpoint directly (25s vs 85s)")
        print("4. Get 266 items with nutrition data")
    else:
        print("\n- ERROR: Could not retrieve saved endpoint")

    # Show all working endpoints
    print("\n" + "=" * 80)
    print("ALL WORKING API ENDPOINTS")
    print("=" * 80)

    all_endpoints = db.get_working_api_endpoints(min_verifications=0)

    if all_endpoints:
        for ep in all_endpoints:
            print(f"\n{ep['domain']}")
            print(f"  Endpoint: {ep['api_menu_endpoint'][:80]}...")
            print(f"  Type: {ep['api_endpoint_type']}")
            print(f"  Verified: {ep['api_verified_count']} times")
    else:
        print("  No working endpoints found")

    db.clouddestroyer.close()
    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    save_chipotle_endpoint()
