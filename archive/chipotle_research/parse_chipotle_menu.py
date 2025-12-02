"""
Parse Chipotle menu_metadata.json to extract menu items with proper names
"""

import json

def parse_chipotle_menu():
    """
    Parse the complex Chipotle menu structure
    """
    print("=" * 80)
    print("PARSING CHIPOTLE MENU STRUCTURE")
    print("=" * 80)

    with open('chipotle_menu_metadata.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract structure
    groups = data.get('groups', [])
    items_dict = data.get('items', {})  # Dict with item IDs as keys
    item_groups = data.get('itemGroups', {})  # Additional item metadata

    print(f"\nData Structure:")
    print(f"  Groups (categories): {len(groups)}")
    print(f"  Items: {len(items_dict)}")
    print(f"  Item Groups: {len(item_groups)}")

    all_menu_items = []

    # Process each group (category)
    for group in groups:
        group_name = group.get('displayName', 'Unknown Category')
        group_type = group.get('menuItemType', group.get('type', 'Unknown'))
        group_description = group.get('description', '')

        print(f"\n{group_name} ({group_type}):")
        print(f"  {group_description[:100]}..." if len(group_description) > 100 else f"  {group_description}")

        # Get items in this group
        group_items = group.get('items', [])

        for item_ref in group_items:
            menu_item_id = item_ref.get('menuItemId')
            sort_order = item_ref.get('sortOrder', 0)

            # Look up item details in items_dict
            item_details = items_dict.get(menu_item_id, {})

            # Look up item group info for name and description
            item_group_info = item_groups.get(menu_item_id, {})

            # Extract item information
            item_name = item_group_info.get('displayName') or item_group_info.get('name') or menu_item_id
            item_description = item_group_info.get('description', '')

            # Nutrition info
            nutrition = item_details.get('nutrition', [])
            calories = next((n['value'] for n in nutrition if n['name'] == 'Calories'), None)

            # Build menu item
            menu_item = {
                'item_id': menu_item_id,
                'name': item_name,
                'category': group_name,
                'category_type': group_type,
                'description': item_description,
                'calories': calories,
                'sort_order': sort_order,
                'dietary_tags': item_details.get('dietaryTags', []),
                'thumbnail_url': item_details.get('thumbnailUrl', '')
            }

            all_menu_items.append(menu_item)

            print(f"    [{sort_order}] {item_name} - {calories} cal" if calories else f"    [{sort_order}] {item_name}")

    print(f"\n{'=' * 80}")
    print(f"TOTAL ITEMS EXTRACTED: {len(all_menu_items)}")
    print(f"{'=' * 80}")

    # Save to file
    with open('chipotle_full_menu.json', 'w', encoding='utf-8') as f:
        json.dump(all_menu_items, f, indent=2, ensure_ascii=False)

    print("\n+ Saved to: chipotle_full_menu.json")

    # Show summary by category
    print("\nSummary by Category:")
    print("-" * 80)

    categories = {}
    for item in all_menu_items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} items")

    return all_menu_items


if __name__ == "__main__":
    items = parse_chipotle_menu()

    # Show sample items with full details
    print("\n" + "=" * 80)
    print("SAMPLE ITEMS (First 10):")
    print("=" * 80)

    for item in items[:10]:
        print(f"\n{item['name']}")
        print(f"  Category: {item['category']}")
        if item['description']:
            print(f"  Description: {item['description'][:100]}...")
        if item['calories']:
            print(f"  Calories: {item['calories']}")
        if item['dietary_tags']:
            print(f"  Dietary: {', '.join(item['dietary_tags'])}")
