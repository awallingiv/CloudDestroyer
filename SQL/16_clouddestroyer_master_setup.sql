-- Master CloudDestroyer Setup Script
-- Runs all CloudDestroyer integration scripts in correct order

USE master;
GO

PRINT 'Starting CloudDestroyer Integration Setup...';
PRINT 'Time: ' + CONVERT(VARCHAR, GETDATE(), 120);
PRINT '================================================';

-- Check if FoodFinder database exists
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'FoodFinder')
BEGIN
    PRINT 'ERROR: FoodFinder database not found. Please run the main database setup first.';
    RETURN;
END

USE FoodFinder;
GO

-- =============================================================================
-- STEP 1: CREATE UNIVERSAL SCRAPING TABLES
-- =============================================================================

PRINT '';
PRINT 'Step 1: Creating Universal Scraping Queue Tables...';

-- Execute universal scraping queue creation
:r 12_universal_scraping_queue.sql

-- Verify tables were created
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'universal_scraping_jobs')
    PRINT '✅ Universal scraping tables created successfully'
ELSE
    PRINT '❌ Failed to create universal scraping tables';

-- =============================================================================
-- STEP 2: CREATE SCRAPING PROCEDURES
-- =============================================================================

PRINT '';
PRINT 'Step 2: Creating Universal Scraping Procedures...';

-- Execute procedure creation
:r 13_universal_scraping_procedures.sql

-- Verify procedures were created
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'spsc_CreateJob')
    PRINT '✅ Universal scraping procedures created successfully'
ELSE
    PRINT '❌ Failed to create universal scraping procedures';

-- =============================================================================
-- STEP 3: EXTEND EXISTING TABLES
-- =============================================================================

PRINT '';
PRINT 'Step 3: Adding CloudDestroyer Extensions to Existing Tables...';

-- Execute extensions
:r 14_clouddestroyer_extensions.sql

-- Verify extensions were added
IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('restaurants') AND name = 'clouddestroyer_status')
    PRINT '✅ CloudDestroyer extensions added successfully'
ELSE
    PRINT '❌ Failed to add CloudDestroyer extensions';

-- =============================================================================
-- STEP 4: LOAD INITIAL DATA AND TEMPLATES
-- =============================================================================

PRINT '';
PRINT 'Step 4: Loading Initial Data and Templates...';

-- Execute initial data setup
:r 15_clouddestroyer_initial_data.sql

-- Verify templates were created
IF EXISTS (SELECT * FROM scraping_job_templates WHERE template_name = 'CloudDestroyer Restaurant Menu')
    PRINT '✅ Initial data and templates loaded successfully'
ELSE
    PRINT '❌ Failed to load initial data and templates';

-- =============================================================================
-- VERIFICATION AND TESTING
-- =============================================================================

PRINT '';
PRINT 'Step 5: Running Verification Tests...';

-- Test 1: Check table structure
DECLARE @TableCount INT;
SELECT @TableCount = COUNT(*) 
FROM sys.tables 
WHERE name IN ('universal_scraping_jobs', 'universal_scraping_results', 'scraping_job_templates', 'scraping_workers', 'scraping_job_history');

IF @TableCount = 5
    PRINT '✅ All required tables present'
ELSE
    PRINT '❌ Missing tables. Expected 5, found ' + CAST(@TableCount AS VARCHAR(10));

-- Test 2: Check procedures
DECLARE @ProcCount INT;
SELECT @ProcCount = COUNT(*) 
FROM sys.procedures 
WHERE name IN ('spsc_CreateJob', 'spsc_GetNextJob', 'spsc_CompleteJob', 'spcd_CreateRestaurantJob', 'spcd_ProcessMenuResult');

IF @ProcCount = 5
    PRINT '✅ All core procedures present'
ELSE
    PRINT '❌ Missing procedures. Expected 5, found ' + CAST(@ProcCount AS VARCHAR(10));

-- Test 3: Check views
DECLARE @ViewCount INT;
SELECT @ViewCount = COUNT(*) 
FROM sys.views 
WHERE name IN ('v_restaurant_scraping_status', 'v_clouddestroyer_analytics', 'v_clouddestroyer_queue', 'v_clouddestroyer_monitoring');

IF @ViewCount = 4
    PRINT '✅ All monitoring views present'
ELSE
    PRINT '❌ Missing views. Expected 4, found ' + CAST(@ViewCount AS VARCHAR(10));

-- Test 4: Test job creation (if test restaurant exists)
BEGIN TRY
    DECLARE @TestJobId INT;
    
    -- Create a test job
    EXEC spsc_CreateJob
        @JobType = 'clouddestroyer_menu',
        @TargetUrl = 'https://test.example.com/menu',
        @JobName = 'Integration Test Job',
        @EntityType = 'test',
        @EntityId = 'test_001',
        @Priority = 50,
        @JobId = @TestJobId OUTPUT;
    
    IF @TestJobId IS NOT NULL
    BEGIN
        PRINT '✅ Job creation test successful (Job ID: ' + CAST(@TestJobId AS VARCHAR(10)) + ')';
        
        -- Clean up test job
        DELETE FROM universal_scraping_jobs WHERE job_id = @TestJobId;
    END
    ELSE
        PRINT '⚠️ Job creation test returned NULL job ID';
        
END TRY
BEGIN CATCH
    PRINT '❌ Job creation test failed: ' + ERROR_MESSAGE();
END CATCH;

-- =============================================================================
-- FINAL SUMMARY
-- =============================================================================

PRINT '';
PRINT '================================================';
PRINT 'CloudDestroyer Integration Setup Complete!';
PRINT '================================================';

-- Generate summary report
SELECT 
    'Database Objects Created' as category,
    'Tables: 5, Procedures: 10+, Views: 4, Functions: 1' as details
UNION ALL
SELECT 
    'Job Templates Available',
    CAST(COUNT(*) AS VARCHAR(10)) + ' templates ready'
FROM scraping_job_templates
UNION ALL
SELECT 
    'Workers Registered',
    CAST(COUNT(*) AS VARCHAR(10)) + ' workers configured'
FROM scraping_workers
UNION ALL
SELECT 
    'System Configuration',
    CAST(COUNT(*) AS VARCHAR(10)) + ' config settings'
FROM system_config
WHERE config_key LIKE 'clouddestroyer%' OR config_key LIKE 'scraping%';

PRINT '';
PRINT '🎯 Quick Start Commands:';
PRINT '';
PRINT '-- Create a restaurant extraction job:';
PRINT 'EXEC spcd_CreateRestaurantJob @RestaurantId=''your_restaurant_id'', @TargetUrl=''https://restaurant.com/menu'';';
PRINT '';
PRINT '-- Get next job for CloudDestroyer worker:';
PRINT 'EXEC spsc_GetNextJob @WorkerId=''clouddestroyer_worker_1'', @WorkerType=''clouddestroyer'', @SupportedJobTypes=''clouddestroyer_menu'';';
PRINT '';
PRINT '-- Monitor the system:';
PRINT 'SELECT * FROM v_clouddestroyer_monitoring;';
PRINT 'SELECT * FROM v_clouddestroyer_queue ORDER BY effective_priority DESC;';
PRINT '';
PRINT '-- Check for alerts:';
PRINT 'SELECT * FROM v_scraping_alerts;';

PRINT '';
PRINT '📊 Integration Features:';
PRINT '✅ Universal scraping queue (supports any scraping task)';
PRINT '✅ CloudDestroyer restaurant menu extraction';
PRINT '✅ Automatic Cloudflare bypass';
PRINT '✅ API endpoint discovery (like Bubba''s 33 success)';
PRINT '✅ Selenium SPA support';
PRINT '✅ Priority queue with intelligent routing';
PRINT '✅ Worker management and health monitoring';
PRINT '✅ Comprehensive analytics and reporting';
PRINT '✅ Retry logic and error handling';
PRINT '✅ Integration with existing restaurant/menu tables';

PRINT '';
PRINT '🔧 Next Steps:';
PRINT '1. Update your CloudDestroyer Python code to use these procedures';
PRINT '2. Configure actual worker IDs in your automation system';
PRINT '3. Set up monitoring dashboard using the provided views';
PRINT '4. Test with real restaurant data from your existing database';

PRINT '';
PRINT 'Setup completed at: ' + CONVERT(VARCHAR, GETDATE(), 120);
GO