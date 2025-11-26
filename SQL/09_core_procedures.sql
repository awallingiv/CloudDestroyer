-- FoodFinder Core Stored Procedures - Phase 1
-- Critical procedures for search, data management, and job processing
-- Compatible with: Microsoft SQL Server 2016+

USE FoodFinder;
GO

-- =============================================================================
-- SEARCH FUNCTIONALITY PROCEDURES
-- =============================================================================

-- High-performance menu search with location filtering and caching
CREATE PROCEDURE sp_SearchMenuItems
    @SearchQuery NVARCHAR(255),
    @Latitude DECIMAL(10,8),
    @Longitude DECIMAL(11,8),
    @RadiusKm DECIMAL(5,2) = 5.0,
    @MaxResults INT = 20,
    @CacheKey VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @StartTime DATETIME2 = GETDATE();
    DECLARE @ResultCount INT = 0;
    DECLARE @QueryId INT;
    
    BEGIN TRY
        -- Normalize search query
        DECLARE @NormalizedQuery NVARCHAR(255) = LTRIM(RTRIM(LOWER(@SearchQuery)));
        
        -- Insert search query for analytics
        INSERT INTO search_queries (query_text, normalized_query, latitude, longitude, radius_km)
        VALUES (@SearchQuery, @NormalizedQuery, @Latitude, @Longitude, @RadiusKm);
        
        SET @QueryId = SCOPE_IDENTITY();
        
        -- Create temporary table for results
        CREATE TABLE #SearchResults (
            restaurant_id VARCHAR(50),
            distance_km DECIMAL(8,2),
            relevance_score DECIMAL(5,2),
            restaurant_name NVARCHAR(255),
            address NVARCHAR(MAX),
            phone VARCHAR(50),
            website VARCHAR(500),
            overall_rating DECIMAL(2,1),
            cuisine_type VARCHAR(100),
            menu_item_name NVARCHAR(255),
            menu_item_description NVARCHAR(MAX),
            menu_item_price DECIMAL(8,2),
            category_name NVARCHAR(100)
        );
        
        -- Search menu items with distance calculation
        INSERT INTO #SearchResults
        SELECT TOP (@MaxResults)
            r.restaurant_id,
            geography::Point(r.latitude, r.longitude, 4326).STDistance(
                geography::Point(@Latitude, @Longitude, 4326)
            ) / 1000.0 AS distance_km,
            CASE 
                WHEN mi.name LIKE '%' + @NormalizedQuery + '%' THEN 100
                WHEN mi.description LIKE '%' + @NormalizedQuery + '%' THEN 80
                WHEN mia.alias_text LIKE '%' + @NormalizedQuery + '%' THEN 90
                WHEN mi.normalized_name LIKE '%' + @NormalizedQuery + '%' THEN 85
                ELSE 50
            END AS relevance_score,
            r.name,
            r.address,
            r.phone,
            r.website,
            r.google_rating,
            mi.name,
            mi.description,
            mi.price,
            mc.category_name
        FROM restaurants r
        INNER JOIN menu_categories mc ON r.restaurant_id = mc.restaurant_id
        INNER JOIN menu_items mi ON mc.category_id = mi.category_id
        LEFT JOIN menu_item_aliases mia ON mi.item_id = mia.item_id
        WHERE (
            mi.name LIKE '%' + @NormalizedQuery + '%'
            OR mi.description LIKE '%' + @NormalizedQuery + '%'
            OR mi.normalized_name LIKE '%' + @NormalizedQuery + '%'
            OR mia.alias_text LIKE '%' + @NormalizedQuery + '%'
        )
        AND mi.is_available = 1
        AND geography::Point(r.latitude, r.longitude, 4326).STDistance(
            geography::Point(@Latitude, @Longitude, 4326)
        ) / 1000.0 <= @RadiusKm
        ORDER BY relevance_score DESC, distance_km ASC;
        
        -- Get result count
        SELECT @ResultCount = COUNT(*) FROM #SearchResults;
        
        -- Return results
        SELECT * FROM #SearchResults
        ORDER BY relevance_score DESC, distance_km ASC;
        
        -- Update search analytics
        DECLARE @ExecutionTime INT = DATEDIFF(MILLISECOND, @StartTime, GETDATE());
        
        UPDATE search_queries 
        SET total_restaurants_found = (SELECT COUNT(DISTINCT restaurant_id) FROM #SearchResults),
            total_menu_items_found = @ResultCount,
            execution_time_ms = @ExecutionTime
        WHERE query_id = @QueryId;
        
        -- Insert search results for caching
        INSERT INTO search_results (query_id, restaurant_id, item_id, relevance_score, distance_km)
        SELECT @QueryId, sr.restaurant_id, mi.item_id, sr.relevance_score, sr.distance_km
        FROM #SearchResults sr
        INNER JOIN menu_categories mc ON sr.restaurant_id = mc.restaurant_id
        INNER JOIN menu_items mi ON mc.category_id = mi.category_id AND mi.name = sr.menu_item_name;
        
        DROP TABLE #SearchResults;
        
    END TRY
    BEGIN CATCH
        IF OBJECT_ID('tempdb..#SearchResults') IS NOT NULL
            DROP TABLE #SearchResults;
            
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Find restaurants within radius with menu availability
CREATE PROCEDURE sp_GetNearbyRestaurants
    @Latitude DECIMAL(10,8),
    @Longitude DECIMAL(11,8),
    @RadiusKm DECIMAL(5,2) = 10.0,
    @HasMenuOnly BIT = 0,
    @MinRating DECIMAL(2,1) = 0
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        SELECT 
            r.restaurant_id,
            r.name,
            r.address,
            r.phone,
            r.website,
            r.menu_url,
            r.price_level,
            r.google_rating,
            r.is_chain,
            r.chain_name,
            geography::Point(r.latitude, r.longitude, 4326).STDistance(
                geography::Point(@Latitude, @Longitude, 4326)
            ) / 1000.0 AS distance_km,
            COUNT(mi.item_id) AS menu_items_count,
            r.last_scraped_at,
            r.scrape_status,
            CASE 
                WHEN r.last_scraped_at IS NULL THEN 'Never scraped'
                WHEN r.last_scraped_at < DATEADD(DAY, -7, GETDATE()) THEN 'Stale data'
                WHEN r.scrape_status = 'completed' THEN 'Current'
                ELSE 'Partial data'
            END AS menu_status
        FROM restaurants r
        LEFT JOIN menu_categories mc ON r.restaurant_id = mc.restaurant_id
        LEFT JOIN menu_items mi ON mc.category_id = mi.category_id AND mi.is_available = 1
        WHERE geography::Point(r.latitude, r.longitude, 4326).STDistance(
            geography::Point(@Latitude, @Longitude, 4326)
        ) / 1000.0 <= @RadiusKm
        AND r.google_rating >= @MinRating
        AND (@HasMenuOnly = 0 OR EXISTS(
            SELECT 1 FROM menu_categories mc2 
            INNER JOIN menu_items mi2 ON mc2.category_id = mi2.category_id 
            WHERE mc2.restaurant_id = r.restaurant_id AND mi2.is_available = 1
        ))
        GROUP BY r.restaurant_id, r.name, r.address, r.phone, r.website, r.menu_url,
                 r.price_level, r.google_rating, r.is_chain, r.chain_name,
                 r.latitude, r.longitude, r.last_scraped_at, r.scrape_status
        ORDER BY distance_km ASC, r.google_rating DESC;
        
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- =============================================================================
-- DATA MANAGEMENT PROCEDURES
-- =============================================================================

-- Insert or update restaurant data from Google Places API
CREATE PROCEDURE sp_UpsertRestaurant
    @RestaurantId VARCHAR(50),
    @Name NVARCHAR(255),
    @Address NVARCHAR(MAX),
    @Phone VARCHAR(50) = NULL,
    @Website VARCHAR(500) = NULL,
    @MenuUrl VARCHAR(500) = NULL,
    @GoogleRating DECIMAL(2,1) = NULL,
    @PriceLevel INT = NULL,
    @Latitude DECIMAL(10,8),
    @Longitude DECIMAL(11,8),
    @Timezone VARCHAR(50) = NULL,
    @HoursJson NVARCHAR(MAX) = NULL,
    @IsChain BIT = 0,
    @ChainName NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Validate coordinates
        IF @Latitude < -90 OR @Latitude > 90
            RAISERROR('Invalid latitude. Must be between -90 and 90.', 16, 1);
            
        IF @Longitude < -180 OR @Longitude > 180
            RAISERROR('Invalid longitude. Must be between -180 and 180.', 16, 1);
            
        -- Validate price level
        IF @PriceLevel IS NOT NULL AND (@PriceLevel < 1 OR @PriceLevel > 4)
            RAISERROR('Invalid price level. Must be between 1 and 4.', 16, 1);
            
        -- Validate JSON if provided
        IF @HoursJson IS NOT NULL AND ISJSON(@HoursJson) = 0
            RAISERROR('Invalid JSON format for hours data.', 16, 1);
        
        -- Auto-detect chain if not specified
        IF @IsChain = 0 AND @ChainName IS NULL
        BEGIN
            SELECT TOP 1 @ChainName = chain_name, @IsChain = 1
            FROM chain_configs
            WHERE @Website LIKE '%' + root_domain + '%'
               OR @Name LIKE '%' + chain_name + '%';
        END
        
        -- Upsert restaurant record
        MERGE restaurants AS target
        USING (VALUES (@RestaurantId, @Name, @Address, @Phone, @Website, @MenuUrl,
                      @GoogleRating, @PriceLevel, @Latitude, @Longitude, @Timezone,
                      @HoursJson, @IsChain, @ChainName)) AS source
                      (restaurant_id, name, address, phone, website, menu_url,
                       google_rating, price_level, latitude, longitude, timezone,
                       hours_json, is_chain, chain_name)
        ON target.restaurant_id = source.restaurant_id
        WHEN MATCHED THEN
            UPDATE SET
                name = source.name,
                address = source.address,
                phone = source.phone,
                website = source.website,
                menu_url = source.menu_url,
                google_rating = source.google_rating,
                price_level = source.price_level,
                latitude = source.latitude,
                longitude = source.longitude,
                timezone = source.timezone,
                hours_json = source.hours_json,
                is_chain = source.is_chain,
                chain_name = source.chain_name,
                updated_at = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (restaurant_id, name, address, phone, website, menu_url,
                   google_rating, price_level, latitude, longitude, timezone,
                   hours_json, is_chain, chain_name, created_at, updated_at)
            VALUES (source.restaurant_id, source.name, source.address, source.phone,
                   source.website, source.menu_url, source.google_rating,
                   source.price_level, source.latitude, source.longitude, source.timezone,
                   source.hours_json, source.is_chain, source.chain_name, GETDATE(), GETDATE());
                   
        -- Return the restaurant record
        SELECT * FROM restaurants WHERE restaurant_id = @RestaurantId;
        
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO