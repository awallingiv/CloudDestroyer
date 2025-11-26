#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Process all remaining high-priority U.S. states for municipality data collection
.DESCRIPTION
    This script runs the generic state scraper and import process for all remaining
    high-priority states: Massachusetts, Tennessee, Washington, Colorado, Virginia, Arizona, and New York
.NOTES
    Author: CloudDestroyer Municipality Collection System
    Date: November 24, 2025
#>

Write-Host "🗺️ REMAINING HIGH-PRIORITY STATES PROCESSING SCRIPT" -ForegroundColor Cyan
Write-Host "=" -repeat 60 -ForegroundColor Cyan
Write-Host ""

# Function to process a single state
function Process-State {
    param(
        [string]$StateName,
        [string]$WikipediaURL,
        [int]$EstimatedMunicipalities
    )
    
    Write-Host "🏛️ Processing: $StateName" -ForegroundColor Yellow
    Write-Host "📍 Estimated municipalities: $EstimatedMunicipalities" -ForegroundColor Gray
    Write-Host "🔗 URL: $WikipediaURL" -ForegroundColor Gray
    Write-Host ""
    
    # Scrape the state
    Write-Host "🚀 Scraping $StateName municipalities..." -ForegroundColor Green
    & python generic_state_scraper.py "$StateName" "$WikipediaURL"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $StateName scraping completed successfully!" -ForegroundColor Green
        
        # Import to database
        Write-Host "📊 Importing $StateName to SQL database..." -ForegroundColor Blue
        & python import_state_to_sql.py "$($StateName.ToLower())"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $StateName import completed successfully!" -ForegroundColor Green
        } else {
            Write-Host "❌ $StateName import failed!" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ $StateName scraping failed!" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "-" -repeat 50 -ForegroundColor Gray
    Write-Host ""
}
}

# Start processing
$startTime = Get-Date
Write-Host "⏰ Started at: $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host ""

# High Priority States (in order of estimated municipality count)
$states = @(
    @{Name="Massachusetts"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_Massachusetts"; Count=351},
    @{Name="Tennessee"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_Tennessee"; Count=345},
    @{Name="Washington"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_Washington"; Count=281},
    @{Name="Colorado"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_Colorado"; Count=272},
    @{Name="Virginia"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_Virginia"; Count=230},
    @{Name="Arizona"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_Arizona"; Count=91},
    @{Name="New York"; URL="https://en.wikipedia.org/wiki/List_of_municipalities_in_New_York"; Count=62}
)

$totalStates = $states.Count
$processedStates = 0
$successfulStates = 0

Write-Host "📋 Processing $totalStates remaining high-priority states..." -ForegroundColor Cyan
Write-Host ""

foreach ($state in $states) {
    $processedStates++
    Write-Host "[$processedStates/$totalStates] " -NoNewline -ForegroundColor Magenta
    
    Process-State -StateName $state.Name -WikipediaURL $state.URL -EstimatedMunicipalities $state.Count
    
    if ($LASTEXITCODE -eq 0) {
        $successfulStates++
    }
}

# Final summary
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "🎉 PROCESSING COMPLETE!" -ForegroundColor Green
Write-Host "=" -repeat 30 -ForegroundColor Green
Write-Host "✅ Successfully processed: $successfulStates/$totalStates states" -ForegroundColor Green
Write-Host "⏱️ Total processing time: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Cyan
Write-Host "🏁 Finished at: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host ""

if ($successfulStates -eq $totalStates) {
    Write-Host "🏆 ALL HIGH-PRIORITY STATES COMPLETED!" -ForegroundColor Green
    Write-Host "🗺️ Total database now contains municipalities from 23 states!" -ForegroundColor Yellow
} else {
    $failedStates = $totalStates - $successfulStates
    Write-Host "⚠️ $failedStates state(s) failed processing. Check logs above for details." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "💡 Next steps: Process medium priority states (IA, KS, NE, AR, etc.)" -ForegroundColor Cyan
Write-Host ""