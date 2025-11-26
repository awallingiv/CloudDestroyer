@echo off
echo FoodFinder Database Setup Starting...
echo.

REM Change to SQL directory
cd /d "%~dp0"

echo Creating database...
sqlcmd -S localhost -E -i "01_create_database.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create database
    pause
    exit /b 1
)

echo Creating core tables...
sqlcmd -S localhost -d FoodFinder -E -i "02_core_tables.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create core tables
    pause
    exit /b 1
)

echo Creating search tables...
sqlcmd -S localhost -d FoodFinder -E -i "03_search_tables.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create search tables
    pause
    exit /b 1
)

echo Creating integration tables...
sqlcmd -S localhost -d FoodFinder -E -i "04_integration_tables.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create integration tables
    pause
    exit /b 1
)

echo Creating analytics tables...
sqlcmd -S localhost -d FoodFinder -E -i "05_analytics_tables.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create analytics tables
    pause
    exit /b 1
)

echo Creating operational tables...
sqlcmd -S localhost -d FoodFinder -E -i "06_operational_tables.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create operational tables
    pause
    exit /b 1
)

echo Inserting sample data...
sqlcmd -S localhost -d FoodFinder -E -i "07_initial_data.sql"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to insert sample data
    pause
    exit /b 1
)

echo.
echo ================================
echo FoodFinder Database Setup Complete!
echo ================================
echo.
echo You can now:
echo 1. Test queries with: sqlcmd -S localhost -d FoodFinder -E -i "08_useful_queries.sql"
echo 2. Connect your application to database "FoodFinder"
echo 3. Start adding restaurant data via your app
echo.
pause