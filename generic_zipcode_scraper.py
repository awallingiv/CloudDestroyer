#!/usr/bin/env python3
"""
Generic ZIP Code Wikipedia Scraper
Scrapes ZIP code data from Wikipedia for any state
"""

import sys
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

# Add the src directory to the path to import CloudDestroyer
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from core.cloud_destroyer import CloudDestroyer
except ImportError:
    print("❌ Error: CloudDestroyer not found. Make sure the src directory exists.")
    sys.exit(1)

class StateZipCodeScraper:
    def __init__(self, state_name, wikipedia_url):
        self.state_name = state_name
        self.wikipedia_url = wikipedia_url
        self.cloud_destroyer = CloudDestroyer()
        self.zip_codes = []
        
    def fetch_page(self):
        """Fetch the Wikipedia page using CloudDestroyer"""
        print(f"🏛️ {self.state_name} ZIP Codes Wikipedia Scraper")
        print("=" * 60)
        print(f"📡 Fetching: {self.wikipedia_url}")
        
        try:
            response = self.cloud_destroyer.get(self.wikipedia_url)
            if response and response.text:
                print(f"✅ CloudDestroyer success: {len(response.text):,} characters")
                return response.text
            else:
                print("❌ CloudDestroyer failed to fetch content")
                return None
        except Exception as e:
            print(f"❌ Error fetching page: {e}")
            return None
    
    def parse_zip_codes(self, html_content):
        """Parse ZIP codes from HTML content"""
        print("🔍 Parsing HTML content...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for tables that might contain ZIP code data
        tables = soup.find_all('table', class_=['wikitable', 'sortable'])
        
        if not tables:
            print("❌ No tables found with ZIP code data")
            return False
            
        print(f"🔍 Found {len(tables)} potential ZIP code tables")
        
        # Try each table to find ZIP code data
        best_table = None
        best_score = 0
        
        for i, table in enumerate(tables):
            score = self._score_zip_table(table)
            print(f"📊 Table {i+1} ZIP code indicators: {score}")
            
            if score > best_score:
                best_score = score
                best_table = table
        
        if not best_table or best_score < 2:
            print("❌ No suitable ZIP code table found")
            return False
            
        print(f"✅ Using table with {best_score} ZIP code indicators")
        
        # Parse the selected table
        return self._parse_zip_table(best_table)
    
    def _score_zip_table(self, table):
        """Score a table based on how likely it contains ZIP code data"""
        score = 0
        table_text = table.get_text().lower()
        
        # Look for ZIP code indicators
        zip_indicators = [
            'zip code', 'zipcode', 'postal code', 'zip',
            'city', 'county', 'latitude', 'longitude',
            '00000', '99999'  # ZIP code patterns
        ]
        
        for indicator in zip_indicators:
            if indicator in table_text:
                score += 1
        
        # Check for numeric patterns that look like ZIP codes
        zip_pattern = re.compile(r'\b\d{5}\b')
        zip_matches = zip_pattern.findall(table_text)
        if len(zip_matches) >= 5:  # At least 5 ZIP codes
            score += 2
            
        return score
    
    def _parse_zip_table(self, table):
        """Parse ZIP codes from a table"""
        rows = table.find_all('tr')
        
        if len(rows) < 2:
            print("❌ Table has insufficient rows")
            return False
            
        # Get headers
        header_row = rows[0]
        headers = [th.get_text().strip().lower() for th in header_row.find_all(['th', 'td'])]
        
        print(f"📝 Table headers: {headers}")
        
        # Map column indices
        column_mapping = self._map_zip_columns(headers)
        print(f"🗺️ Column mapping: {column_mapping}")
        
        if not column_mapping.get('zip_code'):
            print("❌ Could not find ZIP code column")
            return False
        
        # Parse data rows
        parsed_count = 0
        
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < len(headers):
                continue
                
            zip_data = self._extract_zip_data(cells, column_mapping)
            if zip_data:
                self.zip_codes.append(zip_data)
                parsed_count += 1
        
        print(f"✅ Successfully parsed {parsed_count} ZIP codes")
        return True
    
    def _map_zip_columns(self, headers):
        """Map header names to column indices"""
        mapping = {}
        
        for i, header in enumerate(headers):
            header_clean = header.lower().strip()
            
            # ZIP code column
            if any(term in header_clean for term in ['zip code', 'zipcode', 'postal code', 'zip']):
                mapping['zip_code'] = i
            
            # City column
            elif any(term in header_clean for term in ['city', 'place', 'location', 'town']):
                mapping['primary_city'] = i
            
            # County column
            elif any(term in header_clean for term in ['county', 'parish']):
                mapping['county'] = i
            
            # Latitude column
            elif any(term in header_clean for term in ['latitude', 'lat']):
                mapping['latitude'] = i
            
            # Longitude column
            elif any(term in header_clean for term in ['longitude', 'lon', 'lng']):
                mapping['longitude'] = i
            
            # Acceptable cities column
            elif any(term in header_clean for term in ['acceptable', 'alternate', 'other']):
                mapping['acceptable_cities'] = i
        
        return mapping
    
    def _extract_zip_data(self, cells, column_mapping):
        """Extract ZIP code data from table cells"""
        try:
            # Get ZIP code
            zip_code_idx = column_mapping.get('zip_code')
            if zip_code_idx is None or zip_code_idx >= len(cells):
                return None
                
            zip_text = cells[zip_code_idx].get_text().strip()
            
            # Extract 5-digit ZIP code
            zip_match = re.search(r'\b(\d{5})\b', zip_text)
            if not zip_match:
                return None
                
            zip_code = zip_match.group(1)
            
            # Extract ZIP+4 extension if present
            extension_match = re.search(r'\b\d{5}-(\d{4})\b', zip_text)
            zip_extension = extension_match.group(1) if extension_match else None
            
            # Get other fields
            zip_data = {
                'zip_code': zip_code,
                'zip_extension': zip_extension,
                'primary_city': self._get_cell_text(cells, column_mapping.get('primary_city')),
                'county': self._get_cell_text(cells, column_mapping.get('county')),
                'acceptable_cities': self._get_cell_text(cells, column_mapping.get('acceptable_cities')),
                'latitude': self._get_coordinate(cells, column_mapping.get('latitude')),
                'longitude': self._get_coordinate(cells, column_mapping.get('longitude'))
            }
            
            # Clean up city name
            if zip_data['primary_city']:
                zip_data['primary_city'] = re.sub(r'[†‡*]', '', zip_data['primary_city']).strip()
            
            return zip_data
            
        except Exception as e:
            print(f"⚠️ Error parsing ZIP data: {e}")
            return None
    
    def _get_cell_text(self, cells, column_idx):
        """Safely get text from a cell"""
        if column_idx is None or column_idx >= len(cells):
            return None
        return cells[column_idx].get_text().strip() or None
    
    def _get_coordinate(self, cells, column_idx):
        """Extract coordinate value from cell"""
        text = self._get_cell_text(cells, column_idx)
        if not text:
            return None
            
        # Look for decimal coordinate
        coord_match = re.search(r'(-?\d+\.?\d*)', text)
        if coord_match:
            try:
                return float(coord_match.group(1))
            except ValueError:
                pass
        return None
    
    def save_to_json(self):
        """Save ZIP codes to JSON file"""
        if not self.zip_codes:
            print("❌ No ZIP codes to save")
            return None
            
        # Create StateZipCodes directory if it doesn't exist
        output_dir = Path("StateZipCodes")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        state_safe = self.state_name.lower().replace(' ', '_')
        filename = f"{state_safe}_zipcodes_{timestamp}.json"
        filepath = output_dir / filename
        
        # Prepare data
        output_data = {
            "metadata": {
                "state": self.state_name,
                "source": self.wikipedia_url,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "scraper_version": "1.0_zipcode_generic",
                "description": f"{self.state_name} ZIP codes scraped from Wikipedia",
                "total_zipcodes": len(self.zip_codes),
                "statistics": {
                    "total_found": len(self.zip_codes),
                    "with_coordinates": sum(1 for zc in self.zip_codes if zc.get('latitude') and zc.get('longitude')),
                    "with_counties": sum(1 for zc in self.zip_codes if zc.get('county')),
                    "with_extensions": sum(1 for zc in self.zip_codes if zc.get('zip_extension'))
                }
            },
            "zipcodes": self.zip_codes
        }
        
        # Save file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Data saved to: {filepath}")
            print(f"📁 File size: {filepath.stat().st_size:,} bytes")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return None
    
    def print_summary(self):
        """Print scraping summary"""
        print(f"\n📊 SCRAPING SUMMARY")
        print("=" * 40)
        print(f"🏛️ State: {self.state_name}")
        print(f"📬 Total ZIP codes: {len(self.zip_codes)}")
        
        if self.zip_codes:
            with_coords = sum(1 for zc in self.zip_codes if zc.get('latitude') and zc.get('longitude'))
            with_counties = sum(1 for zc in self.zip_codes if zc.get('county'))
            with_extensions = sum(1 for zc in self.zip_codes if zc.get('zip_extension'))
            
            print(f"🗺️ With coordinates: {with_coords}")
            print(f"🏛️ With counties: {with_counties}")
            print(f"📮 With ZIP+4 extensions: {with_extensions}")
            
            # Show sample data
            print(f"\n🔍 SAMPLE DATA (first 10 ZIP codes):")
            print("-" * 60)
            for i, zc in enumerate(self.zip_codes[:10], 1):
                city = zc.get('primary_city', 'Unknown')
                county = zc.get('county', 'Unknown')
                coords = ""
                if zc.get('latitude') and zc.get('longitude'):
                    coords = f" ({zc['latitude']}, {zc['longitude']})"
                
                print(f"{i:2d}. {zc['zip_code']} - {city}")
                print(f"     County: {county}{coords}")
    
    def run(self):
        """Main scraping process"""
        start_time = datetime.now()
        print(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Fetch page content
        html_content = self.fetch_page()
        if not html_content:
            print(f"\n💥 Failed to fetch {self.state_name} ZIP codes!")
            return False
        
        # Parse ZIP codes
        if not self.parse_zip_codes(html_content):
            print(f"\n💥 Failed to parse {self.state_name} ZIP codes!")
            return False
        
        # Save results
        output_file = self.save_to_json()
        if not output_file:
            print(f"\n💥 Failed to save {self.state_name} ZIP codes!")
            return False
        
        # Print summary
        self.print_summary()
        
        # Final success message
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n🎉 SUCCESS!")
        print(f"✅ Scraper extracted {len(self.zip_codes)} {self.state_name} ZIP codes")
        print(f"✅ Data saved to: {output_file}")
        print(f"⏱️ Processing time: {duration:.1f} seconds")
        print(f"⏰ Completed at: {end_time.strftime('%H:%M:%S')}")
        
        return True

def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("Usage: python generic_zipcode_scraper.py \"State Name\" \"Wikipedia_URL\"")
        print("\nExample:")
        print("python generic_zipcode_scraper.py \"California\" \"https://en.wikipedia.org/wiki/List_of_ZIP_codes_in_California\"")
        sys.exit(1)
    
    state_name = sys.argv[1]
    wikipedia_url = sys.argv[2]
    
    print("🚀 Using CloudDestroyer for enhanced scraping")
    
    scraper = StateZipCodeScraper(state_name, wikipedia_url)
    success = scraper.run()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()