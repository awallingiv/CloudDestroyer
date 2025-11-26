#!/usr/bin/env python3
"""
California Municipalities Data Analysis
Analyzes the scraped California municipalities data
"""

import json
import glob
from collections import Counter, defaultdict

def analyze_california_data():
    """Analyze California municipalities data"""
    
    # Find the latest California data file
    files = glob.glob("StateJsons/california_municipalities_*.json")
    if not files:
        print("❌ No California municipalities data files found!")
        return
    
    latest_file = max(files)
    print(f"📊 Analyzing: {latest_file}\n")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    municipalities = data['municipalities']
    
    # Basic statistics
    print("📈 CALIFORNIA MUNICIPALITIES STATISTICS")
    print("=" * 50)
    print(f"🏙️ Total municipalities: {len(municipalities):,}")
    
    # Population analysis
    populations = [m['population'] for m in municipalities if m.get('population')]
    if populations:
        print(f"👥 With population data: {len(populations):,}")
        print(f"👥 Total population: {sum(populations):,}")
        print(f"📊 Average population: {sum(populations)//len(populations):,}")
        print(f"🏆 Largest: {max(populations):,}")
        print(f"🏘️ Smallest: {min(populations):,}")
    
    # County distribution
    counties = [m['primary_county'] for m in municipalities if m.get('primary_county')]
    county_counts = Counter(counties)
    
    print(f"\n🗺️ COUNTY DISTRIBUTION ({len(county_counts)} counties)")
    print("=" * 50)
    print("Top 10 counties by number of municipalities:")
    for i, (county, count) in enumerate(county_counts.most_common(10), 1):
        print(f"{i:2d}. {county:<20} {count:3d} municipalities")
    
    # Population by county
    county_populations = defaultdict(list)
    for m in municipalities:
        if m.get('primary_county') and m.get('population'):
            county_populations[m['primary_county']].append(m['population'])
    
    county_totals = {
        county: sum(pops) 
        for county, pops in county_populations.items()
    }
    
    print(f"\n👥 TOP 10 COUNTIES BY TOTAL POPULATION")
    print("=" * 50)
    for i, (county, total_pop) in enumerate(
        sorted(county_totals.items(), key=lambda x: x[1], reverse=True)[:10], 1
    ):
        avg_pop = total_pop // len(county_populations[county])
        muni_count = len(county_populations[county])
        print(f"{i:2d}. {county:<20} {total_pop:>10,} ({muni_count} cities, avg: {avg_pop:,})")
    
    # Largest cities
    print(f"\n🏆 TOP 15 LARGEST CITIES")
    print("=" * 50)
    largest_cities = sorted(
        [(m['name'], m.get('population', 0), m.get('primary_county', 'Unknown')) 
         for m in municipalities if m.get('population')],
        key=lambda x: x[1],
        reverse=True
    )[:15]
    
    for i, (name, pop, county) in enumerate(largest_cities, 1):
        name_display = name[:25] + "..." if len(name) > 25 else name
        print(f"{i:2d}. {name_display:<28} {pop:>10,} ({county})")
    
    # Small cities (under 1000)
    small_cities = [m for m in municipalities if m.get('population', 0) < 1000]
    print(f"\n🏘️ SMALL CITIES (Population < 1,000)")
    print("=" * 50)
    print(f"Total small cities: {len(small_cities)}")
    
    if small_cities:
        print("Smallest 10 cities:")
        smallest = sorted(small_cities, key=lambda x: x.get('population', 0))[:10]
        for i, city in enumerate(smallest, 1):
            name = city['name'][:25] + "..." if len(city['name']) > 25 else city['name']
            pop = city.get('population', 0)
            county = city.get('primary_county', 'Unknown')
            print(f"{i:2d}. {name:<28} {pop:>6,} ({county})")
    
    # Population ranges
    print(f"\n📊 POPULATION DISTRIBUTION")
    print("=" * 50)
    ranges = [
        ("Under 1,000", lambda p: p < 1000),
        ("1,000 - 5,000", lambda p: 1000 <= p < 5000),
        ("5,000 - 25,000", lambda p: 5000 <= p < 25000),
        ("25,000 - 100,000", lambda p: 25000 <= p < 100000),
        ("100,000 - 500,000", lambda p: 100000 <= p < 500000),
        ("500,000+", lambda p: p >= 500000)
    ]
    
    for range_name, range_func in ranges:
        count = len([m for m in municipalities if m.get('population') and range_func(m['population'])])
        percentage = (count / len(populations)) * 100 if populations else 0
        print(f"{range_name:<20} {count:3d} cities ({percentage:4.1f}%)")

if __name__ == "__main__":
    analyze_california_data()