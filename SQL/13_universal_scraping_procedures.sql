-- Universal Scraping Procedures
-- Comprehensive job management for the universal scraping queue system
-- Procedures prefixed with spsc_ (Scraping Control)

USE FoodFinder;
GO

-- =============================================================================
-- UNIVERSAL SCRAPING QUEUE PROCEDURES
-- =============================================================================

-- Create a new scraping job (generic for any scraping task)
CREATE PROCEDURE spsc_CreateJob
    @JobType VARCHAR(50),
    @TargetUrl VARCHAR(1000),
    @JobName VARCHAR(255) = NULL,
    @EntityType VARCHAR(50) = NULL,
    @EntityId VARCHAR(100) = NULL,
    @Priority INT = 50,
    @ScrapingConfig NVARCHAR(MAX) = NULL,
    @BatchId VARCHAR(100) = NULL,
    @SessionId VARCHAR(100) = NULL,
    @JobId INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Validate inputs
        IF @JobType IS NULL OR @TargetUrl IS NULL
        BEGIN
            RAISERROR('JobType and TargetUrl are required', 16, 1);
            RETURN;
        END
        
        -- Extract domain from URL
        DECLARE @Domain VARCHAR(255);
        SET @Domain = CASE 
            WHEN CHARINDEX('://', @TargetUrl) > 0 THEN
                SUBSTRING(@TargetUrl, CHARINDEX('://', @TargetUrl) + 3, 
                         CHARINDEX('/', @TargetUrl + '/', CHARINDEX('://', @TargetUrl) + 3) - CHARINDEX('://', @TargetUrl) - 3)
            ELSE @TargetUrl
        END;
        
        -- Generate job name if not provided
        IF @JobName IS NULL
        BEGIN
            SET @JobName = @JobType + ' - ' + @Domain;
        END
        
        -- Check for duplicate active jobs
        IF EXISTS (
            SELECT 1 FROM universal_scraping_jobs 
            WHERE job_type = @JobType 
            AND target_url = @TargetUrl 
            AND status IN ('pending', 'running')
        )
        BEGIN
            -- Return existing job ID
            SELECT @JobId = job_id 
            FROM universal_scraping_jobs 
            WHERE job_type = @JobType 
            AND target_url = @TargetUrl 
            AND status IN ('pending', 'running');
            
            RETURN; -- Job already exists
        END
        
        -- Create new job
        INSERT INTO universal_scraping_jobs (
            job_type, job_name, target_url, target_domain,
            entity_type, entity_id, priority, scraping_config,
            batch_id, session_id, created_at
        )
        VALUES (
            @JobType, @JobName, @TargetUrl, @Domain,
            @EntityType, @EntityId, @Priority, @ScrapingConfig,
            @BatchId, @SessionId, GETDATE()
        );
        
        SET @JobId = SCOPE_IDENTITY();
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- Get next job from queue for worker
CREATE PROCEDURE spsc_GetNextJob
    @WorkerId VARCHAR(100),
    @WorkerType VARCHAR(50),
    @SupportedJobTypes VARCHAR(500) = NULL -- Comma-separated list
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @JobId INT = NULL;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Update worker heartbeat
        UPDATE scraping_workers
        SET last_heartbeat = GETDATE(),
            current_jobs = current_jobs + 1
        WHERE worker_id = @WorkerId;
        
        -- If worker doesn't exist, create it
        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO scraping_workers (
                worker_id, worker_name, worker_type, 
                supported_job_types, last_heartbeat, current_jobs
            )
            VALUES (
                @WorkerId, @WorkerId, @WorkerType,
                CASE WHEN @SupportedJobTypes IS NOT NULL 
                     THEN '["' + REPLACE(@SupportedJobTypes, ',', '","') + '"]' 
                     ELSE NULL END,
                GETDATE(), 1
            );
        END
        
        -- Find highest priority job
        SELECT TOP 1 @JobId = job_id
        FROM universal_scraping_jobs
        WHERE status = 'pending'
        AND (earliest_start_at IS NULL OR earliest_start_at <= GETDATE())
        AND (next_retry_at IS NULL OR next_retry_at <= GETDATE())
        AND (
            @SupportedJobTypes IS NULL 
            OR job_type IN (SELECT TRIM(value) FROM STRING_SPLIT(@SupportedJobTypes, ','))
        )
        ORDER BY priority DESC, created_at ASC;
        
        -- Claim the job
        IF @JobId IS NOT NULL
        BEGIN
            UPDATE universal_scraping_jobs
            SET status = 'running',
                worker_id = @WorkerId,
                worker_type = @WorkerType,
                started_at = GETDATE(),
                attempts = attempts + 1
            WHERE job_id = @JobId;
            
            -- Create history entry
            INSERT INTO scraping_job_history (
                job_id, execution_attempt, worker_id, started_at, status
            )
            VALUES (
                @JobId, (SELECT attempts FROM universal_scraping_jobs WHERE job_id = @JobId), 
                @WorkerId, GETDATE(), 'running'
            );
            
            -- Return job details
            SELECT 
                j.job_id,
                j.job_type,
                j.job_name,
                j.target_url,
                j.target_domain,
                j.entity_type,
                j.entity_id,
                j.scraping_config,
                j.extraction_rules,
                j.priority,
                j.attempts,
                j.max_retries,
                j.estimated_duration_seconds,
                j.batch_id,
                j.session_id,
                t.default_config,
                t.extraction_rules as template_rules
            FROM universal_scraping_jobs j
            LEFT JOIN scraping_job_templates t ON j.job_type = t.job_type AND t.is_active = 1
            WHERE j.job_id = @JobId;
        END
        
        COMMIT TRANSACTION;
        
    END TRY
    BEGIN CATCH
        IF XACT_STATE() != 0
            ROLLBACK TRANSACTION;
            
        -- Reset worker job count on error
        UPDATE scraping_workers
        SET current_jobs = current_jobs - 1
        WHERE worker_id = @WorkerId;
        
        THROW;
    END CATCH
END;
GO

-- Complete scraping job with results
CREATE PROCEDURE spsc_CompleteJob
    @JobId INT,
    @Status VARCHAR(20),
    @ItemsExtracted INT = 0,
    @ProcessingTimeSeconds DECIMAL(8,2) = 0,
    @ErrorMessage NVARCHAR(MAX) = NULL,
    @ErrorCode VARCHAR(100) = NULL,
    @RawData NVARCHAR(MAX) = NULL,
    @StructuredData NVARCHAR(MAX) = NULL,
    @ConfidenceScore DECIMAL(3,2) = 1.0
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        DECLARE @WorkerId VARCHAR(100);
        DECLARE @ShouldRetry BIT = 0;
        DECLARE @NextRetryAt DATETIME2 = NULL;
        
        -- Get job details
        SELECT @WorkerId = worker_id
        FROM universal_scraping_jobs
        WHERE job_id = @JobId;
        
        -- Determine retry logic
        IF @Status IN ('failed', 'blocked')
        BEGIN
            DECLARE @Attempts INT, @MaxRetries INT, @RetryDelayMinutes INT;
            
            SELECT @Attempts = attempts, @MaxRetries = max_retries, @RetryDelayMinutes = retry_delay_minutes
            FROM universal_scraping_jobs
            WHERE job_id = @JobId;
            
            IF @Attempts < @MaxRetries
            BEGIN
                SET @ShouldRetry = 1;
                SET @Status = 'retry';
                SET @NextRetryAt = DATEADD(MINUTE, @RetryDelayMinutes * POWER(2, @Attempts - 1), GETDATE());
            END
        END
        
        -- Update job
        UPDATE universal_scraping_jobs
        SET status = @Status,
            items_extracted = @ItemsExtracted,
            actual_duration_seconds = @ProcessingTimeSeconds,
            last_error_message = @ErrorMessage,
            error_code = @ErrorCode,
            completed_at = CASE WHEN @Status IN ('completed', 'failed', 'cancelled') THEN GETDATE() ELSE NULL END,
            next_retry_at = @NextRetryAt,
            data_quality_score = CASE WHEN @Status = 'completed' THEN CAST(@ConfidenceScore * 100 AS INT) ELSE 0 END
        WHERE job_id = @JobId;
        
        -- Create result record if we have data
        IF (@RawData IS NOT NULL OR @StructuredData IS NOT NULL) AND @Status = 'completed'
        BEGIN
            DECLARE @ResultType VARCHAR(50) = 'extracted_data';
            DECLARE @RecordCount INT = @ItemsExtracted;
            
            -- Determine result type based on job type
            SELECT @ResultType = CASE 
                WHEN job_type LIKE '%menu%' THEN 'menu_data'
                WHEN job_type LIKE '%api%' THEN 'api_response'
                WHEN job_type LIKE '%content%' THEN 'html_content'
                ELSE 'extracted_data'
            END
            FROM universal_scraping_jobs
            WHERE job_id = @JobId;
            
            INSERT INTO universal_scraping_results (
                job_id, result_type, confidence_score, 
                raw_data, structured_data, data_size_bytes,
                record_count, processing_time_seconds, extracted_at
            )
            VALUES (
                @JobId, @ResultType, @ConfidenceScore,
                @RawData, @StructuredData, LEN(ISNULL(@RawData, '') + ISNULL(@StructuredData, '')),
                @RecordCount, @ProcessingTimeSeconds, GETDATE()
            );
        END
        
        -- Update job history
        UPDATE scraping_job_history
        SET completed_at = GETDATE(),
            duration_seconds = @ProcessingTimeSeconds,
            status = @Status,
            items_found = @ItemsExtracted,
            error_message = @ErrorMessage
        WHERE job_id = @JobId 
        AND completed_at IS NULL
        AND worker_id = @WorkerId;
        
        -- Update worker statistics
        UPDATE scraping_workers
        SET current_jobs = current_jobs - 1,
            last_heartbeat = GETDATE()
        WHERE worker_id = @WorkerId;
        
        -- Return completion status
        SELECT 
            @JobId as job_id,
            @Status as final_status,
            @ItemsExtracted as items_extracted,
            @ShouldRetry as will_retry,
            @NextRetryAt as next_retry_at;
        
    END TRY
    BEGIN CATCH
        -- Reset worker job count on error
        UPDATE scraping_workers
        SET current_jobs = current_jobs - 1
        WHERE worker_id = @WorkerId;
        
        THROW;
    END CATCH
END;
GO

-- CloudDestroyer specific job creation (wrapper for restaurant menu extraction)
CREATE PROCEDURE spcd_CreateRestaurantJob
    @RestaurantId VARCHAR(50),
    @TargetUrl VARCHAR(1000) = NULL,
    @Priority INT = 70, -- Higher priority for restaurant jobs
    @SessionId VARCHAR(100) = NULL,
    @JobId INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Validate restaurant exists
        IF NOT EXISTS (SELECT 1 FROM restaurants WHERE restaurant_id = @RestaurantId)
        BEGIN
            RAISERROR('Restaurant not found: %s', 16, 1, @RestaurantId);
            RETURN;
        END
        
        -- Get restaurant details
        DECLARE @RestaurantName VARCHAR(255);
        DECLARE @Website VARCHAR(500);
        
        SELECT @RestaurantName = name, @Website = ISNULL(@TargetUrl, ISNULL(menu_url, website))
        FROM restaurants 
        WHERE restaurant_id = @RestaurantId;
        
        IF @Website IS NULL
        BEGIN
            RAISERROR('No website URL found for restaurant: %s', 16, 1, @RestaurantId);
            RETURN;
        END
        
        -- Create CloudDestroyer configuration
        DECLARE @Config NVARCHAR(MAX) = '{
            "extraction_type": "restaurant_menu",
            "use_selenium": "auto",
            "bypass_cloudflare": true,
            "discover_api_endpoints": true,
            "parse_spa": true
        }';
        
        -- Create the job
        EXEC spsc_CreateJob
            @JobType = 'clouddestroyer_menu',
            @TargetUrl = @Website,
            @JobName = 'Extract Menu: ' + @RestaurantName,
            @EntityType = 'restaurant',
            @EntityId = @RestaurantId,
            @Priority = @Priority,
            @ScrapingConfig = @Config,
            @SessionId = @SessionId,
            @JobId = @JobId OUTPUT;
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- Process CloudDestroyer results into menu tables
CREATE PROCEDURE spcd_ProcessMenuResult
    @JobId INT,
    @MenuData NVARCHAR(MAX) -- JSON data from CloudDestroyer (like Bubba's 33 format)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ItemsInserted INT = 0;
    DECLARE @CategoriesCreated INT = 0;
    DECLARE @RestaurantId VARCHAR(50);
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Get restaurant ID from job
        SELECT @RestaurantId = entity_id
        FROM universal_scraping_jobs
        WHERE job_id = @JobId AND entity_type = 'restaurant';
        
        IF @RestaurantId IS NULL
        BEGIN
            RAISERROR('Invalid job or restaurant not found', 16, 1);
            RETURN;
        END
        
        -- Create temporary tables for processing
        CREATE TABLE #TempCategories (
            CategoryName NVARCHAR(100),
            Description NVARCHAR(MAX),
            DisplayOrder INT,
            ExternalId VARCHAR(100)
        );
        
        CREATE TABLE #TempMenuItems (
            CategoryName NVARCHAR(100),
            ItemName NVARCHAR(255),
            Description NVARCHAR(MAX),
            Price DECIMAL(8,2),
            ExternalId VARCHAR(100),
            Confidence INT
        );
        
        -- Parse categories from CloudDestroyer JSON (handles Bubba's 33 structure)
        INSERT INTO #TempCategories (CategoryName, Description, DisplayOrder, ExternalId)
        SELECT 
            JSON_VALUE(value, '$.name'),
            JSON_VALUE(value, '$.description'),
            ISNULL(CAST(JSON_VALUE(value, '$.display_order') AS INT), 0),
            JSON_VALUE(value, '$.id')
        FROM OPENJSON(@MenuData, '$.categories')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL;
        
        -- Parse menu items from nested structure (Bubba's 33 format)
        INSERT INTO #TempMenuItems (CategoryName, ItemName, Description, Price, ExternalId, Confidence)
        SELECT 
            JSON_VALUE(cat_val, '$.name') as CategoryName,
            JSON_VALUE(item_val, '$.name') as ItemName,
            JSON_VALUE(item_val, '$.description') as Description,
            CAST(ISNULL(JSON_VALUE(item_val, '$.base_price'), JSON_VALUE(item_val, '$.price'), '0') AS DECIMAL(8,2)) as Price,
            JSON_VALUE(item_val, '$.id') as ExternalId,
            90 as Confidence -- High confidence for API data
        FROM OPENJSON(@MenuData, '$.categories')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL
        
        UNION ALL
        
        -- Handle direct items array (alternative structure)
        SELECT 
            ISNULL(JSON_VALUE(value, '$.category'), 'Menu Items') as CategoryName,
            JSON_VALUE(value, '$.name') as ItemName,
            JSON_VALUE(value, '$.description') as Description,
            CAST(ISNULL(JSON_VALUE(value, '$.price'), JSON_VALUE(value, '$.base_price'), '0') AS DECIMAL(8,2)) as Price,
            JSON_VALUE(value, '$.id') as ExternalId,
            85 as Confidence -- Good confidence for direct extraction
        FROM OPENJSON(@MenuData, '$.all_items')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL;
        
        -- Insert categories
        INSERT INTO menu_categories (restaurant_id, name, description, display_order, source, external_category_id)
        SELECT DISTINCT
            @RestaurantId,
            tc.CategoryName,
            tc.Description,
            tc.DisplayOrder,
            'scraped',
            tc.ExternalId
        FROM #TempCategories tc
        WHERE tc.CategoryName IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM menu_categories mc 
            WHERE mc.restaurant_id = @RestaurantId 
            AND mc.name = tc.CategoryName
        );
        
        SET @CategoriesCreated = @@ROWCOUNT;
        
        -- Insert menu items
        INSERT INTO menu_items (
            restaurant_id, category_id, name, normalized_name, description, 
            price, external_item_id, source, confidence_score, 
            search_tokens, is_available
        )
        SELECT 
            @RestaurantId,
            mc.category_id,
            tm.ItemName,
            LOWER(REPLACE(REPLACE(REPLACE(tm.ItemName, ' ', ''), '''', ''), '"', '')),
            tm.Description,
            NULLIF(tm.Price, 0), -- Only store non-zero prices
            tm.ExternalId,
            'scraped',
            tm.Confidence,
            LOWER(tm.ItemName + ' ' + ISNULL(tm.Description, '')),
            1
        FROM #TempMenuItems tm
        LEFT JOIN menu_categories mc ON mc.restaurant_id = @RestaurantId AND mc.name = tm.CategoryName
        WHERE tm.ItemName IS NOT NULL
        AND LEN(tm.ItemName) > 2
        AND NOT EXISTS (
            SELECT 1 FROM menu_items mi 
            WHERE mi.restaurant_id = @RestaurantId 
            AND (mi.name = tm.ItemName OR mi.external_item_id = tm.ExternalId)
        );
        
        SET @ItemsInserted = @@ROWCOUNT;
        
        -- Update restaurant status
        UPDATE restaurants 
        SET scrape_status = CASE 
                WHEN @ItemsInserted > 0 THEN 'success'
                ELSE 'no_menu'
            END,
            last_scraped_at = GETDATE(),
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
        -- Clean up temp tables
        DROP TABLE #TempCategories;
        DROP TABLE #TempMenuItems;
        
        COMMIT TRANSACTION;
        
        -- Return summary
        SELECT 
            @RestaurantId AS restaurant_id,
            @ItemsInserted AS items_inserted,
            @CategoriesCreated AS categories_created,
            'success' AS status;
        
    END TRY
    BEGIN CATCH
        IF XACT_STATE() != 0
            ROLLBACK TRANSACTION;
            
        IF OBJECT_ID('tempdb..#TempCategories') IS NOT NULL
            DROP TABLE #TempCategories;
        IF OBJECT_ID('tempdb..#TempMenuItems') IS NOT NULL
            DROP TABLE #TempMenuItems;
        
        THROW;
    END CATCH
END;
GO

-- Batch create restaurant extraction jobs
CREATE PROCEDURE spcd_CreateBatchRestaurantJobs
    @RestaurantIds NVARCHAR(MAX), -- JSON array of restaurant IDs
    @SessionId VARCHAR(100),
    @Priority INT = 70
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @JobsCreated INT = 0;
    
    BEGIN TRY
        -- Create jobs for each restaurant
        DECLARE @JobId INT;
        
        DECLARE rest_cursor CURSOR FOR
        SELECT TRIM('"' FROM value) as restaurant_id
        FROM OPENJSON(@RestaurantIds)
        WHERE TRIM('"' FROM value) IS NOT NULL;
        
        DECLARE @CurrentRestaurantId VARCHAR(50);
        
        OPEN rest_cursor;
        FETCH NEXT FROM rest_cursor INTO @CurrentRestaurantId;
        
        WHILE @@FETCH_STATUS = 0
        BEGIN
            BEGIN TRY
                EXEC spcd_CreateRestaurantJob 
                    @RestaurantId = @CurrentRestaurantId,
                    @Priority = @Priority,
                    @SessionId = @SessionId,
                    @JobId = @JobId OUTPUT;
                
                IF @JobId IS NOT NULL
                    SET @JobsCreated = @JobsCreated + 1;
                
            END TRY
            BEGIN CATCH
                -- Log error but continue with other restaurants
                PRINT 'Error creating job for restaurant: ' + @CurrentRestaurantId + ' - ' + ERROR_MESSAGE();
            END CATCH
            
            FETCH NEXT FROM rest_cursor INTO @CurrentRestaurantId;
        END
        
        CLOSE rest_cursor;
        DEALLOCATE rest_cursor;
        
        SELECT @JobsCreated AS jobs_created;
        
    END TRY
    BEGIN CATCH
        IF CURSOR_STATUS('global', 'rest_cursor') >= 0
        BEGIN
            CLOSE rest_cursor;
            DEALLOCATE rest_cursor;
        END
        
        THROW;
    END CATCH
END;
GO

-- Get queue statistics
CREATE PROCEDURE spsc_GetQueueStats
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        'Queue Overview' as metric_category,
        COUNT(*) as total_jobs,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_jobs,
        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_jobs,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
        AVG(CAST(priority AS FLOAT)) as avg_priority,
        AVG(CAST(actual_duration_seconds AS FLOAT)) as avg_duration_seconds
    FROM universal_scraping_jobs
    WHERE created_at >= DATEADD(DAY, -7, GETDATE())
    
    UNION ALL
    
    SELECT 
        'By Job Type' as metric_category,
        COUNT(*) as total_jobs,
        0, 0, 0, 0, 0, 0 -- Placeholders
    FROM universal_scraping_jobs
    WHERE created_at >= DATEADD(DAY, -7, GETDATE())
    GROUP BY job_type;
    
    -- Worker statistics
    SELECT 
        w.worker_id,
        w.worker_type,
        w.status,
        w.current_jobs,
        w.last_heartbeat,
        COUNT(j.job_id) as jobs_processed_today,
        AVG(CAST(j.actual_duration_seconds AS FLOAT)) as avg_processing_time
    FROM scraping_workers w
    LEFT JOIN universal_scraping_jobs j ON w.worker_id = j.worker_id 
        AND j.completed_at >= CAST(GETDATE() AS DATE)
    GROUP BY w.worker_id, w.worker_type, w.status, w.current_jobs, w.last_heartbeat;
END;
GO