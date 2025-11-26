-- FoodFinder Core Procedures Continued
-- Bulk menu operations and job processing

USE FoodFinder;
GO

-- =============================================================================
-- BULK MENU DATA PROCEDURES
-- =============================================================================

-- Efficiently insert menu items from scraping results
CREATE PROCEDURE sp_BulkInsertMenuItems
    @RestaurantId VARCHAR(50),
    @MenuData NVARCHAR(MAX), -- JSON array of menu items
    @Source VARCHAR(20) = 'scraped'
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Validate JSON format
        IF ISJSON(@MenuData) = 0
            RAISERROR('Invalid JSON format for menu data.', 16, 1);
            
        -- Verify restaurant exists
        IF NOT EXISTS(SELECT 1 FROM restaurants WHERE restaurant_id = @RestaurantId)
            RAISERROR('Restaurant not found: %s', 16, 1, @RestaurantId);
        
        DECLARE @ItemsProcessed INT = 0;
        DECLARE @CategoriesCreated INT = 0;
        
        -- Create temporary table for parsed data
        CREATE TABLE #MenuItems (
            category_name NVARCHAR(100),
            item_name NVARCHAR(255),
            description NVARCHAR(MAX),
            price DECIMAL(8,2),
            normalized_name NVARCHAR(255)
        );
        
        -- Parse JSON and insert into temp table
        INSERT INTO #MenuItems (category_name, item_name, description, price, normalized_name)
        SELECT 
            ISNULL(JSON_VALUE(value, '$.category'), 'Main Menu') as category_name,
            JSON_VALUE(value, '$.name') as item_name,
            JSON_VALUE(value, '$.description') as description,
            TRY_CAST(JSON_VALUE(value, '$.price') AS DECIMAL(8,2)) as price,
            LOWER(LTRIM(RTRIM(REPLACE(REPLACE(JSON_VALUE(value, '$.name'), '''', ''), '"', '')))) as normalized_name
        FROM OPENJSON(@MenuData)
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL;
        
        -- Insert/update categories first
        MERGE menu_categories AS target
        USING (
            SELECT DISTINCT 
                @RestaurantId as restaurant_id,
                category_name,
                @Source as source,
                ROW_NUMBER() OVER (ORDER BY category_name) as display_order
            FROM #MenuItems
        ) AS source ON target.restaurant_id = source.restaurant_id 
                   AND target.category_name = source.category_name
        WHEN NOT MATCHED THEN
            INSERT (restaurant_id, category_name, display_order, source)
            VALUES (source.restaurant_id, source.category_name, source.display_order, source.source);
            
        SET @CategoriesCreated = @@ROWCOUNT;
        
        -- Insert menu items with duplicate detection
        INSERT INTO menu_items (category_id, name, description, price, normalized_name, is_available)
        SELECT DISTINCT
            mc.category_id,
            mi.item_name,
            mi.description,
            mi.price,
            mi.normalized_name,
            1
        FROM #MenuItems mi
        INNER JOIN menu_categories mc ON mc.restaurant_id = @RestaurantId 
                                     AND mc.category_name = mi.category_name
        WHERE NOT EXISTS (
            SELECT 1 FROM menu_items existing
            WHERE existing.category_id = mc.category_id
            AND existing.normalized_name = mi.normalized_name
        );
        
        SET @ItemsProcessed = @@ROWCOUNT;
        
        -- Update restaurant scrape status
        UPDATE restaurants 
        SET last_scraped_at = GETDATE(),
            scrape_status = 'completed',
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
        -- Return summary
        SELECT 
            @RestaurantId as restaurant_id,
            @ItemsProcessed as items_inserted,
            @CategoriesCreated as categories_created,
            (SELECT COUNT(*) FROM menu_categories mc 
             INNER JOIN menu_items mi ON mc.category_id = mi.category_id 
             WHERE mc.restaurant_id = @RestaurantId) as total_menu_items;
        
        DROP TABLE #MenuItems;
        
    END TRY
    BEGIN CATCH
        IF OBJECT_ID('tempdb..#MenuItems') IS NOT NULL
            DROP TABLE #MenuItems;
            
        -- Update restaurant with failed status
        UPDATE restaurants 
        SET scrape_status = 'failed',
            last_scraped_at = GETDATE(),
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Remove outdated menu data and manage retention
CREATE PROCEDURE sp_CleanupStaleMenuData
    @RetentionDays INT = 90,
    @DryRun BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        DECLARE @CutoffDate DATETIME2 = DATEADD(DAY, -@RetentionDays, GETDATE());
        DECLARE @ItemsDeleted INT = 0;
        DECLARE @CategoriesDeleted INT = 0;
        DECLARE @RestaurantsAffected INT = 0;
        
        -- Find items to delete
        CREATE TABLE #ItemsToDelete (
            item_id INT,
            category_id INT,
            restaurant_id VARCHAR(50)
        );
        
        INSERT INTO #ItemsToDelete
        SELECT mi.item_id, mi.category_id, mc.restaurant_id
        FROM menu_items mi
        INNER JOIN menu_categories mc ON mi.category_id = mc.category_id
        INNER JOIN restaurants r ON mc.restaurant_id = r.restaurant_id
        WHERE mi.created_at < @CutoffDate
        OR (r.last_scraped_at < DATEADD(DAY, -30, GETDATE()) AND r.scrape_status = 'failed');
        
        IF @DryRun = 1
        BEGIN
            -- Return what would be deleted
            SELECT 
                COUNT(*) as items_to_delete,
                COUNT(DISTINCT category_id) as categories_affected,
                COUNT(DISTINCT restaurant_id) as restaurants_affected
            FROM #ItemsToDelete;
            
            SELECT TOP 100
                r.name as restaurant_name,
                mc.category_name,
                mi.name as item_name,
                mi.created_at
            FROM #ItemsToDelete itd
            INNER JOIN menu_items mi ON itd.item_id = mi.item_id
            INNER JOIN menu_categories mc ON itd.category_id = mc.category_id
            INNER JOIN restaurants r ON itd.restaurant_id = r.restaurant_id
            ORDER BY mi.created_at;
        END
        ELSE
        BEGIN
            -- Delete menu item aliases first
            DELETE mia
            FROM menu_item_aliases mia
            INNER JOIN #ItemsToDelete itd ON mia.item_id = itd.item_id;
            
            -- Delete menu items
            DELETE mi
            FROM menu_items mi
            INNER JOIN #ItemsToDelete itd ON mi.item_id = itd.item_id;
            
            SET @ItemsDeleted = @@ROWCOUNT;
            
            -- Delete empty categories
            DELETE mc
            FROM menu_categories mc
            LEFT JOIN menu_items mi ON mc.category_id = mi.category_id
            WHERE mi.category_id IS NULL;
            
            SET @CategoriesDeleted = @@ROWCOUNT;
            
            -- Count affected restaurants
            SELECT @RestaurantsAffected = COUNT(DISTINCT restaurant_id) FROM #ItemsToDelete;
            
            -- Return cleanup summary
            SELECT 
                @ItemsDeleted as items_deleted,
                @CategoriesDeleted as categories_deleted,
                @RestaurantsAffected as restaurants_affected,
                @CutoffDate as cutoff_date,
                GETDATE() as cleanup_completed;
        END
        
        DROP TABLE #ItemsToDelete;
        
    END TRY
    BEGIN CATCH
        IF OBJECT_ID('tempdb..#ItemsToDelete') IS NOT NULL
            DROP TABLE #ItemsToDelete;
            
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- =============================================================================
-- JOB PROCESSING PROCEDURES
-- =============================================================================

-- Manage scraping job queue with intelligent prioritization
CREATE PROCEDURE sp_ProcessScrapingQueue
    @WorkerId VARCHAR(100),
    @MaxJobs INT = 5,
    @JobType VARCHAR(30) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Select jobs to process based on priority and availability
        CREATE TABLE #SelectedJobs (job_id INT);
        
        INSERT INTO #SelectedJobs (job_id)
        SELECT TOP (@MaxJobs) job_id
        FROM scraping_jobs
        WHERE status = 'pending'
        AND (next_retry_at IS NULL OR next_retry_at <= GETDATE())
        AND (@JobType IS NULL OR job_type = @JobType)
        AND attempts < max_retries
        ORDER BY priority DESC, scheduled_at ASC;
        
        -- Update selected jobs to running status
        UPDATE sj
        SET status = 'running',
            started_at = GETDATE(),
            worker_id = @WorkerId
        FROM scraping_jobs sj
        INNER JOIN #SelectedJobs sjs ON sj.job_id = sjs.job_id;
        
        -- Return job details for processing
        SELECT 
            sj.job_id,
            sj.restaurant_id,
            sj.job_type,
            sj.priority,
            sj.attempts,
            sj.max_retries,
            r.name as restaurant_name,
            r.website,
            r.menu_url,
            cc.scraper_config,
            cc.menu_endpoints,
            cc.custom_selectors
        FROM scraping_jobs sj
        INNER JOIN #SelectedJobs sjs ON sj.job_id = sjs.job_id
        INNER JOIN restaurants r ON sj.restaurant_id = r.restaurant_id
        LEFT JOIN chain_configs cc ON r.chain_name = cc.chain_name
        ORDER BY sj.priority DESC, sj.scheduled_at ASC;
        
        DROP TABLE #SelectedJobs;
        
    END TRY
    BEGIN CATCH
        IF OBJECT_ID('tempdb..#SelectedJobs') IS NOT NULL
            DROP TABLE #SelectedJobs;
            
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Complete or fail a scraping job
CREATE PROCEDURE sp_CompleteScrapingJob
    @JobId INT,
    @Status VARCHAR(20), -- 'completed', 'failed', 'blocked'
    @ItemsFound INT = 0,
    @CategoriesFound INT = 0,
    @ErrorMessage NVARCHAR(MAX) = NULL,
    @ErrorCode VARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        DECLARE @ProcessingTime INT;
        
        -- Calculate processing time
        SELECT @ProcessingTime = DATEDIFF(MILLISECOND, started_at, GETDATE())
        FROM scraping_jobs
        WHERE job_id = @JobId;
        
        -- Update job with completion details
        UPDATE scraping_jobs
        SET status = @Status,
            completed_at = GETDATE(),
            items_found = @ItemsFound,
            categories_found = @CategoriesFound,
            processing_time_ms = @ProcessingTime,
            last_error_message = @ErrorMessage,
            error_code = @ErrorCode,
            attempts = attempts + 1
        WHERE job_id = @JobId;
        
        -- Schedule retry if failed and within retry limit
        IF @Status = 'failed'
        BEGIN
            DECLARE @Attempts INT, @MaxRetries INT;
            
            SELECT @Attempts = attempts, @MaxRetries = max_retries
            FROM scraping_jobs
            WHERE job_id = @JobId;
            
            IF @Attempts < @MaxRetries
            BEGIN
                -- Exponential backoff: 5 min, 15 min, 45 min
                DECLARE @RetryDelayMinutes INT = POWER(3, @Attempts) * 5;
                
                UPDATE scraping_jobs
                SET status = 'pending',
                    next_retry_at = DATEADD(MINUTE, @RetryDelayMinutes, GETDATE()),
                    started_at = NULL,
                    worker_id = NULL
                WHERE job_id = @JobId;
            END
        END
        
        -- Return job summary
        SELECT 
            job_id,
            restaurant_id,
            status,
            items_found,
            categories_found,
            processing_time_ms,
            attempts,
            max_retries,
            next_retry_at
        FROM scraping_jobs
        WHERE job_id = @JobId;
        
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage2 NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage2, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Track search queries and update analytics
CREATE PROCEDURE sp_UpdateSearchAnalytics
    @QueryText NVARCHAR(255),
    @NormalizedQuery NVARCHAR(255),
    @Latitude DECIMAL(10,8),
    @Longitude DECIMAL(11,8),
    @ExecutionTimeMs INT,
    @ResultsFound INT,
    @CacheHit BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Update popular searches with decay scoring
        MERGE popular_searches AS target
        USING (VALUES (@NormalizedQuery)) AS source (search_term)
        ON target.search_term = source.search_term
        WHEN MATCHED THEN
            UPDATE SET 
                search_count = search_count + 1,
                last_searched = GETDATE(),
                decay_score = CASE 
                    WHEN DATEDIFF(HOUR, last_searched, GETDATE()) > 24 
                    THEN decay_score * 0.9 + 1.0
                    ELSE decay_score + 0.1
                END
        WHEN NOT MATCHED THEN
            INSERT (search_term, search_count, last_searched, last_seen_at, decay_score)
            VALUES (source.search_term, 1, GETDATE(), GETDATE(), 1.0);
        
        -- Update location analytics (simplified grid-based approach)
        DECLARE @GridLat DECIMAL(8,6) = ROUND(@Latitude, 3); -- ~100m precision
        DECLARE @GridLng DECIMAL(9,6) = ROUND(@Longitude, 3);
        
        MERGE location_analytics AS target
        USING (VALUES (@GridLat, @GridLng)) AS source (lat, lng)
        ON ABS(target.latitude_center - source.lat) < 0.001 
           AND ABS(target.longitude_center - source.lng) < 0.001
        WHEN MATCHED THEN
            UPDATE SET 
                total_searches = total_searches + 1,
                last_updated = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (latitude_center, longitude_center, total_searches, unique_users, last_updated)
            VALUES (source.lat, source.lng, 1, 1, GETDATE());
        
    END TRY
    BEGIN CATCH
        -- Don't fail the main operation if analytics update fails
        -- Just log the error silently
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        PRINT 'Analytics update failed: ' + @ErrorMessage;
    END CATCH
END;
GO