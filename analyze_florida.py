import json
from collections import Counter

# Load Florida data
with open('StateJsons/florida_municipalities_20251121_215806.json', 'r', encoding='utf-8') as f:
    fl_data = json.load(f)

municipalities = fl_data['municipalities']
print('🏖️ FLORIDA MUNICIPALITIES ANALYSIS')
print('=' * 50)

print(f'📊 Total: {len(municipalities)} municipalities')
print(f'📍 Counties: {len(fl_data["metadata"]["counties"])} counties')

# Population stats
populations = [m.get('population', 0) for m in municipalities if m.get('population', 0) > 0]
if populations:
    print(f'👥 Population Range: {min(populations):,} to {max(populations):,}')
    print(f'📈 Total Population: {sum(populations):,}')

# Top counties by municipality count  
counties = [m.get('primary_county', '') for m in municipalities if m.get('primary_county')]
county_counts = Counter(counties)
print(f'\n🏛️ TOP 10 COUNTIES BY MUNICIPALITY COUNT:')
for county, count in county_counts.most_common(10):
    if county:
        print(f'   {county}: {count} municipalities')

print(f'\n🏆 TOP 10 LARGEST FLORIDA CITIES:')
largest_cities = sorted([m for m in municipalities if m.get('population', 0) > 0], 
                       key=lambda x: x.get('population', 0), reverse=True)[:10]
for i, city in enumerate(largest_cities):
    name = city.get('name', 'Unknown')
    pop = city.get('population', 0)
    county = city.get('primary_county', 'Unknown')
    print(f'   {i+1:2d}. {name:<20} {pop:>8,} ({county})')