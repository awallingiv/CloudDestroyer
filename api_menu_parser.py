"""
API Menu Parser - Intelligently parses menu data from various API formats
Handles Chipotle-style, OLO, GraphQL, and generic REST APIs
"""

import json
import requests
from typing import Dict, List, Optional
from loguru import logger


class APIMenuParser:
    """
    Parse menu data from various API formats
    """

    def __init__(self, api_key_headers: Dict[str, str] = None):
        """
        Args:
            api_key_headers: Dict of header names and values (e.g., {'Ocp-Apim-Subscription-Key': 'key'})
        """
        self.api_key_headers = api_key_headers or {}
        self.session = requests.Session()

    def fetch_and_parse(self, url: str, timeout: int = 15) -> Dict:
        """
        Fetch API endpoint and intelligently parse the response

        Returns:
            Dict with 'items', 'categories', 'success', 'raw_data'
        """
        logger.info(f"Fetching: {url}")

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            **self.api_key_headers
        }

        try:
            response = self.session.get(url, headers=headers, timeout=timeout)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Failed: {response.status_code} - {response.text[:200]}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'items': [],
                    'categories': []
                }

            data = response.json()
            logger.success(f"Received {len(json.dumps(data))} bytes")

            # Try different parsing strategies
            result = self._parse_response(data)
            result['raw_data'] = data
            result['success'] = len(result['items']) > 0

            logger.info(f"Parsed {len(result['items'])} items in {len(result['categories'])} categories")

            return result

        except Exception as e:
            logger.error(f"Error fetching/parsing: {e}")
            return {
                'success': False,
                'error': str(e),
                'items': [],
                'categories': []
            }

    def _parse_response(self, data: Dict) -> Dict:
        """
        Intelligently parse response based on structure
        """
        items = []
        categories = []

        # Strategy 1: Chipotle-style (groups + items dict + itemGroups)
        if 'groups' in data and 'items' in data:
            logger.info("Detected Chipotle-style API structure")
            result = self._parse_chipotle_style(data)
            if result['items']:
                return result

        # Strategy 2: OLO-style (menuData with categories)
        if 'menuData' in data or 'menu' in data:
            logger.info("Detected OLO-style API structure")
            result = self._parse_olo_style(data)
            if result['items']:
                return result

        # Strategy 3: Simple categories array
        if 'categories' in data and isinstance(data['categories'], list):
            logger.info("Detected categories array structure")
            result = self._parse_categories_array(data['categories'])
            if result['items']:
                return result

        # Strategy 4: Direct items array
        if 'items' in data and isinstance(data['items'], list):
            logger.info("Detected direct items array")
            result = self._parse_items_array(data['items'])
            if result['items']:
                return result

        # Strategy 5: Universal meals (Chipotle lifestyle bowls)
        if isinstance(data, list) and len(data) > 0 and 'mealName' in data[0]:
            logger.info("Detected universal meals structure")
            result = self._parse_universal_meals(data)
            if result['items']:
                return result

        logger.warning("Could not detect API structure, returning empty")
        return {'items': [], 'categories': []}

    def _parse_chipotle_style(self, data: Dict) -> Dict:
        """
        Parse Chipotle-style API with groups, items dict, and itemGroups
        """
        items = []
        categories = []

        groups = data.get('groups', [])
        items_dict = data.get('items', {})
        item_groups = data.get('itemGroups', {})

        # Known protein mappings (could be expanded)
        protein_names = {
            'CMG-1': 'Chicken', 'CMG-2': 'Steak', 'CMG-3': 'Barbacoa',
            'CMG-4': 'Carnitas', 'CMG-5': 'Sofritas', 'CMG-6': 'Veggie',
            'CMG-8': 'Carne Asada', 'CMG-10': 'Brisket'
        }

        for group in groups:
            group_name = group.get('displayName', 'Unknown')
            group_type = group.get('menuItemType', group.get('type', ''))
            description = group.get('description', '')

            # Skip preconfigured/nested groups
            if group_type in ['nested', 'preconfigured']:
                continue

            categories.append({
                'name': group_name,
                'description': description,
                'type': group_type
            })

            group_items = group.get('items', [])

            for item_ref in group_items:
                menu_item_id = item_ref.get('menuItemId')
                item_details = items_dict.get(menu_item_id, {})

                # Get nutrition
                nutrition = item_details.get('nutrition', [])
                calories = next((n['value'] for n in nutrition if n['name'] == 'Calories'), None)

                # Try to get name from protein mapping
                base_protein = protein_names.get(menu_item_id)
                if base_protein:
                    item_name = f"{base_protein} {group_name}"
                else:
                    # Check itemGroups for name
                    item_group_info = item_groups.get(menu_item_id, {})
                    item_name = item_group_info.get('displayName') or menu_item_id

                items.append({
                    'item_id': menu_item_id,
                    'name': item_name,
                    'category': group_name,
                    'description': description,
                    'calories': calories,
                    'price': None,
                    'dietary_tags': item_details.get('dietaryTags', [])
                })

        return {'items': items, 'categories': categories}

    def _parse_olo_style(self, data: Dict) -> Dict:
        """
        Parse OLO-style API (like Bubba's 33)
        """
        items = []
        categories = []

        menu_data = data.get('menuData') or data.get('menu', {})

        if isinstance(menu_data, dict):
            menu_categories = menu_data.get('categories', [])

            for category in menu_categories:
                cat_name = category.get('name', 'Unknown')
                categories.append({
                    'name': cat_name,
                    'description': category.get('description', '')
                })

                for item in category.get('items', []):
                    items.append({
                        'item_id': item.get('id') or item.get('itemId'),
                        'name': item.get('name') or item.get('displayName'),
                        'category': cat_name,
                        'description': item.get('description', ''),
                        'price': item.get('price') or item.get('basePrice'),
                        'calories': item.get('calories')
                    })

        return {'items': items, 'categories': categories}

    def _parse_categories_array(self, categories_data: List) -> Dict:
        """
        Parse simple categories array structure
        """
        items = []
        categories = []

        for category in categories_data:
            cat_name = category.get('name') or category.get('categoryName', 'Unknown')
            categories.append({
                'name': cat_name,
                'description': category.get('description', '')
            })

            category_items = category.get('items') or category.get('products', [])

            for item in category_items:
                items.append({
                    'item_id': item.get('id') or item.get('productId'),
                    'name': item.get('name') or item.get('title'),
                    'category': cat_name,
                    'description': item.get('description', ''),
                    'price': item.get('price'),
                    'calories': item.get('calories')
                })

        return {'items': items, 'categories': categories}

    def _parse_items_array(self, items_data: List) -> Dict:
        """
        Parse direct items array
        """
        items = []

        for item in items_data:
            items.append({
                'item_id': item.get('id'),
                'name': item.get('name') or item.get('title'),
                'category': item.get('category', 'Uncategorized'),
                'description': item.get('description', ''),
                'price': item.get('price'),
                'calories': item.get('calories')
            })

        # Extract unique categories
        categories = list({item['category'] for item in items})
        categories = [{'name': cat, 'description': ''} for cat in categories]

        return {'items': items, 'categories': categories}

    def _parse_universal_meals(self, meals_data: List) -> Dict:
        """
        Parse Chipotle universal meals (lifestyle bowls)
        """
        items = []

        for meal in meals_data:
            items.append({
                'item_id': meal.get('mealId'),
                'name': meal.get('mealName', 'Unknown'),
                'category': meal.get('mealType', 'Meals'),
                'description': meal.get('marketingCopy', ''),
                'price': meal.get('mealPrice', 0),
                'calories': meal.get('calories'),
                'dietary_tags': meal.get('dietaryTags', [])
            })

        categories = [{'name': 'Lifestyle Meals', 'description': 'Preconfigured healthy bowls'}]

        return {'items': items, 'categories': categories}


if __name__ == "__main__":
    # Test with sample data
    parser = APIMenuParser(api_key_headers={
        'Ocp-Apim-Subscription-Key': 'test-key'
    })

    # Would test with actual endpoint
    # result = parser.fetch_and_parse("https://api.example.com/menu")
    # print(f"Found {len(result['items'])} items")
