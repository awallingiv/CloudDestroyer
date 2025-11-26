@echo off
echo 🚀 COMPREHENSIVE ZIP CODE COLLECTION - REMAINING 37 STATES
echo ==========================================================

REM First batch - New England & Northeast (7 states)
set batch1=Maine "New Hampshire" Vermont Massachusetts "Rhode Island" Connecticut "New Jersey"

REM Second batch - Southeast (8 states) 
set batch2=Alabama Arkansas Kentucky Louisiana Mississippi "North Carolina" "South Carolina" Tennessee

REM Third batch - Midwest (7 states)
set batch3=Indiana Iowa Kansas Minnesota Missouri Nebraska "North Dakota"

REM Fourth batch - Mountain West (8 states)
set batch4=Idaho Montana Nevada "New Mexico" Utah Wyoming "South Dakota" Oklahoma

REM Fifth batch - Pacific & Others (7 states)
set batch5=Alaska Hawaii Oregon Delaware Maryland "West Virginia" Wisconsin

echo Processing Batch 1 - New England ^& Northeast (7 states)
echo =====================================================
for %%s in (%batch1%) do (
    echo.
    echo 🏛️ Processing %%s...
    python zipcode_generator.py %%s
    if errorlevel 1 (
        echo ❌ Failed to generate ZIP codes for %%s
    ) else (
        python import_zipcodes_to_sql.py %%s
        if not errorlevel 1 echo ✅ Completed %%s
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo Processing Batch 2 - Southeast (8 states)
echo =========================================
for %%s in (%batch2%) do (
    echo.
    echo 🏛️ Processing %%s...
    python zipcode_generator.py %%s
    if errorlevel 1 (
        echo ❌ Failed to generate ZIP codes for %%s
    ) else (
        python import_zipcodes_to_sql.py %%s
        if not errorlevel 1 echo ✅ Completed %%s
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo Processing Batch 3 - Midwest (7 states)
echo =======================================
for %%s in (%batch3%) do (
    echo.
    echo 🏛️ Processing %%s...
    python zipcode_generator.py %%s
    if errorlevel 1 (
        echo ❌ Failed to generate ZIP codes for %%s
    ) else (
        python import_zipcodes_to_sql.py %%s
        if not errorlevel 1 echo ✅ Completed %%s
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo Processing Batch 4 - Mountain West (8 states)
echo =============================================
for %%s in (%batch4%) do (
    echo.
    echo 🏛️ Processing %%s...
    python zipcode_generator.py %%s
    if errorlevel 1 (
        echo ❌ Failed to generate ZIP codes for %%s
    ) else (
        python import_zipcodes_to_sql.py %%s
        if not errorlevel 1 echo ✅ Completed %%s
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo Processing Batch 5 - Pacific ^& Others (7 states)
echo =================================================
for %%s in (%batch5%) do (
    echo.
    echo 🏛️ Processing %%s...
    python zipcode_generator.py %%s
    if errorlevel 1 (
        echo ❌ Failed to generate ZIP codes for %%s
    ) else (
        python import_zipcodes_to_sql.py %%s
        if not errorlevel 1 echo ✅ Completed %%s
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo 🎉 ALL 37 REMAINING STATES PROCESSED!
echo ===================================
echo Generating comprehensive final report...

python -c "
import pyodbc
conn = pyodbc.connect('Driver={ODBC Driver 17 for SQL Server};Server=.;Database=LocationDataDB;Trusted_Connection=yes;')
cursor = conn.cursor()

print('\n🏆 FINAL COMPLETE ZIP CODE DATABASE STATUS')
print('=' * 60)

cursor.execute('SELECT StateCode, COUNT(*) as ZipCount FROM Zipcodes GROUP BY StateCode ORDER BY ZipCount DESC')
total_zips = 0
state_count = 0

for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]:,} ZIP codes')
    total_zips += row[1]
    state_count += 1

print(f'\n📊 GRAND TOTAL: {total_zips:,} ZIP CODES')
print(f'🗺️  STATES COMPLETE: {state_count}/50 US States')
print(f'📈 COVERAGE: {(state_count/50)*100:.1f}% of United States')

# Check if we have all 50 states
if state_count == 50:
    print('\n🇺🇸 ACHIEVEMENT UNLOCKED: ALL 50 STATES COMPLETE!')
else:
    cursor.execute('SELECT DISTINCT StateCode FROM States WHERE StateCode NOT IN (SELECT DISTINCT StateCode FROM Zipcodes)')
    missing = [row[0] for row in cursor.fetchall()]
    if missing:
        print(f'\n📝 Missing states: {missing}')

conn.close()
"

pause