@echo off
REM =============================================================================
REM CloudDestroyer Municipality Collection - ALL REMAINING STATES
REM Batch script to process all 34 remaining U.S. states
REM 
REM COMPLETED STATES (16): TX, CA, FL, PA, IL, MO, OH, MN, WI, OK, IN, NJ, NC, GA, MI, AL
REM REMAINING STATES (34): All others listed below
REM =============================================================================

echo.
echo ================================================================
echo CLOUDESTROYER - ALL REMAINING U.S. STATES PROCESSING
echo ================================================================
echo Processing 34 remaining states in priority order
echo.

set START_TIME=%time%
echo Started at: %date% %time%
echo.

set TOTAL_STATES=34
set PROCESSED_STATES=0
set SUCCESSFUL_STATES=0

REM =============================================================================
REM HIGH PRIORITY STATES (Remaining 7 states)
REM =============================================================================
echo.
echo *** HIGH PRIORITY STATES (7 remaining) ***
echo.

REM Massachusetts (351 municipalities)
echo [1/34] Processing Massachusetts... (HIGH PRIORITY)
python generic_state_scraper.py "Massachusetts" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Massachusetts"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "massachusetts"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Tennessee (345 municipalities)
echo [2/34] Processing Tennessee... (HIGH PRIORITY)
python generic_state_scraper.py "Tennessee" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Tennessee"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "tennessee"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Washington (281 municipalities)
echo [3/34] Processing Washington... (HIGH PRIORITY)
python generic_state_scraper.py "Washington" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Washington"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "washington"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Colorado (272 municipalities)
echo [4/34] Processing Colorado... (HIGH PRIORITY)
python generic_state_scraper.py "Colorado" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Colorado"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "colorado"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Virginia (230 municipalities)
echo [5/34] Processing Virginia... (HIGH PRIORITY)
python generic_state_scraper.py "Virginia" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Virginia"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "virginia"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Arizona (91 municipalities)
echo [6/34] Processing Arizona... (HIGH PRIORITY)
python generic_state_scraper.py "Arizona" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Arizona"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "arizona"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM New York (62 municipalities)
echo [7/34] Processing New York... (HIGH PRIORITY)
python generic_state_scraper.py "New York" "https://en.wikipedia.org/wiki/List_of_cities_in_New_York"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "new york"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM =============================================================================
REM MEDIUM PRIORITY STATES (17 states)
REM =============================================================================
echo.
echo *** MEDIUM PRIORITY STATES (17 remaining) ***
echo.

REM Iowa (947 municipalities)
echo [8/34] Processing Iowa... (MEDIUM PRIORITY)
python generic_state_scraper.py "Iowa" "https://en.wikipedia.org/wiki/List_of_cities_in_Iowa"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "iowa"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Kansas (627 municipalities)
echo [9/34] Processing Kansas... (MEDIUM PRIORITY)
python generic_state_scraper.py "Kansas" "https://en.wikipedia.org/wiki/List_of_cities_in_Kansas"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "kansas"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Nebraska (531 municipalities)
echo [10/34] Processing Nebraska... (MEDIUM PRIORITY)
python generic_state_scraper.py "Nebraska" "https://en.wikipedia.org/wiki/List_of_cities_in_Nebraska"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "nebraska"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Arkansas (502 municipalities) - Different URL format
echo [11/34] Processing Arkansas... (MEDIUM PRIORITY)
python generic_state_scraper.py "Arkansas" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Arkansas"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "arkansas"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Kentucky (424 municipalities)
echo [12/34] Processing Kentucky... (MEDIUM PRIORITY)
python generic_state_scraper.py "Kentucky" "https://en.wikipedia.org/wiki/List_of_cities_in_Kentucky"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "kentucky"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Louisiana (304 municipalities)
echo [13/34] Processing Louisiana... (MEDIUM PRIORITY)
python generic_state_scraper.py "Louisiana" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Louisiana"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "louisiana"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Mississippi (298 municipalities)
echo [14/34] Processing Mississippi... (MEDIUM PRIORITY)
python generic_state_scraper.py "Mississippi" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Mississippi"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "mississippi"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM South Carolina (269 municipalities)
echo [15/34] Processing South Carolina... (MEDIUM PRIORITY)
python generic_state_scraper.py "South Carolina" "https://en.wikipedia.org/wiki/List_of_municipalities_in_South_Carolina"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "south carolina"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Utah (248 municipalities)
echo [16/34] Processing Utah... (MEDIUM PRIORITY)
python generic_state_scraper.py "Utah" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Utah"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "utah"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Oregon (241 municipalities)
echo [17/34] Processing Oregon... (MEDIUM PRIORITY)
python generic_state_scraper.py "Oregon" "https://en.wikipedia.org/wiki/List_of_cities_in_Oregon"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "oregon"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Idaho (200 municipalities)
echo [18/34] Processing Idaho... (MEDIUM PRIORITY)
python generic_state_scraper.py "Idaho" "https://en.wikipedia.org/wiki/List_of_cities_in_Idaho"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "idaho"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Connecticut (169 municipalities)
echo [19/34] Processing Connecticut... (MEDIUM PRIORITY)
python generic_state_scraper.py "Connecticut" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Connecticut"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "connecticut"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Maryland (157 municipalities)
echo [20/34] Processing Maryland... (MEDIUM PRIORITY)
python generic_state_scraper.py "Maryland" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Maryland"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "maryland"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM New Mexico (106 municipalities)
echo [21/34] Processing New Mexico... (MEDIUM PRIORITY)
python generic_state_scraper.py "New Mexico" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_New_Mexico"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "new mexico"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Nevada (19 municipalities)
echo [22/34] Processing Nevada... (MEDIUM PRIORITY)
python generic_state_scraper.py "Nevada" "https://en.wikipedia.org/wiki/List_of_cities_in_Nevada"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "nevada"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Hawaii (5 municipalities) - Special case
echo [23/34] Processing Hawaii... (MEDIUM PRIORITY - Special Structure)
python generic_state_scraper.py "Hawaii" "https://en.wikipedia.org/wiki/List_of_places_in_Hawaii"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "hawaii"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Alaska (149 municipalities) - Different URL format
echo [24/34] Processing Alaska... (MEDIUM PRIORITY)
python generic_state_scraper.py "Alaska" "https://en.wikipedia.org/wiki/List_of_cities_and_boroughs_in_Alaska"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "alaska"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM =============================================================================
REM LOW PRIORITY STATES (10 states)
REM =============================================================================
echo.
echo *** LOW PRIORITY STATES (10 remaining) ***
echo.

REM Maine (488 municipalities)
echo [25/34] Processing Maine... (LOW PRIORITY)
python generic_state_scraper.py "Maine" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Maine"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "maine"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM North Dakota (357 municipalities)
echo [26/34] Processing North Dakota... (LOW PRIORITY)
python generic_state_scraper.py "North Dakota" "https://en.wikipedia.org/wiki/List_of_cities_in_North_Dakota"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "north dakota"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM South Dakota (311 municipalities)
echo [27/34] Processing South Dakota... (LOW PRIORITY)
python generic_state_scraper.py "South Dakota" "https://en.wikipedia.org/wiki/List_of_cities_in_South_Dakota"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "south dakota"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Vermont (255 municipalities)
echo [28/34] Processing Vermont... (LOW PRIORITY)
python generic_state_scraper.py "Vermont" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Vermont"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "vermont"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM New Hampshire (234 municipalities)
echo [29/34] Processing New Hampshire... (LOW PRIORITY)
python generic_state_scraper.py "New Hampshire" "https://en.wikipedia.org/wiki/List_of_municipalities_in_New_Hampshire"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "new hampshire"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM West Virginia (232 municipalities)
echo [30/34] Processing West Virginia... (LOW PRIORITY)
python generic_state_scraper.py "West Virginia" "https://en.wikipedia.org/wiki/List_of_cities_in_West_Virginia"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "west virginia"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Montana (129 municipalities)
echo [31/34] Processing Montana... (LOW PRIORITY)
python generic_state_scraper.py "Montana" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Montana"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "montana"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Wyoming (99 municipalities)
echo [32/34] Processing Wyoming... (LOW PRIORITY)
python generic_state_scraper.py "Wyoming" "https://en.wikipedia.org/wiki/List_of_municipalities_in_Wyoming"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "wyoming"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Delaware (57 municipalities)
echo [33/34] Processing Delaware... (LOW PRIORITY)
python generic_state_scraper.py "Delaware" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Delaware"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "delaware"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM Rhode Island (39 municipalities)
echo [34/34] Processing Rhode Island... (LOW PRIORITY)
python generic_state_scraper.py "Rhode Island" "https://en.wikipedia.org/wiki/List_of_cities_and_towns_in_Rhode_Island"
if %errorlevel% equ 0 (
    python import_state_to_sql.py "rhode island"
    if %errorlevel% equ 0 (set /a SUCCESSFUL_STATES+=1)
)
set /a PROCESSED_STATES+=1
echo --------------------------------------------------

REM =============================================================================
REM FINAL SUMMARY
REM =============================================================================
echo.
echo ================================================================
echo PROCESSING COMPLETE - ALL 50 U.S. STATES!
echo ================================================================
echo Successfully processed: %SUCCESSFUL_STATES%/%TOTAL_STATES% states
echo Started at: %START_TIME%
echo Finished at: %time%
echo.

if %SUCCESSFUL_STATES% equ %TOTAL_STATES% (
    echo *** CONGRATULATIONS! ALL 50 U.S. STATES COMPLETED! ***
    echo Total database now contains municipalities from all 50 states!
    echo Estimated total: Over 20,000 municipalities!
) else (
    set /a FAILED_STATES=%TOTAL_STATES%-%SUCCESSFUL_STATES%
    echo *** %FAILED_STATES% state(s) failed processing. ***
    echo Check output above for details on failed states.
)

echo.
echo Final step: Run comprehensive verification and statistics report
echo.
pause