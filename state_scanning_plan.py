#!/usr/bin/env python3
"""
U.S. States Municipality Scanning Plan
Comprehensive list of all 50 states for systematic municipal data collection
"""

# States we've already completed
COMPLETED_STATES = {
    'TX': {'name': 'Texas', 'municipalities': 1227, 'status': 'Complete - In Database'},
    'CA': {'name': 'California', 'municipalities': 483, 'status': 'Complete - In Database'}, 
    'FL': {'name': 'Florida', 'municipalities': 412, 'status': 'Complete - In Database'}
}

# All 50 U.S. States with Wikipedia URLs for municipalities
ALL_STATES = {
    'AL': {
        'name': 'Alabama',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Alabama',
        'priority': 'High',
        'estimated_cities': 461
    },
    'AK': {
        'name': 'Alaska', 
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_boroughs_in_Alaska',
        'priority': 'Medium',
        'estimated_cities': 149
    },
    'AZ': {
        'name': 'Arizona',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Arizona', 
        'priority': 'High',
        'estimated_cities': 91
    },
    'AR': {
        'name': 'Arkansas',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Arkansas',
        'priority': 'Medium',
        'estimated_cities': 502
    },
    'CO': {
        'name': 'Colorado',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Colorado',
        'priority': 'High',
        'estimated_cities': 272
    },
    'CT': {
        'name': 'Connecticut',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Connecticut',
        'priority': 'Medium',
        'estimated_cities': 169
    },
    'DE': {
        'name': 'Delaware',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Delaware',
        'priority': 'Low',
        'estimated_cities': 57
    },
    'GA': {
        'name': 'Georgia',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Georgia_(U.S._state)',
        'priority': 'High',
        'estimated_cities': 535
    },
    'HI': {
        'name': 'Hawaii',
        'url': 'https://en.wikipedia.org/wiki/List_of_places_in_Hawaii',
        'priority': 'Medium',
        'estimated_cities': 5  # Hawaii has unique structure
    },
    'ID': {
        'name': 'Idaho',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Idaho',
        'priority': 'Medium',
        'estimated_cities': 200
    },
    'IL': {
        'name': 'Illinois',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Illinois',
        'priority': 'High',
        'estimated_cities': 1298
    },
    'IN': {
        'name': 'Indiana',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Indiana',
        'priority': 'High',
        'estimated_cities': 569
    },
    'IA': {
        'name': 'Iowa',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Iowa',
        'priority': 'Medium',
        'estimated_cities': 947
    },
    'KS': {
        'name': 'Kansas',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Kansas',
        'priority': 'Medium',
        'estimated_cities': 627
    },
    'KY': {
        'name': 'Kentucky',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Kentucky',
        'priority': 'Medium',
        'estimated_cities': 424
    },
    'LA': {
        'name': 'Louisiana',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Louisiana',
        'priority': 'Medium',
        'estimated_cities': 304
    },
    'ME': {
        'name': 'Maine',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Maine',
        'priority': 'Low',
        'estimated_cities': 488
    },
    'MD': {
        'name': 'Maryland',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Maryland',
        'priority': 'Medium',
        'estimated_cities': 157
    },
    'MA': {
        'name': 'Massachusetts',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Massachusetts',
        'priority': 'High',
        'estimated_cities': 351
    },
    'MI': {
        'name': 'Michigan',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Michigan',
        'priority': 'High',
        'estimated_cities': 533
    },
    'MN': {
        'name': 'Minnesota',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Minnesota',
        'priority': 'High',
        'estimated_cities': 853
    },
    'MS': {
        'name': 'Mississippi',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Mississippi',
        'priority': 'Medium',
        'estimated_cities': 298
    },
    'MO': {
        'name': 'Missouri',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Missouri',
        'priority': 'High',
        'estimated_cities': 955
    },
    'MT': {
        'name': 'Montana',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Montana',
        'priority': 'Low',
        'estimated_cities': 129
    },
    'NE': {
        'name': 'Nebraska',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Nebraska',
        'priority': 'Medium',
        'estimated_cities': 531
    },
    'NV': {
        'name': 'Nevada',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Nevada',
        'priority': 'Medium',
        'estimated_cities': 19
    },
    'NH': {
        'name': 'New Hampshire',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_New_Hampshire',
        'priority': 'Low',
        'estimated_cities': 234
    },
    'NJ': {
        'name': 'New Jersey',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_New_Jersey',
        'priority': 'High',
        'estimated_cities': 565
    },
    'NM': {
        'name': 'New Mexico',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_New_Mexico',
        'priority': 'Medium',
        'estimated_cities': 106
    },
    'NY': {
        'name': 'New York',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_New_York',
        'priority': 'High',
        'estimated_cities': 62  # Cities only, towns separate
    },
    'NC': {
        'name': 'North Carolina',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_North_Carolina',
        'priority': 'High',
        'estimated_cities': 553
    },
    'ND': {
        'name': 'North Dakota',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_North_Dakota',
        'priority': 'Low',
        'estimated_cities': 357
    },
    'OH': {
        'name': 'Ohio',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Ohio',
        'priority': 'High',
        'estimated_cities': 938
    },
    'OK': {
        'name': 'Oklahoma',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Oklahoma',
        'priority': 'High',
        'estimated_cities': 596
    },
    'OR': {
        'name': 'Oregon',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_Oregon',
        'priority': 'Medium',
        'estimated_cities': 241
    },
    'PA': {
        'name': 'Pennsylvania',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Pennsylvania',
        'priority': 'High',
        'estimated_cities': 2562  # Very large number
    },
    'RI': {
        'name': 'Rhode Island',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Rhode_Island',
        'priority': 'Low',
        'estimated_cities': 39
    },
    'SC': {
        'name': 'South Carolina',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_South_Carolina',
        'priority': 'Medium',
        'estimated_cities': 269
    },
    'SD': {
        'name': 'South Dakota',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_South_Dakota',
        'priority': 'Low',
        'estimated_cities': 311
    },
    'TN': {
        'name': 'Tennessee',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Tennessee',
        'priority': 'High',
        'estimated_cities': 345
    },
    'UT': {
        'name': 'Utah',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Utah',
        'priority': 'Medium',
        'estimated_cities': 248
    },
    'VT': {
        'name': 'Vermont',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Vermont',
        'priority': 'Low',
        'estimated_cities': 255
    },
    'VA': {
        'name': 'Virginia',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Virginia',
        'priority': 'High',
        'estimated_cities': 230
    },
    'WA': {
        'name': 'Washington',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Washington',
        'priority': 'High',
        'estimated_cities': 281
    },
    'WV': {
        'name': 'West Virginia',
        'url': 'https://en.wikipedia.org/wiki/List_of_cities_in_West_Virginia',
        'priority': 'Low',
        'estimated_cities': 232
    },
    'WI': {
        'name': 'Wisconsin',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Wisconsin',
        'priority': 'High',
        'estimated_cities': 601
    },
    'WY': {
        'name': 'Wyoming',
        'url': 'https://en.wikipedia.org/wiki/List_of_municipalities_in_Wyoming',
        'priority': 'Low',
        'estimated_cities': 99
    }
}

def get_next_priority_states():
    """Get the next states to scan based on priority"""
    
    completed_codes = set(COMPLETED_STATES.keys())
    
    # High priority states (large populations, major metro areas)
    high_priority = []
    medium_priority = []
    low_priority = []
    
    for code, info in ALL_STATES.items():
        if code not in completed_codes:
            if info['priority'] == 'High':
                high_priority.append((code, info))
            elif info['priority'] == 'Medium':
                medium_priority.append((code, info))
            else:
                low_priority.append((code, info))
    
    # Sort by estimated cities (descending)
    high_priority.sort(key=lambda x: x[1]['estimated_cities'], reverse=True)
    medium_priority.sort(key=lambda x: x[1]['estimated_cities'], reverse=True)
    low_priority.sort(key=lambda x: x[1]['estimated_cities'], reverse=True)
    
    return high_priority, medium_priority, low_priority

def print_scanning_plan():
    """Print the complete scanning plan"""
    
    print("🗺️ U.S. STATES MUNICIPALITY SCANNING PLAN")
    print("=" * 60)
    
    # Show completed states
    print("✅ COMPLETED STATES (3/50)")
    print("-" * 30)
    for code, info in COMPLETED_STATES.items():
        print(f"{code}: {info['name']} - {info['municipalities']} municipalities")
    
    # Show next states by priority
    high, medium, low = get_next_priority_states()
    
    print(f"\n🔥 HIGH PRIORITY STATES ({len(high)} remaining)")
    print("-" * 30)
    print("State | Name                | Est. Cities | URL")
    print("------|---------------------|-------------|---------------------------")
    for code, info in high:
        name = info['name'][:18].ljust(18)
        cities = str(info['estimated_cities']).rjust(8)
        print(f" {code}   | {name} | {cities}    | Wikipedia")
    
    print(f"\n⚡ MEDIUM PRIORITY STATES ({len(medium)} remaining)")
    print("-" * 30)
    print("State | Name                | Est. Cities")
    print("------|---------------------|------------")
    for code, info in medium[:10]:  # Show first 10
        name = info['name'][:18].ljust(18)
        cities = str(info['estimated_cities']).rjust(8)
        print(f" {code}   | {name} | {cities}")
    
    if len(medium) > 10:
        print(f"      | ... and {len(medium)-10} more medium priority states")
    
    print(f"\n📍 LOW PRIORITY STATES ({len(low)} remaining)")
    print("-" * 30)
    total_low_cities = sum(info['estimated_cities'] for _, info in low)
    print(f"Total: {len(low)} states with ~{total_low_cities:,} estimated cities")
    
    # Show totals
    total_remaining = len(high) + len(medium) + len(low)
    total_completed = len(COMPLETED_STATES)
    
    print(f"\n📊 PROGRESS SUMMARY")
    print(f"-" * 20)
    print(f"✅ Completed: {total_completed}/50 states")
    print(f"🎯 Remaining: {total_remaining}/50 states")
    print(f"🏆 Progress: {(total_completed/50)*100:.1f}%")
    
    # Recommend next state
    if high:
        next_state_code, next_state_info = high[0]
        print(f"\n🚀 RECOMMENDED NEXT STATE")
        print(f"-" * 25)
        print(f"State: {next_state_info['name']} ({next_state_code})")
        print(f"Estimated Cities: {next_state_info['estimated_cities']:,}")
        print(f"Priority: {next_state_info['priority']}")
        print(f"URL: {next_state_info['url']}")
        
        return next_state_code, next_state_info
    
    return None, None

if __name__ == "__main__":
    next_code, next_info = print_scanning_plan()
    
    if next_code:
        print(f"\n💡 Ready to scan {next_info['name']}!")
        print(f"Run: python generic_state_scraper.py \"{next_info['name']}\" \"{next_info['url']}\"")