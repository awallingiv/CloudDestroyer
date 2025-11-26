@echo off
REM =============================================================================
REM CloudDestroyer Municipality Collection - MISSING STATES ONLY
REM Batch script to process the 6 states missing from the database
REM 
REM Missing States: AK, CT, DE, ME, NY, VT
REM =============================================================================

echo.
echo ================================================================
echo CLOUDESTROYER - MISSING STATES PROCESSING
echo ================================================================
echo Processing 6 missing states from database
echo.

set START_TIME=%time%
echo Started at: %date% %time%
echo.

set TOTAL_STATES=6
set PROCESSED_STATES=0
set SUCCESSFUL_STATES=0

echo Current database has 44/50 states. Processing remaining 6 states...
echo.

REM Alaska (149 municipalities)
echo [1/6] Processing Alaska...
echo Estimated municipalities: 149
python generic_state_scraper.py "Alaska" "https://en.wikipedia.org/wiki/List_of_cities_and_boroughs_in_Alaska"
if %errorlevel% equ 0 (
    echo ✓ Alaska scraping completed successfully!
    python import_state_to_sql.py "alaska"
    if %errorlevel% equ 0 (
        echo ✓ Alaska import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Alaska import failed!
    )
) else (
    echo ✗ Alaska scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Connecticut (169 municipalities)
echo [2/6] Processing Connecticut...
echo Estimated municipalities: 169
python generic_state_scraper.py "Connecticut" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Connecticut"
if %errorlevel% equ 0 (
    echo ✓ Connecticut scraping completed successfully!
    python import_state_to_sql.py "connecticut"
    if %errorlevel% equ 0 (
        echo ✓ Connecticut import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Connecticut import failed!
    )
) else (
    echo ✗ Connecticut scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Delaware (57 municipalities)
echo [3/6] Processing Delaware...
echo Estimated municipalities: 57
python generic_state_scraper.py "Delaware" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Delaware"
if %errorlevel% equ 0 (
    echo ✓ Delaware scraping completed successfully!
    python import_state_to_sql.py "delaware"
    if %errorlevel% equ 0 (
        echo ✓ Delaware import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Delaware import failed!
    )
) else (
    echo ✗ Delaware scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Maine (488 municipalities)
echo [4/6] Processing Maine...
echo Estimated municipalities: 488
python generic_state_scraper.py "Maine" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Maine"
if %errorlevel% equ 0 (
    echo ✓ Maine scraping completed successfully!
    python import_state_to_sql.py "maine"
    if %errorlevel% equ 0 (
        echo ✓ Maine import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Maine import failed!
    )
) else (
    echo ✗ Maine scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM New York (62 municipalities - cities only)
echo [5/6] Processing New York...
echo Estimated municipalities: 62 (cities only)
python generic_state_scraper.py "New York" "https://en.wikipedia.org/wiki/List_of_cities_in_New_York"
if %errorlevel% equ 0 (
    echo ✓ New York scraping completed successfully!
    python import_state_to_sql.py "new york"
    if %errorlevel% equ 0 (
        echo ✓ New York import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ New York import failed!
    )
) else (
    echo ✗ New York scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Vermont (255 municipalities)
echo [6/6] Processing Vermont...
echo Estimated municipalities: 255
python generic_state_scraper.py "Vermont" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Vermont"
if %errorlevel% equ 0 (
    echo ✓ Vermont scraping completed successfully!
    python import_state_to_sql.py "vermont"
    if %errorlevel% equ 0 (
        echo ✓ Vermont import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Vermont import failed!
    )
) else (
    echo ✗ Vermont scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Final summary
echo.
echo ================================================================
echo PROCESSING COMPLETE - ALL 50 U.S. STATES!
echo ================================================================
echo Successfully processed: %SUCCESSFUL_STATES%/%TOTAL_STATES% missing states
echo Started at: %START_TIME%
echo Finished at: %time%
echo.

if %SUCCESSFUL_STATES% equ %TOTAL_STATES% (
    echo *** CONGRATULATIONS! ALL 50 U.S. STATES NOW COMPLETED! ***
    echo Database now contains municipalities from all 50 states!
    echo Previous: 44 states
    echo Added: 6 states
    echo Total: 50/50 states - COMPLETE!
) else (
    set /a FAILED_STATES=%TOTAL_STATES%-%SUCCESSFUL_STATES%
    echo *** %FAILED_STATES% state(s) failed processing. ***
    echo Check output above for details on failed states.
    set /a TOTAL_COMPLETED=44+%SUCCESSFUL_STATES%
    echo Current total: %TOTAL_COMPLETED%/50 states
)

echo.
echo Expected municipality additions: ~1,180 municipalities
echo Run county count query again to verify all states are present
echo.
pause