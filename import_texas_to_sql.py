#!/usr/bin/env python3
"""
Texas Municipalities SQL Import Script
Imports Texas municipality data from JSON into LocationDataDB
"""

import json
import pyodbc
import glob
from datetime import datetime

def get_latest_texas_file():
    """Get the latest Texas municipalities JSON file"""
    files = glob.glob("StateJsons/texas_municipalities_*.json")
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

def get_or_create_state(cursor, state_code, state_name):
    """Get or create state record"""
    # Check if state exists
    cursor.execute("SELECT StateCode FROM States WHERE StateCode = ?", state_code)
    if cursor.fetchone():
        return state_code
    
    # Create state if it doesn't exist
    cursor.execute("""
        INSERT INTO States (StateCode, StateName, IsActive, CreatedDate, ModifiedDate)
        VALUES (?, ?, 1, GETUTCDATE(), GETUTCDATE())
    """, state_code, state_name)
    print(f"✅ Created state record: {state_name} ({state_code})")
    return state_code

def get_or_create_county(cursor, county_name, state_code):
    """Get or create county record"""
    # Check if county exists
    cursor.execute("""
        SELECT CountyId FROM Counties 
        WHERE CountyName = ? AND StateCode = ?
    """, county_name, state_code)
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Create county if it doesn't exist
    cursor.execute("""
        INSERT INTO Counties (StateCode, CountyName, IsActive, CreatedDate, ModifiedDate)
        OUTPUT INSERTED.CountyId
        VALUES (?, ?, 1, GETUTCDATE(), GETUTCDATE())
    """, state_code, county_name)
    county_id = cursor.fetchone()[0]
    print(f"✅ Created county record: {county_name} (ID: {county_id})")
    return county_id

def import_texas_municipalities():
    """Import Texas municipalities from JSON to SQL"""
    
    # Get latest file
    json_file = get_latest_texas_file()
    if not json_file:
        print("❌ No Texas municipalities JSON file found!")
        return False
    
    print(f"📊 Importing from: {json_file}")
    
    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    municipalities = data['municipalities']
    print(f"📍 Found {len(municipalities)} municipalities to import")
    
    # Connect to database
    conn = connect_to_database()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Ensure Texas state exists
        state_code = get_or_create_state(cursor, 'TX', 'Texas')
        
        # Track statistics
        imported_count = 0
        updated_count = 0
        error_count = 0
        created_counties = set()
        
        print("\n🏗️ Starting import process...")
        
        for i, muni in enumerate(municipalities, 1):
            try:
                name = muni.get('name', '').strip()
                if not name or name == '#N/A':
                    continue
                
                # Get primary county
                primary_county = muni.get('primary_county', '').replace(' County', '').strip()
                if not primary_county:
                    primary_county = 'Unknown'
                
                # Get or create county
                county_id = get_or_create_county(cursor, primary_county, state_code)
                if primary_county not in created_counties:
                    created_counties.add(primary_county)
                
                # Parse population
                population = muni.get('population')
                if isinstance(population, str):
                    # Clean population string
                    population = population.replace(',', '').replace(' ', '')
                    try:
                        population = int(population) if population.isdigit() else None
                    except:
                        population = None
                
                # Get city type/designation
                city_type = muni.get('designation', muni.get('type', '')).strip()
                if not city_type:
                    city_type = 'City'
                
                # Check if city already exists
                cursor.execute("""
                    SELECT CityId FROM Cities 
                    WHERE CityName = ? AND StateCode = ? AND PrimaryCountyId = ?
                """, name, state_code, county_id)
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing city
                    city_id = existing[0]
                    cursor.execute("""
                        UPDATE Cities 
                        SET CityType = ?, ModifiedDate = GETUTCDATE(), LastUpdatedAt = GETDATE()
                        WHERE CityId = ?
                    """, city_type, city_id)
                    
                    # Handle population data
                    if population:
                        # Check if population data exists
                        cursor.execute("""
                            SELECT PopulationId FROM PopulationData 
                            WHERE LocationType = 'City' AND LocationId = ? AND CensusYear = 2020
                        """, city_id)
                        
                        pop_existing = cursor.fetchone()
                        if pop_existing:
                            # Update existing population
                            cursor.execute("""
                                UPDATE PopulationData 
                                SET Population = ?, ModifiedDate = GETUTCDATE()
                                WHERE PopulationId = ?
                            """, population, pop_existing[0])
                        else:
                            # Insert new population data
                            cursor.execute("""
                                INSERT INTO PopulationData (
                                    LocationType, LocationId, CensusYear, Population,
                                    DataSource, IsActive, CreatedDate, ModifiedDate, CreatedAt
                                ) VALUES ('City', ?, 2020, ?, 'Wikipedia', 1, GETUTCDATE(), GETUTCDATE(), GETDATE())
                            """, city_id, population)
                    
                    updated_count += 1
                    if i % 100 == 0:
                        print(f"  📝 Updated {name} (population: {population:,})")
                else:
                    # Insert new city
                    cursor.execute("""
                        INSERT INTO Cities (
                            StateCode, PrimaryCountyId, CityName, CityType,
                            IsActive, CreatedDate, ModifiedDate, CreatedAt, LastUpdatedAt
                        ) OUTPUT INSERTED.CityId
                        VALUES (?, ?, ?, ?, 1, GETUTCDATE(), GETUTCDATE(), GETDATE(), GETDATE())
                    """, state_code, county_id, name, city_type)
                    
                    city_id = cursor.fetchone()[0]
                    
                    # Insert population data if available
                    if population:
                        cursor.execute("""
                            INSERT INTO PopulationData (
                                LocationType, LocationId, CensusYear, Population,
                                DataSource, IsActive, CreatedDate, ModifiedDate, CreatedAt
                            ) VALUES ('City', ?, 2020, ?, 'Wikipedia', 1, GETUTCDATE(), GETUTCDATE(), GETDATE())
                        """, city_id, population)
                    
                    imported_count += 1
                    if i % 100 == 0:
                        print(f"  ✅ Imported {name} (population: {population:,})")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error processing {muni.get('name', 'Unknown')}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        
        # Print summary
        print(f"\n📊 IMPORT SUMMARY")
        print(f"=" * 40)
        print(f"✅ New cities imported: {imported_count}")
        print(f"📝 Existing cities updated: {updated_count}")
        print(f"❌ Errors encountered: {error_count}")
        print(f"🗺️ Counties processed: {len(created_counties)}")
        print(f"📁 Source file: {json_file}")
        
        # Verify import
        cursor.execute("SELECT COUNT(*) FROM Cities WHERE StateCode = 'TX'")
        total_tx_cities = cursor.fetchone()[0]
        print(f"🏙️ Total Texas cities in database: {total_tx_cities}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🏛️ TEXAS MUNICIPALITIES SQL IMPORT")
    print("=" * 50)
    success = import_texas_municipalities()
    if success:
        print("\n🎉 Import completed successfully!")
    else:
        print("\n💥 Import failed!")