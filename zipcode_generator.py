"""
Simple ZIP Code Data Generator
Creates ZIP code data using known patterns and ranges
"""
import sys
import os
import csv
import json
from pathlib import Path
from typing import List, Dict

class ZipCodeGenerator:
    def __init__(self):
        self.output_dir = Path("StateZipCodes")
        self.output_dir.mkdir(exist_ok=True)
        
        # ZIP code prefixes by state (first 3 digits)
        self.state_zip_prefixes = {
            'Alabama': ['350-369'],
            'Alaska': ['995-999'],
            'Arizona': ['850-865'],
            'Arkansas': ['716-729', '754-755'],
            'California': ['900-961'],
            'Colorado': ['800-816'],
            'Connecticut': ['060-069'],
            'Delaware': ['197-199'],
            'Florida': ['320-349'],
            'Georgia': ['300-319'],
            'Hawaii': ['967-968'],
            'Idaho': ['832-838'],
            'Illinois': ['600-629'],
            'Indiana': ['460-479'],
            'Iowa': ['500-528'],
            'Kansas': ['660-679'],
            'Kentucky': ['400-427'],
            'Louisiana': ['700-715'],
            'Maine': ['039-049'],
            'Maryland': ['206-219'],
            'Massachusetts': ['010-027'],
            'Michigan': ['480-499'],
            'Minnesota': ['550-567'],
            'Mississippi': ['386-399'],
            'Missouri': ['630-659'],
            'Montana': ['590-599'],
            'Nebraska': ['680-693'],
            'Nevada': ['889-898'],
            'New Hampshire': ['030-038'],
            'New Jersey': ['070-089'],
            'New Mexico': ['870-884'],
            'New York': ['100-149'],
            'North Carolina': ['270-289'],
            'North Dakota': ['580-589'],
            'Ohio': ['430-459'],
            'Oklahoma': ['730-749'],
            'Oregon': ['970-979'],
            'Pennsylvania': ['150-196'],
            'Rhode Island': ['028-029'],
            'South Carolina': ['290-299'],
            'South Dakota': ['570-577'],
            'Tennessee': ['370-385'],
            'Texas': ['750-799'],
            'Utah': ['840-847'],
            'Vermont': ['050-059'],
            'Virginia': ['220-246'],
            'Washington': ['980-994'],
            'West Virginia': ['247-268'],
            'Wisconsin': ['530-549'],
            'Wyoming': ['820-831']
        }
    
    def generate_state_zipcodes(self, state_name: str) -> List[Dict]:
        """Generate ZIP codes for a state using known prefixes"""
        
        if state_name not in self.state_zip_prefixes:
            print(f"❌ Unknown state: {state_name}")
            return []
        
        print(f"🏛️  Generating ZIP codes for {state_name}")
        
        zipcodes = []
        prefixes = self.state_zip_prefixes[state_name]
        
        for prefix_range in prefixes:
            if '-' in prefix_range:
                start, end = prefix_range.split('-')
                start_num = int(start)
                end_num = int(end)
                
                for prefix in range(start_num, end_num + 1):
                    # Generate all possible ZIP codes for this prefix
                    prefix_str = f"{prefix:03d}"
                    
                    # For now, generate some sample ZIP codes (00-99 range)
                    for suffix in range(0, 100, 5):  # Every 5th to keep it manageable
                        zip_code = f"{prefix_str}{suffix:02d}"
                        
                        zipcodes.append({
                            'zip_code': zip_code,
                            'city': f"City_{zip_code}",  # Placeholder
                            'state': state_name,
                            'county': f"County_{prefix_str}",  # Placeholder  
                            'latitude': '',
                            'longitude': ''
                        })
        
        print(f"✅ Generated {len(zipcodes)} ZIP codes for {state_name}")
        return zipcodes
    
    def save_to_csv(self, state_name: str, zipcodes: List[Dict]):
        """Save ZIP codes to CSV file"""
        if not zipcodes:
            return
            
        filename = self.output_dir / f"{state_name.replace(' ', '_')}_zipcodes.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['zip_code', 'city', 'state', 'county', 'latitude', 'longitude']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for zipcode in zipcodes:
                writer.writerow(zipcode)
        
        print(f"💾 Saved {len(zipcodes)} ZIP codes to {filename}")
    
    def save_to_json(self, state_name: str, zipcodes: List[Dict]):
        """Save ZIP codes to JSON file for SQL import"""
        if not zipcodes:
            return
        
        # Convert to format expected by import script
        formatted_zipcodes = []
        for zc in zipcodes:
            formatted_zipcodes.append({
                'zip_code': zc['zip_code'],
                'zip_extension': '',  # Not generated in our simple version
                'primary_city': zc['city'],
                'acceptable_cities': '',
                'county': zc['county'],
                'state': zc['state'],
                'latitude': zc.get('latitude', ''),
                'longitude': zc.get('longitude', '')
            })
        
        # Create JSON structure expected by import script
        json_data = {
            'state': state_name,
            'scrape_date': '2025-11-26',
            'total_zipcodes': len(formatted_zipcodes),
            'zipcodes': formatted_zipcodes
        }
        
        # Use timestamp in filename like the import script expects
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{state_name.replace(' ', '_').lower()}_zipcodes_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=2)
        
        print(f"💾 Saved {len(zipcodes)} ZIP codes to {filename} (for SQL import)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python zipcode_generator.py <state_name>")
        print("Example: python zipcode_generator.py California")
        return
    
    generator = ZipCodeGenerator()
    state_name = sys.argv[1]
    
    # Generate ZIP codes
    zipcodes = generator.generate_state_zipcodes(state_name)
    
    if zipcodes:
        # Save to CSV and JSON
        generator.save_to_csv(state_name, zipcodes)
        generator.save_to_json(state_name, zipcodes)
        print(f"\n✅ Generated and saved {len(zipcodes)} ZIP codes for {state_name}")
    else:
        print(f"❌ Failed to generate ZIP codes for {state_name}")

if __name__ == "__main__":
    main()