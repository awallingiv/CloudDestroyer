@echo off
REM =============================================================================
REM CloudDestroyer Municipality Collection - Remaining High Priority States
REM Batch script to process Massachusetts, Tennessee, Washington, Colorado,
REM Virginia, Arizona, and New York state municipalities
REM =============================================================================

echo.
echo ========================================
echo REMAINING HIGH-PRIORITY STATES PROCESSING
echo ========================================
echo.

set START_TIME=%time%
echo Started at: %date% %time%
echo.

set TOTAL_STATES=7
set PROCESSED_STATES=0
set SUCCESSFUL_STATES=0

echo Processing %TOTAL_STATES% remaining high-priority states...
echo.

REM Massachusetts (351 municipalities)
echo.
echo [1/7] Processing Massachusetts...
echo Estimated municipalities: 351
python generic_state_scraper.py "Massachusetts" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Massachusetts"
if %errorlevel% equ 0 (
    echo ✓ Massachusetts scraping completed successfully!
    python import_state_to_sql.py "massachusetts"
    if %errorlevel% equ 0 (
        echo ✓ Massachusetts import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Massachusetts import failed!
    )
) else (
    echo ✗ Massachusetts scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Tennessee (345 municipalities)
echo.
echo [2/7] Processing Tennessee...
echo Estimated municipalities: 345
python generic_state_scraper.py "Tennessee" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Tennessee"
if %errorlevel% equ 0 (
    echo ✓ Tennessee scraping completed successfully!
    python import_state_to_sql.py "tennessee"
    if %errorlevel% equ 0 (
        echo ✓ Tennessee import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Tennessee import failed!
    )
) else (
    echo ✗ Tennessee scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Washington (281 municipalities)
echo.
echo [3/7] Processing Washington...
echo Estimated municipalities: 281
python generic_state_scraper.py "Washington" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Washington"
if %errorlevel% equ 0 (
    echo ✓ Washington scraping completed successfully!
    python import_state_to_sql.py "washington"
    if %errorlevel% equ 0 (
        echo ✓ Washington import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Washington import failed!
    )
) else (
    echo ✗ Washington scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Colorado (272 municipalities)
echo.
echo [4/7] Processing Colorado...
echo Estimated municipalities: 272
python generic_state_scraper.py "Colorado" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Colorado"
if %errorlevel% equ 0 (
    echo ✓ Colorado scraping completed successfully!
    python import_state_to_sql.py "colorado"
    if %errorlevel% equ 0 (
        echo ✓ Colorado import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Colorado import failed!
    )
) else (
    echo ✗ Colorado scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Virginia (230 municipalities)
echo.
echo [5/7] Processing Virginia...
echo Estimated municipalities: 230
python generic_state_scraper.py "Virginia" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Virginia"
if %errorlevel% equ 0 (
    echo ✓ Virginia scraping completed successfully!
    python import_state_to_sql.py "virginia"
    if %errorlevel% equ 0 (
        echo ✓ Virginia import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Virginia import failed!
    )
) else (
    echo ✗ Virginia scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Arizona (91 municipalities)
echo.
echo [6/7] Processing Arizona...
echo Estimated municipalities: 91
python generic_state_scraper.py "Arizona" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Arizona"
if %errorlevel% equ 0 (
    echo ✓ Arizona scraping completed successfully!
    python import_state_to_sql.py "arizona"
    if %errorlevel% equ 0 (
        echo ✓ Arizona import completed successfully!
        set /a SUCCESSFUL_STATES+=1
    ) else (
        echo ✗ Arizona import failed!
    )
) else (
    echo ✗ Arizona scraping failed!
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM New York (62 municipalities)
echo.
echo [7/7] Processing New York...
echo Estimated municipalities: 62
python generic_state_scraper.py "New York" "https://en.wikipedia.org/wiki/List_of_municipalities_in_New_York"
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

REM Final summary
echo.
echo ========================================
echo PROCESSING COMPLETE!
echo ========================================
echo Successfully processed: %SUCCESSFUL_STATES%/%TOTAL_STATES% states
echo Started at: %START_TIME%
echo Finished at: %time%
echo.

if %SUCCESSFUL_STATES% equ %TOTAL_STATES% (
    echo *** ALL HIGH-PRIORITY STATES COMPLETED! ***
    echo Total database now contains municipalities from 23 states!
) else (
    set /a FAILED_STATES=%TOTAL_STATES%-%SUCCESSFUL_STATES%
    echo *** %FAILED_STATES% state(s) failed processing. Check output above for details. ***
)

echo.
echo Next steps: Process medium priority states (IA, KS, NE, AR, etc.)
echo.
pause