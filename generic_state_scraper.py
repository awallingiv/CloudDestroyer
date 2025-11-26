"""
Enhanced State Municipalities Wikipedia Scraper
Generic version that can scrape municipality data from different states
"""
import sys
import os
import json
import time
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.core.cloud_destroyer import CloudDestroyer
    CLOUDDESTROYER_AVAILABLE = True
except ImportError:
    print("⚠️ CloudDestroyer not available, falling back to requests")
    import requests
    CLOUDDESTROYER_AVAILABLE = False

@dataclass
class Municipality:
    """Data structure for municipality"""
    rank: Optional[int] = None
    name: str = ""
    designation: str = ""
    primary_county: str = ""
    secondary_counties: List[str] = None
    population: Optional[int] = None
    area_sq_mi: Optional[float] = None
    incorporated: Optional[str] = None
    notes: str = ""

class StateMunicipalitiesScraper:
    """Enhanced scraper for state municipalities from Wikipedia"""
    
    def __init__(self, state_name: str, wikipedia_url: str):
        self.state_name = state_name
        self.base_url = wikipedia_url
        self.municipalities = []
        
        # Initialize scraper
        if CLOUDDESTROYER_AVAILABLE:
            print("🚀 Using CloudDestroyer for enhanced scraping")
            self.destroyer = CloudDestroyer()
        else:
            print("📡 Using basic requests for scraping")
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
    
    def fetch_page(self) -> str:
        """Fetch the Wikipedia page content"""
        print(f"📡 Fetching: {self.base_url}")
        
        try:
            if CLOUDDESTROYER_AVAILABLE:
                response = self.destroyer.get(self.base_url)
                if response.status_code == 200:
                    print(f"✅ CloudDestroyer success: {len(response.text):,} characters")
                    return response.text
                else:
                    print(f"❌ CloudDestroyer failed: {response.status_code}")
                    return None
            else:
                response = self.session.get(self.base_url, timeout=30)
                response.raise_for_status()
                print(f"✅ Requests success: {len(response.text):,} characters")
                return response.text
                
        except Exception as e:
            print(f"❌ Failed to fetch page: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean text from HTML artifacts"""
        if not text:
            return ""
        
        # Remove references like [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def parse_population(self, pop_text: str) -> Optional[int]:
        """Parse population from text"""
        if not pop_text:
            return None
        
        # Remove everything except digits and commas
        pop_clean = re.sub(r'[^\d,]', '', pop_text)
        pop_clean = pop_clean.replace(',', '')
        
        try:
            return int(pop_clean) if pop_clean else None
        except ValueError:
            return None
    
    def parse_area(self, area_text: str) -> Optional[float]:
        """Parse area from text"""
        if not area_text:
            return None
        
        # Look for numbers followed by sq mi or similar
        area_match = re.search(r'([\d,.]+)\s*(?:sq\s*mi|square\s*miles?)', area_text, re.IGNORECASE)
        if area_match:
            try:
                return float(area_match.group(1).replace(',', ''))
            except ValueError:
                pass
        
        return None
    
    def parse_counties(self, county_text: str) -> tuple[str, List[str]]:
        """Parse primary and secondary counties"""
        if not county_text:
            return "", []
        
        county_text = self.clean_text(county_text)
        
        # Split on common delimiters
        counties = re.split(r'[,;/]', county_text)
        counties = [c.strip() for c in counties if c.strip()]
        
        primary = counties[0] if counties else ""
        secondary = counties[1:] if len(counties) > 1 else []
        
        return primary, secondary
    
    def find_municipalities_table(self, soup: BeautifulSoup) -> Optional[Any]:
        """Find the main municipalities table"""
        print("🔍 Looking for municipalities table...")
        
        # Look for tables with municipality data
        tables = soup.find_all('table', class_='wikitable')
        
        for table in tables:
            # Check if this table has the expected headers
            header_row = table.find('tr')
            if header_row:
                header_text = header_row.get_text().lower()
                # Look for key indicators
                indicators = ['municipality', 'city', 'town', 'population', 'county', 'incorporated']
                if any(indicator in header_text for indicator in indicators):
                    # Count how many indicators match
                    matches = sum(1 for indicator in indicators if indicator in header_text)
                    if matches >= 2:  # Need at least 2 matching indicators
                        print(f"✅ Found municipalities table with {matches} indicators")
                        return table
        
        # Fallback: look for large tables
        large_tables = [t for t in tables if len(t.find_all('tr')) > 50]
        if large_tables:
            print("✅ Using largest table as fallback")
            return max(large_tables, key=lambda t: len(t.find_all('tr')))
        
        return None
    
    def extract_municipalities_from_table(self, soup: BeautifulSoup) -> List[Municipality]:
        """Extract municipalities from Wikipedia table"""
        municipalities = []
        
        main_table = self.find_municipalities_table(soup)
        
        if not main_table:
            print("❌ Could not find municipalities table")
            return []
        
        # Parse table headers to understand column structure
        header_row = main_table.find('tr')
        headers = []
        for th in header_row.find_all(['th', 'td']):
            headers.append(self.clean_text(th.get_text()).lower())
        
        print(f"📝 Table headers: {headers}")
        
        # Map column indices with flexible matching
        col_map = {}
        for i, header in enumerate(headers):
            header_lower = header.lower()
            
            # Rank/Number
            if any(word in header_lower for word in ['rank', '#', 'no.', 'number']):
                col_map['rank'] = i
            
            # Municipality name
            elif any(word in header_lower for word in ['municipality', 'city', 'town', 'name', 'place']):
                if 'name' not in col_map:  # Use first match
                    col_map['name'] = i
            
            # Type/Designation
            elif any(word in header_lower for word in ['type', 'designation', 'classification']):
                col_map['designation'] = i
            
            # County
            elif 'county' in header_lower:
                if 'primary' in header_lower or 'main' in header_lower or not col_map.get('primary_county'):
                    col_map['primary_county'] = i
                elif 'secondary' in header_lower or 'additional' in header_lower:
                    col_map['secondary_county'] = i
            
                # Population (prefer 2020 census, avoid density)
                elif 'population' in header_lower:
                    if 'density' not in header_lower:  # Avoid population density
                        if '2020' in header_lower:
                            col_map['population'] = i
                        elif 'population' == header_lower.strip():
                            col_map['population'] = i
                        elif not col_map.get('population'):  # Fallback to first population column
                            col_map['population'] = i            # Area
            elif any(word in header_lower for word in ['area', 'sq', 'square']):
                col_map['area'] = i
            
            # Incorporated date
            elif any(word in header_lower for word in ['incorporated', 'founded', 'established']):
                col_map['incorporated'] = i
        
        # Manual fix for California - force population column
        if 'population (2020)' in [h.lower() for h in headers]:
            for i, h in enumerate(headers):
                if 'population (2020)' in h.lower():
                    col_map['population'] = i
                    break
        
        print(f"🗺️ Column mapping: {col_map}")
        
        # Process data rows
        rows = main_table.find_all('tr')[1:]  # Skip header
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            
            if len(cells) < 2:
                continue
            
            try:
                municipality = Municipality()
                
                # Extract data based on column mapping
                
                # Rank
                if 'rank' in col_map and col_map['rank'] < len(cells):
                    rank_text = self.clean_text(cells[col_map['rank']].get_text())
                    try:
                        municipality.rank = int(rank_text) if rank_text.isdigit() else None
                    except ValueError:
                        municipality.rank = None
                
                # Name (required)
                if 'name' in col_map and col_map['name'] < len(cells):
                    municipality.name = self.clean_text(cells[col_map['name']].get_text())
                else:
                    # Fallback: use first non-numeric cell as name
                    for cell in cells:
                        text = self.clean_text(cell.get_text())
                        if text and not text.isdigit() and len(text) > 1:
                            municipality.name = text
                            break
                
                # Skip if no valid name
                if not municipality.name or len(municipality.name) < 2:
                    continue
                
                # Designation
                if 'designation' in col_map and col_map['designation'] < len(cells):
                    municipality.designation = self.clean_text(cells[col_map['designation']].get_text())
                
                # Primary County
                if 'primary_county' in col_map and col_map['primary_county'] < len(cells):
                    primary, secondary = self.parse_counties(cells[col_map['primary_county']].get_text())
                    municipality.primary_county = primary
                    municipality.secondary_counties = secondary
                
                # Secondary Counties
                if 'secondary_county' in col_map and col_map['secondary_county'] < len(cells):
                    _, additional_secondary = self.parse_counties(cells[col_map['secondary_county']].get_text())
                    if municipality.secondary_counties is None:
                        municipality.secondary_counties = additional_secondary
                    else:
                        municipality.secondary_counties.extend(additional_secondary)
                
                # Population
                if 'population' in col_map and col_map['population'] < len(cells):
                    pop_text = cells[col_map['population']].get_text()
                    municipality.population = self.parse_population(pop_text)
                
                # Area
                if 'area' in col_map and col_map['area'] < len(cells):
                    area_text = cells[col_map['area']].get_text()
                    municipality.area_sq_mi = self.parse_area(area_text)
                
                # Incorporated date
                if 'incorporated' in col_map and col_map['incorporated'] < len(cells):
                    municipality.incorporated = self.clean_text(cells[col_map['incorporated']].get_text())
                
                # Only add if we have a valid name
                if municipality.name and len(municipality.name) > 1:
                    municipalities.append(municipality)
                
            except Exception as e:
                print(f"⚠️ Error parsing row {row_idx}: {e}")
                continue
        
        print(f"✅ Successfully parsed {len(municipalities)} municipalities")
        return municipalities
    
    def scrape_municipalities(self) -> List[Dict[str, Any]]:
        """Main scraping method"""
        start_time = time.time()
        
        print(f"🏛️ {self.state_name} Municipalities Wikipedia Scraper")
        print("=" * 60)
        
        # Fetch the page
        html_content = self.fetch_page()
        if not html_content:
            return []
        
        # Parse with BeautifulSoup
        print("🔍 Parsing HTML content...")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract municipalities from main table
        municipalities = self.extract_municipalities_from_table(soup)
        
        if not municipalities:
            print("❌ No municipalities extracted")
            return []
        
        # Generate statistics
        total_count = len(municipalities)
        with_population = sum(1 for m in municipalities if m.population)
        with_counties = sum(1 for m in municipalities if m.primary_county)
        unique_counties = set(m.primary_county for m in municipalities if m.primary_county)
        
        processing_time = time.time() - start_time
        
        print(f"\n📊 SCRAPING SUMMARY")
        print("=" * 40)
        print(f"🏙️ Total municipalities: {total_count:,}")
        print(f"👥 With population data: {with_population:,}")
        print(f"🗺️ With county data: {with_counties:,}")
        print(f"📍 Unique counties: {len(unique_counties):,}")
        print(f"⏱️ Processing time: {processing_time:.1f} seconds")
        
        # Convert to dictionary format
        municipalities_dict = []
        for muni in municipalities:
            muni_dict = {
                'rank': muni.rank,
                'name': muni.name,
                'designation': muni.designation,
                'primary_county': muni.primary_county,
                'secondary_counties': muni.secondary_counties or [],
                'population': muni.population,
                'area_sq_mi': muni.area_sq_mi,
                'incorporated': muni.incorporated
            }
            # Remove None/empty values
            muni_dict = {k: v for k, v in muni_dict.items() if v is not None and v != "" and v != []}
            municipalities_dict.append(muni_dict)
        
        return municipalities_dict
    
    def save_to_json(self, municipalities: List[Dict], filename: str = None):
        """Save municipalities data to JSON file"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            state_safe = self.state_name.lower().replace(' ', '_')
            filename = f"StateJsons/{state_safe}_municipalities_{timestamp}.json"
        
        # Calculate statistics
        total_count = len(municipalities)
        with_population = sum(1 for m in municipalities if m.get('population'))
        with_counties = sum(1 for m in municipalities if m.get('primary_county'))
        
        # Get unique counties
        unique_counties = set()
        for m in municipalities:
            if m.get('primary_county'):
                unique_counties.add(m['primary_county'])
            for county in m.get('secondary_counties', []):
                unique_counties.add(county)
        
        # Population statistics
        populations = [m['population'] for m in municipalities if m.get('population')]
        pop_stats = {}
        if populations:
            pop_stats = {
                'min': min(populations),
                'max': max(populations),
                'average': sum(populations) // len(populations),
                'total': sum(populations)
            }
        
        # Create comprehensive JSON structure
        output_data = {
            'metadata': {
                'state': self.state_name,
                'source': self.base_url,
                'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'scraper_version': '2.0_generic',
                'description': f'{self.state_name} municipalities scraped from Wikipedia',
                'total_municipalities': total_count,
                'statistics': {
                    'total_found': total_count,
                    'with_population': with_population,
                    'with_counties': with_counties,
                    'unique_counties': len(unique_counties),
                    'population_stats': pop_stats
                },
                'counties': sorted(list(unique_counties))
            },
            'municipalities': municipalities
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Data saved to: {filename}")
            print(f"📁 File size: {os.path.getsize(filename):,} bytes")
            return filename
            
        except Exception as e:
            print(f"❌ Failed to save JSON: {e}")
            return None

def scrape_state(state_name: str, url: str):
    """Scrape municipalities for a specific state"""
    
    print(f"🏛️ {state_name} Municipalities Wikipedia Scraper")
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Create scraper
    scraper = StateMunicipalitiesScraper(state_name, url)
    
    # Scrape municipalities
    municipalities = scraper.scrape_municipalities()
    
    if municipalities:
        # Save to JSON
        json_file = scraper.save_to_json(municipalities)
        
        # Show sample data
        print(f"\n🔍 SAMPLE DATA (first 10 municipalities):")
        print("-" * 60)
        for i, muni in enumerate(municipalities[:10]):
            name = muni.get('name', 'Unknown')
            county = muni.get('primary_county', 'Unknown County')
            population = muni.get('population')
            
            print(f"{i+1:2d}. {name:<25}")
            if county:
                print(f"     County: {county}")
            if population:
                print(f"     Population: {population:,}")
            print()
        
        # Show largest cities
        if municipalities:
            with_pop = [m for m in municipalities if m.get('population')]
            if with_pop:
                largest = sorted(with_pop, key=lambda x: x['population'], reverse=True)[:10]
                
                print(f"\n🏆 TOP 10 LARGEST CITIES:")
                print("-" * 50)
                for i, city in enumerate(largest):
                    print(f"{i+1:2d}. {city['name']:<25} {city['population']:,}")
        
        print(f"\n🎉 SUCCESS!")
        print(f"✅ Scraper extracted {len(municipalities):,} {state_name} municipalities")
        if json_file:
            print(f"✅ Data saved to: {json_file}")
    
    else:
        print("❌ No municipalities were scraped")
    
    print(f"\n⏰ Completed at: {time.strftime('%H:%M:%S')}")
    return municipalities

if __name__ == "__main__":
    # Can be run directly or imported
    import sys
    
    if len(sys.argv) > 2:
        state_name = sys.argv[1]
        url = sys.argv[2]
        scrape_state(state_name, url)
    else:
        print("Usage: python generic_state_scraper.py 'State Name' 'Wikipedia URL'")