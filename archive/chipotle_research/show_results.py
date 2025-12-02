"""Display results from the Bubba's 33 scraping test"""
import json

# Load the results
with open('bubba_menu_results_20251202_084641.json', 'r') as f:
    data = json.load(f)

print("="*80)
print("BUBBA'S 33 MENU SCRAPING RESULTS")
print("="*80)
print(f"Success: {data['success']}")
print(f"Restaurant: {data['restaurant_name']}")
print(f"Website: {data['website_url']}")
print(f"Menu URL: {data['menu_url']}")
print(f"Duration: {data['processing_time_seconds']:.2f} seconds")
print(f"Confidence Score: {data['confidence_score']:.2f}")
print()

menu_data = data['menu_data']
categories = menu_data['categories']
items = menu_data['items']

print(f"Categories Found: {len(categories)}")
for i, cat_name in enumerate(list(categories.keys())[:10], 1):
    item_count = len(categories[cat_name])
    print(f"  {i}. {cat_name} ({item_count} items)")

if len(categories) > 10:
    print(f"  ... and {len(categories) - 10} more categories")

print()
print(f"Total Menu Items: {len(items)}")

# Count items with prices
items_with_prices = sum(1 for item in items if item.get('price'))
print(f"Items with Prices: {items_with_prices} ({items_with_prices/len(items)*100:.1f}%)" if items else "N/A")

print()
print("Sample Menu Items:")
for i, item in enumerate(items[:15], 1):
    name = item.get('name', 'Unknown')
    price = item.get('price', 'N/A')
    category = item.get('category', 'Uncategorized')
    desc = item.get('description', '')[:60] + "..." if len(item.get('description', '')) > 60 else item.get('description', '')

    if price and price != 'N/A' and price != '':
        print(f"  {i}. [{category}] {name} - ${price}")
    else:
        print(f"  {i}. [{category}] {name}")
    if desc:
        print(f"      {desc}")

if len(items) > 15:
    print(f"\n  ... and {len(items) - 15} more items")

print()
print("="*80)
print("SCRAPING TEST SUCCESSFUL!")
print(f"Extracted {len(items)} menu items from {len(categories)} categories")
print("="*80)
