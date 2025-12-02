"""
Example CloudDestroyer API Client
Shows how to call the API from another application
"""

import requests
import json
from typing import Optional

class CloudDestroyerClient:
    """
    Simple client for CloudDestroyer API
    """

    def __init__(self, api_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize client

        Args:
            api_url: Base URL of the API (default: http://localhost:8000)
            api_key: API key for authentication (optional)
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })

    def health_check(self) -> dict:
        """
        Check if API service is healthy

        Returns:
            dict with status, timestamp, version
        """
        response = self.session.get(f"{self.api_url}/health")
        response.raise_for_status()
        return response.json()

    def extract_menu(
        self,
        website_url: str,
        restaurant_name: Optional[str] = None,
        force_menu_url: Optional[str] = None,
        timeout: int = 120
    ) -> dict:
        """
        Extract restaurant menu

        Args:
            website_url: Restaurant website URL
            restaurant_name: Optional restaurant name
            force_menu_url: Optional specific menu page URL
            timeout: Request timeout in seconds (default: 120)

        Returns:
            MenuExtractionResult dict
        """
        payload = {
            "website_url": website_url
        }

        if restaurant_name:
            payload["restaurant_name"] = restaurant_name

        if force_menu_url:
            payload["force_menu_url"] = force_menu_url

        response = self.session.post(
            f"{self.api_url}/restaurant/extract",
            json=payload,
            timeout=timeout
        )

        response.raise_for_status()
        return response.json()

    def print_menu_summary(self, result: dict):
        """
        Print a nice summary of extraction result

        Args:
            result: MenuExtractionResult dict
        """
        print("=" * 80)
        print("MENU EXTRACTION RESULT")
        print("=" * 80)
        print(f"Restaurant: {result['restaurant_name']}")
        print(f"Success: {result['success']}")
        print(f"Items Found: {result['items_found']}")
        print(f"Categories: {result['categories_found']}")
        print(f"Processing Time: {result['processing_time_seconds']:.1f}s")
        print(f"Confidence: {result['confidence_score']:.2f}")

        if result.get('menu_data') and 'extraction_method' in result['menu_data']:
            print(f"Method: {result['menu_data']['extraction_method']}")

        if result.get('error_message'):
            print(f"Error: {result['error_message']}")

        # Show sample items
        if result.get('menu_data') and 'items' in result['menu_data']:
            items = result['menu_data']['items']
            print(f"\nSample Items (first 10):")
            print("-" * 80)
            for item in items[:10]:
                name = item.get('name', 'Unnamed')
                cat = item.get('category', 'Unknown')
                cal = item.get('calories')
                price = item.get('price')

                line = f"  [{cat}] {name}"
                if cal:
                    line += f" - {cal} cal"
                if price and price > 0:
                    line += f" - ${price:.2f}"

                print(line)


def main():
    """
    Example usage
    """
    print("CloudDestroyer API Client Example")
    print("=" * 80)
    print()

    # Initialize client
    client = CloudDestroyerClient(
        api_url="http://localhost:8000",
        api_key=None  # Set your API key here if needed
    )

    # Check health
    try:
        health = client.health_check()
        print(f"✓ API is healthy (version {health['version']})")
        print()
    except Exception as e:
        print(f"✗ API health check failed: {e}")
        print("Make sure the API server is running:")
        print("  python start_api.py")
        return

    # Extract Chipotle menu
    print("Extracting Chipotle menu...")
    print()

    try:
        result = client.extract_menu(
            website_url="https://www.chipotle.com",
            restaurant_name="Chipotle"
        )

        client.print_menu_summary(result)

        # Save to file
        output_file = "chipotle_api_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print()
        print(f"✓ Full result saved to: {output_file}")

    except requests.exceptions.Timeout:
        print("✗ Request timed out (menu extraction can take 15-60 seconds)")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    main()
