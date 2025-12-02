#!/usr/bin/env python3
"""
Generic ZIP Code SQL Import Script
Imports ZIP code data from JSON into LocationDataDB for any state
"""

import json
import pyodbc
import glob
import sys
from datetime import datetime

def get_latest_zipcode_file(state_name):
    """Get the latest state ZIP codes JSON file"""
    # Convert spaces to underscores to match scraper filename format
    state_safe = state_name.lower().replace(' ', '_')
    files = glob.glob(f"StateZipCodes/{state_safe}_zipcodes_*.json")
    if not files:
        return None
    return max(files)

def connect_to_database():
    """Connect to LocationDataDB"""
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=.;"
        "Database=LocationDataDB;"
        "Trusted_Connection=yes;"
    )
    try:
        conn = pyodbc.connect(connection_string)
        print("✅ Connected to LocationDataDB")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def get_state_code_mapping():
    """Get state name to code mapping"""
    return {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY'
    }

def validate_state_exists(cursor, state_code):
    """Validate that the state exists in the States table"""
    cursor.execute("SELECT StateCode FROM States WHERE StateCode = ?", state_code)
    if cursor.fetchone():
        return True
    else:
        print(f"❌ State {state_code} not found in States table. Please ensure states are imported first.")
        return False

def import_state_zipcodes(state_name, state_code):
    """Import state ZIP codes from JSON to SQL"""
    
    # Get latest file
    json_file = get_latest_zipcode_file(state_name)
    if not json_file:
        print(f"❌ No {state_name} ZIP codes JSON file found!")
        return False
    
    print(f"📊 Importing from: {json_file}")
    
    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return False
    
    zipcodes = data['zipcodes']
    print(f"📬 Found {len(zipcodes)} ZIP codes to import")
    
    # Connect to database
    conn = connect_to_database()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Validate state exists
        if not validate_state_exists(cursor, state_code):
            return False
        
        # Track statistics
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        print(f"\n🏗️ Starting {state_name} ZIP codes import process...")
        
        for i, zipcode in enumerate(zipcodes, 1):
            try:
                # Extract ZIP code data
                zip_code = zipcode.get('zip_code', '').strip()
                if not zip_code or len(zip_code) != 5:
                    continue
                
                zip_extension = zipcode.get('zip_extension', '').strip() or None
                if zip_extension and len(zip_extension) != 4:
                    zip_extension = None
                
                primary_city = zipcode.get('primary_city', '').strip() or 'Unknown'
                acceptable_cities = zipcode.get('acceptable_cities', '').strip() or None
                county = zipcode.get('county', '').strip() or None
                
                # Parse coordinates
                latitude = zipcode.get('latitude')
                longitude = zipcode.get('longitude')
                
                # Validate coordinates
                if latitude is not None:
                    try:
                        latitude = float(latitude)
                        if not (-90 <= latitude <= 90):
                            latitude = None
                    except (ValueError, TypeError):
                        latitude = None
                
                if longitude is not None:
                    try:
                        longitude = float(longitude)
                        if not (-180 <= longitude <= 180):
                            longitude = None
                    except (ValueError, TypeError):
                        longitude = None
                
                # Check if ZIP code already exists
                cursor.execute("""
                    SELECT ZipcodeId FROM Zipcodes 
                    WHERE StateCode = ? AND ZipCode = ?
                """, state_code, zip_code)
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing ZIP code
                    cursor.execute("""
                        UPDATE Zipcodes 
                        SET ZipCodeExtension = ?, PrimaryCity = ?, AcceptableCities = ?,
                            County = ?, Latitude = ?, Longitude = ?, ModifiedDate = GETUTCDATE()
                        WHERE StateCode = ? AND ZipCode = ?
                    """, zip_extension, primary_city, acceptable_cities, county, 
                        latitude, longitude, state_code, zip_code)
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"  📝 Updated {updated_count} ZIP codes...")
                else:
                    # Insert new ZIP code
                    cursor.execute("""
                        INSERT INTO Zipcodes (StateCode, ZipCode, ZipCodeExtension, PrimaryCity,
                                            AcceptableCities, County, Latitude, Longitude, 
                                            IsActive, CreatedDate, ModifiedDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, GETUTCDATE(), GETUTCDATE())
                    """, state_code, zip_code, zip_extension, primary_city, acceptable_cities,
                        county, latitude, longitude)
                    imported_count += 1
                    if imported_count % 100 == 0:
                        print(f"  ✅ Imported {imported_count} ZIP codes...")
                
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Only show first 5 errors
                    print(f"  ⚠️ Error importing ZIP {zip_code}: {e}")
        
        # Commit changes
        conn.commit()
        
        # Print summary
        print(f"\n📊 {state_name.upper()} ZIP CODES IMPORT SUMMARY")
        print("=" * 50)
        print(f"✅ New ZIP codes imported: {imported_count}")
        print(f"📝 Existing ZIP codes updated: {updated_count}")
        print(f"❌ Errors encountered: {error_count}")
        print(f"📁 Source file: {json_file}")
        print(f"📬 Total {state_name} ZIP codes in database: {imported_count + updated_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        conn.rollback()
        return False
        
    finally:
        print("🔌 Database connection closed")
        conn.close()

def main():
    """Main function"""
    # Can be run with state name as argument
    if len(sys.argv) > 1:
        state_name = sys.argv[1].title()
        
        # Get state code mapping
        state_mapping = get_state_code_mapping()
        state_code = state_mapping.get(state_name.lower())
        
        if not state_code:
            print(f"❌ Unknown state: {state_name}")
            print("Available states:", ', '.join(state_mapping.keys()))
            return False
    else:
        print("❌ Please provide a state name")
        print("Usage: python import_zipcodes_to_sql.py \"State Name\"")
        print("Example: python import_zipcodes_to_sql.py \"California\"")
        return False
    
    print(f"🏛️ {state_name.upper()} ZIP CODES SQL IMPORT")
    print("=" * 50)
    
    success = import_state_zipcodes(state_name, state_code)
    if success:
        print(f"\n🎉 {state_name} ZIP codes import completed successfully!")
        return True
    else:
        print(f"\n💥 {state_name} ZIP codes import failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)