"""
Final comprehensive Chipotle menu parser with names and prices
"""

import json

def parse_chipotle_complete_menu():
    """
    Parse all Chipotle menu data sources and combine into complete menu
    """
    print("=" * 80)
    print("CHIPOTLE COMPLETE MENU EXTRACTION")
    print("=" * 80)

    # Load all data files
    with open('chipotle_universal_meals.json', 'r', encoding='utf-8') as f:
        universal_meals = json.load(f)

    with open('chipotle_menu_metadata.json', 'r', encoding='utf-8') as f:
        menu_metadata = json.load(f)

    print(f"\nData loaded:")
    print(f"  Universal Meals: {len(universal_meals)} meals")
    print(f"  Menu Metadata Items: {len(menu_metadata.get('items', {}))} items")

    all_menu_items = []

    # Parse Universal Meals (these have names and descriptions)
    print("\n" + "=" * 80)
    print("PARSING LIFESTYLE/PRECONFIGURED MEALS")
    print("=" * 80)

    for meal in universal_meals:
        meal_name = meal.get('mealName', 'Unknown Meal')
        meal_type = meal.get('mealType', 'Unknown')
        meal_price = meal.get('mealPrice', 0)
        calories = meal.get('calories', '')
        dietary_tags = meal.get('dietaryTags', [])
        marketing_copy = meal.get('marketingCopy', '')

        # Get entree details
        entree = meal.get('entree', {})
        item_id = entree.get('itemId', '')
        ingredients = entree.get('ingredientsSummary', '')

        menu_item = {
            'item_id': item_id,
            'name': meal_name,
            'category': meal_type,
            'description': marketing_copy or ingredients,
            'price': meal_price,
            'calories': calories,
            'dietary_tags': dietary_tags,
            'ingredients': ingredients
        }

        all_menu_items.append(menu_item)

        price_str = f"${meal_price:.2f}" if meal_price > 0 else "Price varies"
        print(f"  {meal_name} - {price_str} - {calories} cal")

    # Parse Categories from Menu Metadata for standard build-your-own items
    print("\n" + "=" * 80)
    print("PARSING CUSTOMIZABLE MENU CATEGORIES")
    print("=" * 80)

    groups = menu_metadata.get('groups', [])
    items_dict = menu_metadata.get('items', {})

    # We need to construct item names from group displayName + item type
    # For example: "Burrito" group + protein type from CMG-1 (Chicken)
    # But item metadata doesn't have protein names, just nutrition

    # Known protein/base mappings (reverse engineered from universal_meals)
    protein_names = {
        'CMG-1': 'Chicken',
        'CMG-2': 'Steak',
        'CMG-3': 'Barbacoa',
        'CMG-4': 'Carnitas',
        'CMG-5': 'Sofritas',
        'CMG-6': 'Veggie',
        'CMG-7': 'Chorizo',
        'CMG-8': 'Carne Asada',
        'CMG-10': 'Brisket',
        'CMG-11': 'Smoked Brisket',
        'CMG-12': 'Plant-Based Chorizo',
        'CMG-13': 'Pollo Asado',
        'CMG-14': 'Fajita Veggies',
        'CMG-15': 'Guacamole'
    }

    for group in groups:
        group_name = group.get('displayName', 'Unknown')
        group_type = group.get('menuItemType', group.get('type', ''))
        description = group.get('description', '')

        # Skip nested/empty groups
        if group_type in ['nested', 'preconfigured']:
            continue

        print(f"\n{group_name} ({group_type}):")

        # Get items in this group
        group_items = group.get('items', [])

        for item_ref in group_items:
            menu_item_id = item_ref.get('menuItemId')

            # Get item details
            item_details = items_dict.get(menu_item_id, {})
            nutrition = item_details.get('nutrition', [])
            calories = next((n['value'] for n in nutrition if n['name'] == 'Calories'), None)

            # Construct item name
            # Check if this is a base protein (CMG-1 through CMG-15)
            base_protein = protein_names.get(menu_item_id)

            if base_protein:
                item_name = f"{base_protein} {group_name}"
            else:
                # It's a side/drink/other - use menu_item_id as placeholder
                item_name = menu_item_id

            menu_item = {
                'item_id': menu_item_id,
                'name': item_name,
                'category': group_name,
                'category_type': group_type,
                'description': description,
                'price': None,  # Customizable items don't have fixed prices
                'calories': calories,
                'dietary_tags': item_details.get('dietaryTags', [])
            }

            all_menu_items.append(menu_item)

            cal_str = f"{calories} cal" if calories else "Cal varies"
            print(f"    {item_name} - {cal_str}")

    # Parse Sides and Drinks (these might have individual names in itemGroups)
    # Already handled above in groups

    print("\n" + "=" * 80)
    print(f"TOTAL ITEMS EXTRACTED: {len(all_menu_items)}")
    print("=" * 80)

    # Save to file
    with open('chipotle_complete_menu.json', 'w', encoding='utf-8') as f:
        json.dump(all_menu_items, f, indent=2, ensure_ascii=False)

    print("\n+ Saved to: chipotle_complete_menu.json")

    # Summary
    print("\nSummary by Category:")
    print("-" * 80)

    categories = {}
    for item in all_menu_items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = {'count': 0, 'with_price': 0}
        categories[cat]['count'] += 1
        if item.get('price') and item['price'] > 0:
            categories[cat]['with_price'] += 1

    for cat in sorted(categories.keys()):
        count = categories[cat]['count']
        with_price = categories[cat]['with_price']
        print(f"  {cat}: {count} items ({with_price} with prices)")

    # Show items with prices
    print("\n" + "=" * 80)
    print("ITEMS WITH PRICES (Lifestyle Bowls & Special Items):")
    print("=" * 80)

    priced_items = [item for item in all_menu_items if item.get('price') and item['price'] > 0]

    for item in priced_items:
        price_str = f"${item['price']:.2f}"
        cal_str = f"{item['calories']} cal" if item.get('calories') else "Cal varies"
        print(f"  {item['name']:<50} {price_str:>8}  {cal_str}")

    print(f"\nTotal items with prices: {len(priced_items)}")

    return all_menu_items


if __name__ == "__main__":
    items = parse_chipotle_complete_menu()

    print("\n" + "=" * 80)
    print("SAMPLE CUSTOMIZABLE ITEMS:")
    print("=" * 80)

    # Show some burrito options
    burritos = [item for item in items if item['category'] == 'Burrito'][:5]
    for item in burritos:
        print(f"\n{item['name']}")
        if item.get('description'):
            print(f"  {item['description'][:100]}...")
        if item.get('calories'):
            print(f"  Calories: {item['calories']}")
