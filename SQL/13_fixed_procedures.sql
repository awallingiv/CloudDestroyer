-- SQL Server Compatible Universal Scraping Procedures
-- Fixed for SQL Server 2016+ compatibility

USE FoodFinder;
GO

-- Drop existing procedures that may have failed
IF OBJECT_ID('spcd_CreateRestaurantJob') IS NOT NULL DROP PROCEDURE spcd_CreateRestaurantJob;
IF OBJECT_ID('spcd_ProcessMenuResult') IS NOT NULL DROP PROCEDURE spcd_ProcessMenuResult;
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
        
        -- Create CloudDestroyer configuration (manual JSON string)
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
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Process CloudDestroyer results into menu tables (simplified)
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
        
        -- Simple category extraction (parse top-level categories)
        INSERT INTO menu_categories (restaurant_id, name, description, display_order, source, external_category_id)
        SELECT DISTINCT
            @RestaurantId,
            JSON_VALUE(value, '$.name'),
            JSON_VALUE(value, '$.description'),
            0,
            'scraped',
            JSON_VALUE(value, '$.id')
        FROM OPENJSON(@MenuData, '$.categories')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM menu_categories mc 
            WHERE mc.restaurant_id = @RestaurantId 
            AND mc.name = JSON_VALUE(value, '$.name')
        );
        
        SET @CategoriesCreated = @@ROWCOUNT;
        
        -- Simple item extraction from all_items array (like Bubba's 33 format)
        INSERT INTO menu_items (
            restaurant_id, category_id, name, normalized_name, description, 
            price, external_item_id, source, confidence_score, 
            search_tokens, is_available
        )
        SELECT 
            @RestaurantId,
            mc.category_id,
            JSON_VALUE(value, '$.name'),
            LOWER(REPLACE(JSON_VALUE(value, '$.name'), ' ', '')),
            JSON_VALUE(value, '$.description'),
            CASE WHEN ISNUMERIC(JSON_VALUE(value, '$.base_price')) = 1 
                 THEN CAST(JSON_VALUE(value, '$.base_price') AS DECIMAL(8,2)) 
                 ELSE NULL END,
            JSON_VALUE(value, '$.id'),
            'scraped',
            90,
            LOWER(JSON_VALUE(value, '$.name') + ' ' + ISNULL(JSON_VALUE(value, '$.description'), '')),
            1
        FROM OPENJSON(@MenuData, '$.all_items')
        LEFT JOIN menu_categories mc ON mc.restaurant_id = @RestaurantId 
            AND mc.name = JSON_VALUE(value, '$.category')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL
        AND LEN(JSON_VALUE(value, '$.name')) > 2
        AND NOT EXISTS (
            SELECT 1 FROM menu_items mi 
            WHERE mi.restaurant_id = @RestaurantId 
            AND mi.name = JSON_VALUE(value, '$.name')
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
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY(); 
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

PRINT 'Fixed CloudDestroyer procedures created successfully!';
GO