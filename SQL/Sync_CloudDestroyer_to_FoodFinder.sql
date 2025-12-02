-- =============================================================================
-- Sync Procedures: CloudDestroyer -> FoodFinder
-- Cross-database synchronization of extraction results
-- =============================================================================

USE CloudDestroyer;
GO

-- =============================================================================
-- SECTION 1: SYNC STATUS TRACKING (in CloudDestroyer DB)
-- =============================================================================

-- Mark results as synced
IF OBJECT_ID('sp_MarkResultSynced') IS NOT NULL DROP PROCEDURE sp_MarkResultSynced;
GO

CREATE PROCEDURE sp_MarkResultSynced
    @ResultId INT,
    @SyncTarget VARCHAR(100) = 'FoodFinder',
    @Success BIT = 1,
    @ErrorMessage NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE scraping_results
    SET sync_status = CASE WHEN @Success = 1 THEN 'synced' ELSE 'failed' END,
        synced_at = CASE WHEN @Success = 1 THEN GETDATE() ELSE NULL END,
        sync_target = @SyncTarget,
        sync_error = @ErrorMessage
    WHERE result_id = @ResultId;
END;
GO

-- Get pending sync items
IF OBJECT_ID('sp_GetPendingSyncResults') IS NOT NULL DROP PROCEDURE sp_GetPendingSyncResults;
GO

CREATE PROCEDURE sp_GetPendingSyncResults
    @BatchSize INT = 100,
    @SyncTarget VARCHAR(100) = 'FoodFinder'
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT TOP (@BatchSize)
        r.result_id,
        r.job_id,
        j.entity_type,
        j.entity_id,
        j.target_url,
        r.result_type,
        r.structured_data,
        r.record_count,
        r.confidence_score,
        r.extracted_at,
        j.items_with_prices,
        j.price_extraction_status
    FROM scraping_results r
    INNER JOIN scraping_jobs j ON r.job_id = j.job_id
    WHERE r.sync_status = 'pending'
      AND r.validation_status IN ('valid', 'partial')
      AND r.structured_data IS NOT NULL
      AND j.entity_type = 'restaurant'
    ORDER BY r.extracted_at ASC;
END;
GO

-- =============================================================================
-- SECTION 2: SYNC PROCEDURE (runs from CloudDestroyer, writes to FoodFinder)
-- =============================================================================

-- Main sync procedure - syncs a single result to FoodFinder
IF OBJECT_ID('sp_SyncResultToFoodFinder') IS NOT NULL DROP PROCEDURE sp_SyncResultToFoodFinder;
GO

CREATE PROCEDURE sp_SyncResultToFoodFinder
    @ResultId INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @EntityId VARCHAR(100);
    DECLARE @StructuredData NVARCHAR(MAX);
    DECLARE @ItemsWithPrices INT;
    DECLARE @TargetUrl VARCHAR(1000);
    DECLARE @ErrorMessage NVARCHAR(MAX);
    
    BEGIN TRY
        -- Get result data
        SELECT 
            @EntityId = j.entity_id,
            @StructuredData = r.structured_data,
            @ItemsWithPrices = j.items_with_prices,
            @TargetUrl = j.target_url
        FROM scraping_results r
        INNER JOIN scraping_jobs j ON r.job_id = j.job_id
        WHERE r.result_id = @ResultId;
        
        IF @EntityId IS NULL OR @StructuredData IS NULL
        BEGIN
            EXEC sp_MarkResultSynced @ResultId = @ResultId, @Success = 0, @ErrorMessage = 'Missing entity_id or structured_data';
            RETURN;
        END
        
        -- Call FoodFinder import procedure
        -- Note: This requires linked server or same SQL instance
        EXEC FoodFinder.dbo.sp_ImportMenuData 
            @RestaurantId = @EntityId,
            @MenuData = @StructuredData,
            @MenuSource = 'clouddestroyer';
        
        -- Mark as synced
        EXEC sp_MarkResultSynced @ResultId = @ResultId, @Success = 1;
        
        SELECT @ResultId AS result_id, @EntityId AS entity_id, 'synced' AS status;
        
    END TRY
    BEGIN CATCH
        SET @ErrorMessage = ERROR_MESSAGE();
        EXEC sp_MarkResultSynced @ResultId = @ResultId, @Success = 0, @ErrorMessage = @ErrorMessage;
        
        SELECT @ResultId AS result_id, @EntityId AS entity_id, 'failed' AS status, @ErrorMessage AS error;
    END CATCH
END;
GO

-- Batch sync procedure
IF OBJECT_ID('sp_SyncBatchToFoodFinder') IS NOT NULL DROP PROCEDURE sp_SyncBatchToFoodFinder;
GO

CREATE PROCEDURE sp_SyncBatchToFoodFinder
    @BatchSize INT = 50
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ResultId INT;
    DECLARE @SyncedCount INT = 0;
    DECLARE @FailedCount INT = 0;
    
    -- Create temp table for pending results
    CREATE TABLE #PendingSync (
        result_id INT,
        entity_id VARCHAR(100)
    );
    
    -- Get pending results
    INSERT INTO #PendingSync (result_id, entity_id)
    SELECT TOP (@BatchSize)
        r.result_id,
        j.entity_id
    FROM scraping_results r
    INNER JOIN scraping_jobs j ON r.job_id = j.job_id
    WHERE r.sync_status = 'pending'
      AND r.validation_status IN ('valid', 'partial')
      AND r.structured_data IS NOT NULL
      AND j.entity_type = 'restaurant'
    ORDER BY r.extracted_at ASC;
    
    -- Process each result
    DECLARE sync_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT result_id FROM #PendingSync;
    
    OPEN sync_cursor;
    FETCH NEXT FROM sync_cursor INTO @ResultId;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            EXEC sp_SyncResultToFoodFinder @ResultId = @ResultId;
            SET @SyncedCount = @SyncedCount + 1;
        END TRY
        BEGIN CATCH
            SET @FailedCount = @FailedCount + 1;
        END CATCH
        
        FETCH NEXT FROM sync_cursor INTO @ResultId;
    END
    
    CLOSE sync_cursor;
    DEALLOCATE sync_cursor;
    
    DROP TABLE #PendingSync;
    
    SELECT 
        @SyncedCount AS synced_count,
        @FailedCount AS failed_count,
        @SyncedCount + @FailedCount AS total_processed;
END;
GO

-- =============================================================================
-- SECTION 3: SYNC STATISTICS
-- =============================================================================

-- Sync statistics view
IF OBJECT_ID('v_sync_statistics') IS NOT NULL DROP VIEW v_sync_statistics;
GO

CREATE VIEW v_sync_statistics AS
SELECT 
    'Sync Overview' AS metric_category,
    COUNT(*) AS total_results,
    SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) AS pending_sync,
    SUM(CASE WHEN sync_status = 'synced' THEN 1 ELSE 0 END) AS synced,
    SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) AS failed,
    MAX(synced_at) AS last_sync_time,
    AVG(CASE WHEN sync_status = 'synced' THEN DATEDIFF(MINUTE, extracted_at, synced_at) ELSE NULL END) AS avg_sync_delay_minutes
FROM scraping_results
WHERE result_type IN ('menu_data', 'structured_data');
GO

-- Get sync status report
IF OBJECT_ID('sp_GetSyncReport') IS NOT NULL DROP PROCEDURE sp_GetSyncReport;
GO

CREATE PROCEDURE sp_GetSyncReport
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Overall stats
    SELECT * FROM v_sync_statistics;
    
    -- Recent sync activity
    SELECT TOP 20
        r.result_id,
        j.entity_id,
        j.target_domain,
        r.record_count,
        r.sync_status,
        r.synced_at,
        r.sync_error,
        r.extracted_at
    FROM scraping_results r
    INNER JOIN scraping_jobs j ON r.job_id = j.job_id
    WHERE r.result_type IN ('menu_data', 'structured_data')
    ORDER BY r.extracted_at DESC;
    
    -- Failed syncs needing attention
    SELECT 
        r.result_id,
        j.entity_id,
        j.target_url,
        r.sync_error,
        r.extracted_at
    FROM scraping_results r
    INNER JOIN scraping_jobs j ON r.job_id = j.job_id
    WHERE r.sync_status = 'failed'
    ORDER BY r.extracted_at DESC;
END;
GO

-- =============================================================================
-- SECTION 4: HELPER PROCEDURES FOR PYTHON INTEGRATION
-- =============================================================================

-- Get extraction result data for Python sync
IF OBJECT_ID('sp_GetResultForSync') IS NOT NULL DROP PROCEDURE sp_GetResultForSync;
GO

CREATE PROCEDURE sp_GetResultForSync
    @ResultId INT
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        r.result_id,
        r.job_id,
        j.entity_type,
        j.entity_id,
        j.target_url,
        j.target_domain,
        r.result_type,
        r.structured_data,
        r.raw_data,
        r.record_count,
        r.confidence_score,
        r.extraction_method,
        r.extracted_at,
        j.items_extracted,
        j.items_with_prices,
        j.price_extraction_status,
        j.price_source,
        j.price_unavailable_reason
    FROM scraping_results r
    INNER JOIN scraping_jobs j ON r.job_id = j.job_id
    WHERE r.result_id = @ResultId;
END;
GO

-- =============================================================================
-- USAGE NOTES
-- =============================================================================

/*
SYNC METHODS:

1. SQL Server Job (recommended for production):
   - Schedule sp_SyncBatchToFoodFinder to run every few minutes
   - Handles batches of results automatically

2. Python integration:
   - Use sp_GetPendingSyncResults to get pending items
   - Process each result and call sp_MarkResultSynced
   - Good for complex transformations

3. Real-time sync:
   - Call sp_SyncResultToFoodFinder immediately after job completion
   - Add to sp_CompleteJob or call from Python

EXAMPLE USAGE:

-- Get pending results
EXEC sp_GetPendingSyncResults @BatchSize = 10;

-- Sync a batch
EXEC sp_SyncBatchToFoodFinder @BatchSize = 50;

-- Check sync status
EXEC sp_GetSyncReport;

-- Manual sync single result
EXEC sp_SyncResultToFoodFinder @ResultId = 123;

PYTHON EXAMPLE:

def sync_results_to_foodfinder():
    # Get pending results from CloudDestroyer
    pending = cursor.execute("EXEC sp_GetPendingSyncResults @BatchSize = 50").fetchall()
    
    for result in pending:
        try:
            # Transform data if needed
            menu_data = json.loads(result.structured_data)
            
            # Insert into FoodFinder
            foodfinder_cursor.execute(
                "EXEC sp_ImportMenuData @RestaurantId = ?, @MenuData = ?",
                result.entity_id, json.dumps(menu_data)
            )
            
            # Mark as synced in CloudDestroyer
            cursor.execute(
                "EXEC sp_MarkResultSynced @ResultId = ?, @Success = 1",
                result.result_id
            )
        except Exception as e:
            cursor.execute(
                "EXEC sp_MarkResultSynced @ResultId = ?, @Success = 0, @ErrorMessage = ?",
                result.result_id, str(e)
            )
*/

PRINT 'Sync procedures created successfully!';
GO


