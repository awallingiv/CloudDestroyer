#!/usr/bin/env python3
"""
Multi-State Municipalities Comparison Analysis
Compares Texas, Florida, and California municipalities data
"""

import json
import glob
from collections import Counter, defaultdict

def load_latest_data(state_name):
    """Load the latest data file for a given state"""
    pattern = f"StateJsons/{state_name.lower()}_municipalities_*.json"
    files = glob.glob(pattern)
    if not files:
        return None, None
    
    latest_file = max(files)
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data, latest_file

def analyze_multi_state():
    """Compare municipalities across Texas, Florida, and California"""
    
    print("🇺🇸 MULTI-STATE MUNICIPALITIES COMPARISON")
    print("=" * 60)
    
    states_data = {}
    
    # Load data for each state
    for state in ['texas', 'florida', 'california']:
        data, filename = load_latest_data(state)
        if data:
            states_data[state.title()] = {
                'data': data,
                'file': filename,
                'municipalities': data['municipalities']
            }
            print(f"✅ {state.title()}: Loaded {filename}")
        else:
            print(f"❌ {state.title()}: No data file found")
    
    if not states_data:
        print("❌ No state data found!")
        return
    
    print("\n📊 BASIC STATISTICS COMPARISON")
    print("=" * 60)
    print(f"{'State':<12} {'Cities':<8} {'Population':<12} {'Avg Pop':<10} {'Counties':<10}")
    print("-" * 60)
    
    state_summaries = {}
    
    for state_name, state_info in states_data.items():
        municipalities = state_info['municipalities']
        
        # Basic stats
        total_cities = len(municipalities)
        populations = [m['population'] for m in municipalities if m.get('population')]
        total_pop = sum(populations) if populations else 0
        avg_pop = total_pop // len(populations) if populations else 0
        
        counties = set(m['primary_county'] for m in municipalities if m.get('primary_county'))
        county_count = len(counties)
        
        state_summaries[state_name] = {
            'cities': total_cities,
            'population': total_pop,
            'avg_population': avg_pop,
            'counties': county_count,
            'municipalities': municipalities
        }
        
        print(f"{state_name:<12} {total_cities:<8,} {total_pop:<12,} {avg_pop:<10,} {county_count:<10}")
    
    # Find largest cities across all states
    print(f"\n🏆 TOP 20 LARGEST CITIES (ALL STATES)")
    print("=" * 60)
    
    all_cities = []
    for state_name, summary in state_summaries.items():
        for m in summary['municipalities']:
            if m.get('population'):
                all_cities.append({
                    'name': m['name'],
                    'population': m['population'],
                    'state': state_name,
                    'county': m.get('primary_county', 'Unknown')
                })
    
    all_cities.sort(key=lambda x: x['population'], reverse=True)
    
    for i, city in enumerate(all_cities[:20], 1):
        name = city['name'][:20] + "..." if len(city['name']) > 20 else city['name']
        print(f"{i:2d}. {name:<23} {city['population']:>10,} ({city['state']}, {city['county']})")
    
    # State comparisons
    print(f"\n📈 STATE RANKINGS")
    print("=" * 60)
    
    # By total cities
    by_cities = sorted(state_summaries.items(), key=lambda x: x[1]['cities'], reverse=True)
    print("By number of municipalities:")
    for i, (state, data) in enumerate(by_cities, 1):
        print(f"  {i}. {state}: {data['cities']:,} municipalities")
    
    # By total population
    by_population = sorted(state_summaries.items(), key=lambda x: x[1]['population'], reverse=True)
    print("\nBy total municipal population:")
    for i, (state, data) in enumerate(by_population, 1):
        print(f"  {i}. {state}: {data['population']:,} people")
    
    # By average population
    by_avg_pop = sorted(state_summaries.items(), key=lambda x: x[1]['avg_population'], reverse=True)
    print("\nBy average municipal population:")
    for i, (state, data) in enumerate(by_avg_pop, 1):
        print(f"  {i}. {state}: {data['avg_population']:,} people per city")
    
    # Population distribution comparison
    print(f"\n📊 POPULATION DISTRIBUTION COMPARISON")
    print("=" * 60)
    
    ranges = [
        ("Under 1K", lambda p: p < 1000),
        ("1K-5K", lambda p: 1000 <= p < 5000),
        ("5K-25K", lambda p: 5000 <= p < 25000),
        ("25K-100K", lambda p: 25000 <= p < 100000),
        ("100K-500K", lambda p: 100000 <= p < 500000),
        ("500K+", lambda p: p >= 500000)
    ]
    
    print(f"{'Range':<12} {'Texas':<8} {'Florida':<8} {'California':<8}")
    print("-" * 40)
    
    for range_name, range_func in ranges:
        row = f"{range_name:<12}"
        for state_name, summary in [('Texas', state_summaries.get('Texas')), 
                                   ('Florida', state_summaries.get('Florida')), 
                                   ('California', state_summaries.get('California'))]:
            if summary:
                count = len([m for m in summary['municipalities'] 
                           if m.get('population') and range_func(m['population'])])
                row += f" {count:<8}"
            else:
                row += f" {'N/A':<8}"
        print(row)
    
    # Interesting insights
    print(f"\n🔍 INTERESTING INSIGHTS")
    print("=" * 60)
    
    # Find smallest and largest cities across states
    smallest_city = min(all_cities, key=lambda x: x['population'])
    largest_city = max(all_cities, key=lambda x: x['population'])
    
    print(f"🏘️ Smallest city: {smallest_city['name']} ({smallest_city['state']}) - {smallest_city['population']:,} people")
    print(f"🏙️ Largest city: {largest_city['name']} ({largest_city['state']}) - {largest_city['population']:,} people")
    
    # Population ratio
    ratio = largest_city['population'] / smallest_city['population']
    print(f"📊 Size ratio (largest/smallest): {ratio:,.0f}x")
    
    # States with most large cities (>100k)
    large_cities_by_state = defaultdict(int)
    for city in all_cities:
        if city['population'] >= 100000:
            large_cities_by_state[city['state']] += 1
    
    print(f"\n🏙️ Large cities (100K+ population) by state:")
    for state, count in sorted(large_cities_by_state.items(), key=lambda x: x[1], reverse=True):
        print(f"  {state}: {count} large cities")
    
    # Average county size
    print(f"\n🗺️ Average municipalities per county:")
    for state_name, summary in state_summaries.items():
        avg_per_county = summary['cities'] / summary['counties'] if summary['counties'] > 0 else 0
        print(f"  {state_name}: {avg_per_county:.1f} municipalities per county")

if __name__ == "__main__":
    analyze_multi_state()