# FoodFinder Database Setup Script
# Run this PowerShell script to create the complete database

param(
    [string]$ServerName = "localhost",
    [switch]$UseWindowsAuth = $true,
    [string]$Username = "",
    [string]$Password = ""
)

Write-Host "FoodFinder Database Setup Starting..." -ForegroundColor Green
Write-Host "Server: $ServerName" -ForegroundColor Yellow

# Build connection parameters
$connectionParams = @("-S", $ServerName)
if ($UseWindowsAuth) {
    $connectionParams += "-E"
} else {
    if ($Username -and $Password) {
        $connectionParams += @("-U", $Username, "-P", $Password)
    } else {
        Write-Error "Username and Password required when not using Windows Authentication"
        exit 1
    }
}

# Set location to SQL directory
Set-Location $PSScriptRoot

# SQL files to execute in order
$sqlFiles = @(
    @{ File = "01_create_database.sql"; Database = "master"; Description = "Creating database" },
    @{ File = "02_core_tables.sql"; Database = "FoodFinder"; Description = "Creating core tables" },
    @{ File = "03_search_tables.sql"; Database = "FoodFinder"; Description = "Creating search tables" },
    @{ File = "04_integration_tables.sql"; Database = "FoodFinder"; Description = "Creating integration tables" },
    @{ File = "05_analytics_tables.sql"; Database = "FoodFinder"; Description = "Creating analytics tables" },
    @{ File = "06_operational_tables.sql"; Database = "FoodFinder"; Description = "Creating operational tables" },
    @{ File = "07_initial_data.sql"; Database = "FoodFinder"; Description = "Inserting sample data" }
)

# Execute each SQL file
foreach ($sqlFile in $sqlFiles) {
    Write-Host "$($sqlFile.Description)..." -ForegroundColor Cyan
    
    $params = $connectionParams + @("-d", $sqlFile.Database, "-i", $sqlFile.File)
    $result = & sqlcmd @params
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to execute $($sqlFile.File)"
        Write-Host $result -ForegroundColor Red
        exit 1
    }
    
    Write-Host "$($sqlFile.Description) completed" -ForegroundColor Green
}

Write-Host ""
Write-Host "FoodFinder Database Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Test queries: sqlcmd -S $ServerName -d FoodFinder -E -i '08_useful_queries.sql'" -ForegroundColor Gray
Write-Host "2. Connect your React Native app to database 'FoodFinder'" -ForegroundColor Gray
Write-Host "3. Configure your backend to use this database" -ForegroundColor Gray
Write-Host ""
Write-Host "Happy coding!" -ForegroundColor Magenta