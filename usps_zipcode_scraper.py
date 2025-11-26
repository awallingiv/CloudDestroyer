"""
USPS ZIP Code Scraper using CloudDestroyer
Scrapes ZIP code data from USPS or other reliable sources
"""
import sys
import os
import json
import csv
from pathlib import Path
import time
import re
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.cloud_destroyer import CloudDestroyer

class USPSZipCodeScraper:
    def __init__(self):
        self.destroyer = CloudDestroyer()
        self.output_dir = Path("StateZipCodes")
        self.output_dir.mkdir(exist_ok=True)
        
    def scrape_state_zipcodes(self, state_name: str, state_abbrev: str) -> List[Dict]:
        """
        Scrape ZIP codes for a state using multiple sources
        """
        print(f"\n🏛️  Scraping ZIP codes for {state_name} ({state_abbrev})")
        
        zipcodes = []
        
        # Try multiple sources
        sources = [
            self._try_zipcode_org(state_name, state_abbrev),
            self._try_usps_com(state_name, state_abbrev),
            self._try_zipinfo_com(state_name, state_abbrev)
        ]
        
        for source_data in sources:
            if source_data:
                zipcodes.extend(source_data)
                break  # Use first successful source
                
        # Remove duplicates
        unique_zipcodes = {}
        for zc in zipcodes:
            zip_code = zc.get('zip_code', '').strip()
            if zip_code and zip_code not in unique_zipcodes:
                unique_zipcodes[zip_code] = zc
                
        final_zipcodes = list(unique_zipcodes.values())
        print(f"✅ Found {len(final_zipcodes)} ZIP codes for {state_name}")
        
        # Save to CSV
        self._save_to_csv(state_name, final_zipcodes)
        
        return final_zipcodes
    
    def _try_zipcode_org(self, state_name: str, state_abbrev: str) -> List[Dict]:
        """Try zipcode.org"""
        try:
            # Convert state name to lowercase with dashes
            state_url = state_name.lower().replace(' ', '-')
            url = f"https://www.zipcode.org/{state_url}"
            
            print(f"📡 Trying zipcode.org: {url}")
            response = self.destroyer.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._parse_zipcode_org(soup, state_name)
            else:
                print(f"❌ zipcode.org returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ zipcode.org failed: {e}")
            
        return []
    
    def _try_usps_com(self, state_name: str, state_abbrev: str) -> List[Dict]:
        """Try USPS.com"""
        try:
            # USPS ZIP lookup by state
            url = f"https://tools.usps.com/zip-code-lookup.htm?bystate"
            
            print(f"📡 Trying USPS.com: {url}")
            response = self.destroyer.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._parse_usps_com(soup, state_abbrev)
            else:
                print(f"❌ USPS.com returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ USPS.com failed: {e}")
            
        return []
    
    def _try_zipinfo_com(self, state_name: str, state_abbrev: str) -> List[Dict]:
        """Try zipinfo.com"""
        try:
            # Convert to proper format
            state_url = state_name.lower().replace(' ', '-')
            url = f"https://zipinfo.com/state/{state_url}/"
            
            print(f"📡 Trying zipinfo.com: {url}")
            response = self.destroyer.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._parse_zipinfo_com(soup, state_name)
            else:
                print(f"❌ zipinfo.com returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ zipinfo.com failed: {e}")
            
        return []
    
    def _parse_zipcode_org(self, soup: BeautifulSoup, state_name: str) -> List[Dict]:
        """Parse ZIP codes from zipcode.org"""
        zipcodes = []
        
        # Look for ZIP code links or tables
        zip_links = soup.find_all('a', href=re.compile(r'/\d{5}'))
        for link in zip_links:
            zip_code = re.search(r'/(\d{5})', link.get('href'))
            if zip_code:
                zipcodes.append({
                    'zip_code': zip_code.group(1),
                    'city': link.get_text(strip=True),
                    'state': state_name,
                    'county': '',
                    'latitude': '',
                    'longitude': ''
                })
        
        # Also look for tables with ZIP codes
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    zip_text = cols[0].get_text(strip=True)
                    city_text = cols[1].get_text(strip=True)
                    
                    if re.match(r'^\d{5}$', zip_text):
                        zipcodes.append({
                            'zip_code': zip_text,
                            'city': city_text,
                            'state': state_name,
                            'county': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                            'latitude': '',
                            'longitude': ''
                        })
        
        return zipcodes
    
    def _parse_usps_com(self, soup: BeautifulSoup, state_abbrev: str) -> List[Dict]:
        """Parse ZIP codes from USPS.com"""
        zipcodes = []
        
        # USPS typically has different structure - adapt as needed
        # This is a placeholder for USPS-specific parsing
        
        return zipcodes
    
    def _parse_zipinfo_com(self, soup: BeautifulSoup, state_name: str) -> List[Dict]:
        """Parse ZIP codes from zipinfo.com"""
        zipcodes = []
        
        # Look for ZIP code patterns in the content
        zip_pattern = re.compile(r'\b\d{5}\b')
        text = soup.get_text()
        
        found_zips = set(zip_pattern.findall(text))
        for zip_code in found_zips:
            zipcodes.append({
                'zip_code': zip_code,
                'city': '',
                'state': state_name,
                'county': '',
                'latitude': '',
                'longitude': ''
            })
        
        return zipcodes
    
    def _save_to_csv(self, state_name: str, zipcodes: List[Dict]):
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

# State data for testing
US_STATES = [
    ('Alabama', 'AL'),
    ('Alaska', 'AK'),
    ('Arizona', 'AZ'),
    ('Arkansas', 'AR'),
    ('California', 'CA'),
    ('Colorado', 'CO'),
    ('Connecticut', 'CT'),
    ('Delaware', 'DE'),
    ('Florida', 'FL'),
    ('Georgia', 'GA'),
    ('Hawaii', 'HI'),
    ('Idaho', 'ID'),
    ('Illinois', 'IL'),
    ('Indiana', 'IN'),
    ('Iowa', 'IA'),
    ('Kansas', 'KS'),
    ('Kentucky', 'KY'),
    ('Louisiana', 'LA'),
    ('Maine', 'ME'),
    ('Maryland', 'MD'),
    ('Massachusetts', 'MA'),
    ('Michigan', 'MI'),
    ('Minnesota', 'MN'),
    ('Mississippi', 'MS'),
    ('Missouri', 'MO'),
    ('Montana', 'MT'),
    ('Nebraska', 'NE'),
    ('Nevada', 'NV'),
    ('New Hampshire', 'NH'),
    ('New Jersey', 'NJ'),
    ('New Mexico', 'NM'),
    ('New York', 'NY'),
    ('North Carolina', 'NC'),
    ('North Dakota', 'ND'),
    ('Ohio', 'OH'),
    ('Oklahoma', 'OK'),
    ('Oregon', 'OR'),
    ('Pennsylvania', 'PA'),
    ('Rhode Island', 'RI'),
    ('South Carolina', 'SC'),
    ('South Dakota', 'SD'),
    ('Tennessee', 'TN'),
    ('Texas', 'TX'),
    ('Utah', 'UT'),
    ('Vermont', 'VT'),
    ('Virginia', 'VA'),
    ('Washington', 'WA'),
    ('West Virginia', 'WV'),
    ('Wisconsin', 'WI'),
    ('Wyoming', 'WY')
]

def main():
    if len(sys.argv) < 2:
        print("Usage: python usps_zipcode_scraper.py <state_name>")
        print("Example: python usps_zipcode_scraper.py California")
        print("Or: python usps_zipcode_scraper.py all")
        return
    
    scraper = USPSZipCodeScraper()
    
    if sys.argv[1].lower() == 'all':
        # Scrape all states
        print("🚀 Starting ZIP code collection for all 50 states...")
        total_zipcodes = 0
        
        for state_name, state_abbrev in US_STATES:
            try:
                zipcodes = scraper.scrape_state_zipcodes(state_name, state_abbrev)
                total_zipcodes += len(zipcodes)
                time.sleep(2)  # Be respectful to servers
                
            except Exception as e:
                print(f"❌ Failed to scrape {state_name}: {e}")
                continue
        
        print(f"\n🎉 Total ZIP codes collected: {total_zipcodes}")
        
    else:
        # Single state
        state_name = sys.argv[1]
        state_abbrev = ''
        
        # Find state abbreviation
        for name, abbrev in US_STATES:
            if name.lower() == state_name.lower():
                state_abbrev = abbrev
                break
        
        if not state_abbrev:
            print(f"❌ Unknown state: {state_name}")
            return
            
        zipcodes = scraper.scrape_state_zipcodes(state_name, state_abbrev)
        print(f"\n✅ Collected {len(zipcodes)} ZIP codes for {state_name}")

if __name__ == "__main__":
    main()