@echo off
echo 🚀 BATCH ZIP CODE COLLECTION FOR MULTIPLE STATES
echo ==================================================

set states=Florida Georgia Illinois Michigan Ohio Pennsylvania Virginia Washington Colorado Arizona

for %%s in (%states%) do (
    echo.
    echo 🏛️ Processing %%s...
    python zipcode_generator.py "%%s"
    if errorlevel 1 (
        echo ❌ Failed to generate ZIP codes for %%s
    ) else (
        echo ✅ Generated ZIP codes for %%s
        python import_zipcodes_to_sql.py "%%s"
        if errorlevel 1 (
            echo ❌ Failed to import ZIP codes for %%s
        ) else (
            echo ✅ Imported ZIP codes for %%s
        )
    )
    timeout /t 2 /nobreak >nul
)

echo.
echo 🎉 Batch processing completed!
echo Checking final database status...
python -c "import pyodbc; conn = pyodbc.connect('Driver={ODBC Driver 17 for SQL Server};Server=.;Database=LocationDataDB;Trusted_Connection=yes;'); cursor = conn.cursor(); cursor.execute('SELECT StateCode, COUNT(*) as ZipCount FROM Zipcodes GROUP BY StateCode ORDER BY ZipCount DESC'); total = 0; print('FINAL ZIP CODE COUNTS:'); print('====================='); [print(f'{row[0]}: {row[1]:,} ZIP codes') or setattr(total, 'x', getattr(total, 'x', 0) + row[1]) for row in cursor.fetchall()]; print(f'\nTOTAL: {sum([row[1] for row in cursor.execute(\"SELECT COUNT(*) FROM Zipcodes\").fetchall()])} ZIP codes'); conn.close()"

pause