-- =============================================================================
-- FoodFinder Database Schema
-- Restaurant search application database
-- =============================================================================

-- Create database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'FoodFinder')
BEGIN
    CREATE DATABASE FoodFinder
    COLLATE SQL_Latin1_General_CP1_CI_AS;
END
GO

USE FoodFinder;
GO

SELECT 
    'FoodFinder database created successfully' AS status,
    DB_NAME() AS current_database,
    DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS collation;
GO

-- =============================================================================
-- SECTION 1: CORE RESTAURANT TABLES
-- =============================================================================

-- Chain restaurant configurations (must be created first due to FK reference)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'chain_configs')
CREATE TABLE chain_configs (
    chain_id INT IDENTITY(1,1) PRIMARY KEY,
    chain_name VARCHAR(100) UNIQUE NOT NULL,
    normalized_name VARCHAR(100),

    -- Online ordering platforms
    website_pattern VARCHAR(255),
    root_domain VARCHAR(100),
    doordash_enabled BIT DEFAULT 0,
    ubereats_enabled BIT DEFAULT 0,
    grubhub_enabled BIT DEFAULT 0,

    -- Shared menu handling
    uses_shared_menu BIT DEFAULT 0,
    shared_menu_url VARCHAR(500),
    menu_endpoints NVARCHAR(MAX) CHECK (menu_endpoints IS NULL OR ISJSON(menu_endpoints) = 1),

    -- Branding
    logo_url VARCHAR(500),
    primary_color VARCHAR(10),

    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Main restaurant information
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'restaurants')
CREATE TABLE restaurants (
    restaurant_id VARCHAR(50) PRIMARY KEY,         -- Google Places ID or custom ID
    name NVARCHAR(255) NOT NULL,
    address NVARCHAR(MAX),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'US',
    phone VARCHAR(50),
    website VARCHAR(500),

    -- Google Places data
    google_rating DECIMAL(2,1),
    google_review_count INT DEFAULT 0,
    price_level INT CHECK (price_level IS NULL OR (price_level >= 1 AND price_level <= 4)),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    timezone VARCHAR(50),
    hours_json NVARCHAR(MAX) CHECK (hours_json IS NULL OR ISJSON(hours_json) = 1),

    -- Restaurant classification
    cuisine_types NVARCHAR(MAX) CHECK (cuisine_types IS NULL OR ISJSON(cuisine_types) = 1),
    is_chain BIT DEFAULT 0,
    chain_id INT NULL,

    -- Menu status
    has_menu BIT DEFAULT 0,
    menu_url VARCHAR(500),
    menu_source VARCHAR(50),                       -- 'clouddestroyer', 'manual', 'api', 'third_party'
    menu_item_count INT DEFAULT 0,
    menu_category_count INT DEFAULT 0,
    menu_last_updated DATETIME2 NULL,

    -- Price data status
    has_prices BIT DEFAULT 0,
    items_with_prices INT DEFAULT 0,
    avg_item_price DECIMAL(8,2) NULL,

    -- Status flags
    is_active BIT DEFAULT 1,
    is_verified BIT DEFAULT 0,
    needs_update BIT DEFAULT 0,

    -- Timestamps
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),

    CONSTRAINT FK_restaurants_chain FOREIGN KEY (chain_id) REFERENCES chain_configs(chain_id)
);
GO

-- Restaurant indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_location')
    CREATE INDEX idx_restaurants_location ON restaurants (latitude, longitude);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_chain')
    CREATE INDEX idx_restaurants_chain ON restaurants (is_chain, chain_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_city_state')
    CREATE INDEX idx_restaurants_city_state ON restaurants (city, state);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_has_menu')
    CREATE INDEX idx_restaurants_has_menu ON restaurants (has_menu) WHERE has_menu = 1;
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_rating')
    CREATE INDEX idx_restaurants_rating ON restaurants (google_rating DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_active')
    CREATE INDEX idx_restaurants_active ON restaurants (is_active) WHERE is_active = 1;
GO

-- Menu categories
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_categories')
CREATE TABLE menu_categories (
    category_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(MAX),
    display_order INT DEFAULT 0,
    
    -- Metadata
    item_count INT DEFAULT 0,
    external_id VARCHAR(100),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_categories_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT UQ_menu_categories_restaurant_name UNIQUE (restaurant_id, name)
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_categories_restaurant')
    CREATE INDEX idx_menu_categories_restaurant ON menu_categories (restaurant_id, display_order);
GO

-- Menu items
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_items')
CREATE TABLE menu_items (
    item_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    category_id INT NULL,
    
    -- Item details
    name NVARCHAR(255) NOT NULL,
    normalized_name NVARCHAR(255),                 -- Lowercase, no spaces for matching
    description NVARCHAR(MAX),
    
    -- Pricing
    price DECIMAL(8,2),
    price_text VARCHAR(50),                        -- Original price text (e.g., "$12.99", "Market Price")
    
    -- Media
    image_url VARCHAR(500),
    
    -- Metadata
    external_id VARCHAR(100),
    is_available BIT DEFAULT 1,
    is_popular BIT DEFAULT 0,
    
    -- Search optimization
    search_tokens NVARCHAR(MAX),                   -- Tokenized text for search
    
    -- Quality tracking
    confidence_score INT DEFAULT 0,                -- 0-100 confidence in data accuracy
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_items_restaurant
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT FK_menu_items_category
        FOREIGN KEY (category_id) REFERENCES menu_categories(category_id) ON DELETE NO ACTION
);
GO

-- Menu item indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_restaurant')
    CREATE INDEX idx_menu_items_restaurant ON menu_items (restaurant_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_category')
    CREATE INDEX idx_menu_items_category ON menu_items (category_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_normalized')
    CREATE INDEX idx_menu_items_normalized ON menu_items (normalized_name);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_price')
    CREATE INDEX idx_menu_items_price ON menu_items (price);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_available')
    CREATE INDEX idx_menu_items_available ON menu_items (is_available) WHERE is_available = 1;
GO

-- Menu item aliases for search matching
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_item_aliases')
CREATE TABLE menu_item_aliases (
    alias_id INT IDENTITY(1,1) PRIMARY KEY,
    item_id INT NOT NULL,
    alias_text NVARCHAR(255) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(20) DEFAULT 'manual',
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_aliases_item FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE CASCADE,
    CONSTRAINT UQ_aliases_item_text UNIQUE (item_id, alias_text)
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_aliases_text')
    CREATE INDEX idx_aliases_text ON menu_item_aliases (alias_text);
GO

-- =============================================================================
-- SECTION 2: SEARCH & USER TABLES
-- =============================================================================

-- Search query log
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'search_queries')
CREATE TABLE search_queries (
    query_id INT IDENTITY(1,1) PRIMARY KEY,
    query_text NVARCHAR(255) NOT NULL,
    normalized_query NVARCHAR(255) NOT NULL,
    
    -- Location context
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    radius_km DECIMAL(5,2) DEFAULT 5.0,
    city VARCHAR(100),
    state VARCHAR(50),
    
    -- Results
    total_restaurants_found INT DEFAULT 0,
    total_menu_items_found INT DEFAULT 0,
    
    -- Performance
    execution_time_ms INT,
    cache_hit BIT DEFAULT 0,
    
    -- Session tracking
    session_id VARCHAR(64),
    device_type VARCHAR(20),
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_queries_normalized')
    CREATE INDEX idx_search_queries_normalized ON search_queries (normalized_query);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_queries_location')
    CREATE INDEX idx_search_queries_location ON search_queries (latitude, longitude);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_queries_created')
    CREATE INDEX idx_search_queries_created ON search_queries (created_at);
GO

-- Popular/trending searches
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'popular_searches')
CREATE TABLE popular_searches (
    search_id INT IDENTITY(1,1) PRIMARY KEY,
    search_term NVARCHAR(255) UNIQUE NOT NULL,
    search_count INT DEFAULT 1,
    last_searched DATETIME2 DEFAULT GETDATE(),
    trend_score DECIMAL(5,2) DEFAULT 1.0,
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_popular_count')
    CREATE INDEX idx_popular_count ON popular_searches (search_count DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_popular_trend')
    CREATE INDEX idx_popular_trend ON popular_searches (trend_score DESC);
GO

-- User interactions for analytics
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_interactions')
CREATE TABLE user_interactions (
    interaction_id INT IDENTITY(1,1) PRIMARY KEY,
    session_id VARCHAR(64),
    
    action VARCHAR(30) NOT NULL 
        CHECK (action IN ('search', 'view_restaurant', 'view_menu', 'view_item', 'click_website', 'click_phone', 'click_directions')),
    
    -- Context
    query_text VARCHAR(255),
    restaurant_id VARCHAR(50),
    item_id INT,
    
    -- Location
    user_latitude DECIMAL(10,8),
    user_longitude DECIMAL(11,8),
    
    -- Device info
    device_type VARCHAR(20) DEFAULT 'unknown',
    user_agent NVARCHAR(500),
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_interactions_session')
    CREATE INDEX idx_interactions_session ON user_interactions (session_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_interactions_action')
    CREATE INDEX idx_interactions_action ON user_interactions (action);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_interactions_restaurant')
    CREATE INDEX idx_interactions_restaurant ON user_interactions (restaurant_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_interactions_created')
    CREATE INDEX idx_interactions_created ON user_interactions (created_at);
GO

-- =============================================================================
-- SECTION 3: SYSTEM TABLES
-- =============================================================================

-- Application configuration
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'app_config')
CREATE TABLE app_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value NVARCHAR(MAX),
    config_type VARCHAR(20) DEFAULT 'string',
    description NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================================================
-- SECTION 4: TRIGGERS
-- =============================================================================

-- Restaurant updated_at trigger
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_restaurants_updated')
BEGIN
    EXEC('
    CREATE TRIGGER tr_restaurants_updated
    ON restaurants
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE restaurants 
        SET updated_at = GETDATE()
        FROM restaurants r
        INNER JOIN inserted i ON r.restaurant_id = i.restaurant_id;
    END');
END
GO

-- Menu items updated_at trigger
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_menu_items_updated')
BEGIN
    EXEC('
    CREATE TRIGGER tr_menu_items_updated
    ON menu_items
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE menu_items 
        SET updated_at = GETDATE()
        FROM menu_items m
        INNER JOIN inserted i ON m.item_id = i.item_id;
    END');
END
GO

-- =============================================================================
-- SECTION 5: VIEWS
-- =============================================================================

-- Restaurant search view
IF OBJECT_ID('v_restaurant_search') IS NOT NULL DROP VIEW v_restaurant_search;
GO

CREATE VIEW v_restaurant_search AS
SELECT 
    r.restaurant_id,
    r.name,
    r.address,
    r.city,
    r.state,
    r.phone,
    r.website,
    r.google_rating,
    r.google_review_count,
    r.price_level,
    r.latitude,
    r.longitude,
    r.cuisine_types,
    r.is_chain,
    c.chain_name,
    r.has_menu,
    r.menu_item_count,
    r.has_prices,
    r.avg_item_price,
    r.hours_json
FROM restaurants r
LEFT JOIN chain_configs c ON r.chain_id = c.chain_id
WHERE r.is_active = 1;
GO

-- Menu item search view
IF OBJECT_ID('v_menu_item_search') IS NOT NULL DROP VIEW v_menu_item_search;
GO

CREATE VIEW v_menu_item_search AS
SELECT 
    mi.item_id,
    mi.name AS item_name,
    mi.normalized_name,
    mi.description,
    mi.price,
    mi.price_text,
    mi.image_url,
    mi.is_available,
    mc.name AS category_name,
    r.restaurant_id,
    r.name AS restaurant_name,
    r.city,
    r.state,
    r.latitude,
    r.longitude,
    r.google_rating,
    r.price_level
FROM menu_items mi
INNER JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
LEFT JOIN menu_categories mc ON mi.category_id = mc.category_id
WHERE mi.is_available = 1 AND r.is_active = 1;
GO

-- Restaurant statistics view
IF OBJECT_ID('v_restaurant_stats') IS NOT NULL DROP VIEW v_restaurant_stats;
GO

CREATE VIEW v_restaurant_stats AS
SELECT 
    'Restaurant Statistics' AS metric_category,
    COUNT(*) AS total_restaurants,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_restaurants,
    SUM(CASE WHEN has_menu = 1 THEN 1 ELSE 0 END) AS restaurants_with_menu,
    SUM(CASE WHEN has_prices = 1 THEN 1 ELSE 0 END) AS restaurants_with_prices,
    SUM(menu_item_count) AS total_menu_items,
    AVG(CAST(google_rating AS FLOAT)) AS avg_google_rating,
    SUM(CASE WHEN is_chain = 1 THEN 1 ELSE 0 END) AS chain_locations
FROM restaurants;
GO

-- =============================================================================
-- SECTION 6: STORED PROCEDURES
-- =============================================================================

-- Upsert restaurant
IF OBJECT_ID('sp_UpsertRestaurant') IS NOT NULL DROP PROCEDURE sp_UpsertRestaurant;
GO

CREATE PROCEDURE sp_UpsertRestaurant
    @RestaurantId VARCHAR(50),
    @Name NVARCHAR(255),
    @Address NVARCHAR(MAX) = NULL,
    @City VARCHAR(100) = NULL,
    @State VARCHAR(50) = NULL,
    @ZipCode VARCHAR(20) = NULL,
    @Phone VARCHAR(50) = NULL,
    @Website VARCHAR(500) = NULL,
    @GoogleRating DECIMAL(2,1) = NULL,
    @GoogleReviewCount INT = NULL,
    @PriceLevel INT = NULL,
    @Latitude DECIMAL(10,8) = NULL,
    @Longitude DECIMAL(11,8) = NULL,
    @HoursJson NVARCHAR(MAX) = NULL,
    @CuisineTypes NVARCHAR(MAX) = NULL,
    @IsChain BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Auto-detect chain
    DECLARE @ChainId INT = NULL;
    IF @IsChain = 0 AND @Website IS NOT NULL
    BEGIN
        SELECT TOP 1 @ChainId = chain_id, @IsChain = 1
        FROM chain_configs
        WHERE @Website LIKE '%' + root_domain + '%'
           OR @Name LIKE '%' + chain_name + '%';
    END
    
    MERGE restaurants AS target
    USING (SELECT @RestaurantId AS restaurant_id) AS source
    ON target.restaurant_id = source.restaurant_id
    WHEN MATCHED THEN
        UPDATE SET
            name = @Name,
            address = ISNULL(@Address, target.address),
            city = ISNULL(@City, target.city),
            state = ISNULL(@State, target.state),
            zip_code = ISNULL(@ZipCode, target.zip_code),
            phone = ISNULL(@Phone, target.phone),
            website = ISNULL(@Website, target.website),
            google_rating = ISNULL(@GoogleRating, target.google_rating),
            google_review_count = ISNULL(@GoogleReviewCount, target.google_review_count),
            price_level = ISNULL(@PriceLevel, target.price_level),
            latitude = ISNULL(@Latitude, target.latitude),
            longitude = ISNULL(@Longitude, target.longitude),
            hours_json = ISNULL(@HoursJson, target.hours_json),
            cuisine_types = ISNULL(@CuisineTypes, target.cuisine_types),
            is_chain = @IsChain,
            chain_id = @ChainId
    WHEN NOT MATCHED THEN
        INSERT (restaurant_id, name, address, city, state, zip_code, phone, website,
                google_rating, google_review_count, price_level, latitude, longitude,
                hours_json, cuisine_types, is_chain, chain_id)
        VALUES (@RestaurantId, @Name, @Address, @City, @State, @ZipCode, @Phone, @Website,
                @GoogleRating, @GoogleReviewCount, @PriceLevel, @Latitude, @Longitude,
                @HoursJson, @CuisineTypes, @IsChain, @ChainId);
    
    SELECT * FROM restaurants WHERE restaurant_id = @RestaurantId;
END;
GO

-- Import menu data from CloudDestroyer results
IF OBJECT_ID('sp_ImportMenuData') IS NOT NULL DROP PROCEDURE sp_ImportMenuData;
GO

CREATE PROCEDURE sp_ImportMenuData
    @RestaurantId VARCHAR(50),
    @MenuData NVARCHAR(MAX),
    @MenuSource VARCHAR(50) = 'clouddestroyer'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ItemsInserted INT = 0;
    DECLARE @CategoriesCreated INT = 0;
    DECLARE @ItemsWithPrices INT = 0;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Verify restaurant exists
        IF NOT EXISTS (SELECT 1 FROM restaurants WHERE restaurant_id = @RestaurantId)
        BEGIN
            RAISERROR('Restaurant not found: %s', 16, 1, @RestaurantId);
            RETURN;
        END
        
        -- Clear existing menu data for this restaurant
        DELETE FROM menu_items WHERE restaurant_id = @RestaurantId;
        DELETE FROM menu_categories WHERE restaurant_id = @RestaurantId;
        
        -- Insert categories from JSON
        INSERT INTO menu_categories (restaurant_id, name, description, display_order)
        SELECT DISTINCT 
            @RestaurantId,
            JSON_VALUE(value, '$.name'),
            JSON_VALUE(value, '$.description'),
            ISNULL(CAST(JSON_VALUE(value, '$.display_order') AS INT), 0)
        FROM OPENJSON(@MenuData, '$.categories')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL;
        
        SET @CategoriesCreated = @@ROWCOUNT;
        
        -- Insert menu items from JSON
        INSERT INTO menu_items (
            restaurant_id, category_id, name, normalized_name, description,
            price, price_text, image_url, external_id, confidence_score, search_tokens
        )
        SELECT 
            @RestaurantId,
            mc.category_id,
            JSON_VALUE(value, '$.name'),
            LOWER(REPLACE(JSON_VALUE(value, '$.name'), ' ', '')),
            JSON_VALUE(value, '$.description'),
            CASE 
                WHEN ISNUMERIC(REPLACE(REPLACE(JSON_VALUE(value, '$.price'), '$', ''), ',', '')) = 1 
                THEN CAST(REPLACE(REPLACE(JSON_VALUE(value, '$.price'), '$', ''), ',', '') AS DECIMAL(8,2))
                ELSE NULL 
            END,
            JSON_VALUE(value, '$.price'),
            JSON_VALUE(value, '$.image_url'),
            JSON_VALUE(value, '$.external_id'),
            ISNULL(CAST(JSON_VALUE(value, '$.confidence') AS INT), 80),
            LOWER(JSON_VALUE(value, '$.name') + ' ' + ISNULL(JSON_VALUE(value, '$.description'), ''))
        FROM OPENJSON(@MenuData, '$.items')
        LEFT JOIN menu_categories mc ON mc.restaurant_id = @RestaurantId 
            AND mc.name = JSON_VALUE(value, '$.category')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL
          AND LEN(JSON_VALUE(value, '$.name')) > 2;
        
        SET @ItemsInserted = @@ROWCOUNT;
        
        -- Count items with prices
        SELECT @ItemsWithPrices = COUNT(*) 
        FROM menu_items 
        WHERE restaurant_id = @RestaurantId AND price IS NOT NULL;
        
        -- Update category item counts
        UPDATE mc
        SET item_count = (SELECT COUNT(*) FROM menu_items mi WHERE mi.category_id = mc.category_id)
        FROM menu_categories mc
        WHERE mc.restaurant_id = @RestaurantId;
        
        -- Update restaurant menu status
        UPDATE restaurants
        SET has_menu = CASE WHEN @ItemsInserted > 0 THEN 1 ELSE 0 END,
            menu_source = @MenuSource,
            menu_item_count = @ItemsInserted,
            menu_category_count = @CategoriesCreated,
            menu_last_updated = GETDATE(),
            has_prices = CASE WHEN @ItemsWithPrices > 0 THEN 1 ELSE 0 END,
            items_with_prices = @ItemsWithPrices,
            avg_item_price = (SELECT AVG(price) FROM menu_items WHERE restaurant_id = @RestaurantId AND price IS NOT NULL),
            needs_update = 0
        WHERE restaurant_id = @RestaurantId;
        
        COMMIT TRANSACTION;
        
        SELECT 
            @RestaurantId AS restaurant_id,
            @ItemsInserted AS items_imported,
            @CategoriesCreated AS categories_created,
            @ItemsWithPrices AS items_with_prices,
            'success' AS status;
        
    END TRY
    BEGIN CATCH
        IF XACT_STATE() != 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

-- Simple search procedure
IF OBJECT_ID('sp_SearchMenuItems') IS NOT NULL DROP PROCEDURE sp_SearchMenuItems;
GO

CREATE PROCEDURE sp_SearchMenuItems
    @SearchText NVARCHAR(255),
    @Latitude DECIMAL(10,8) = NULL,
    @Longitude DECIMAL(11,8) = NULL,
    @RadiusKm DECIMAL(5,2) = 10.0,
    @MaxResults INT = 50
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @NormalizedSearch NVARCHAR(255) = LOWER(TRIM(@SearchText));
    DECLARE @StartTime DATETIME2 = GETDATE();
    
    -- Log search
    INSERT INTO search_queries (query_text, normalized_query, latitude, longitude, radius_km)
    VALUES (@SearchText, @NormalizedSearch, @Latitude, @Longitude, @RadiusKm);
    
    -- Update popular searches
    MERGE popular_searches AS target
    USING (SELECT @NormalizedSearch AS term) AS source
    ON target.search_term = source.term
    WHEN MATCHED THEN UPDATE SET search_count = search_count + 1, last_searched = GETDATE()
    WHEN NOT MATCHED THEN INSERT (search_term) VALUES (source.term);
    
    -- Search results
    SELECT TOP (@MaxResults)
        mi.item_id,
        mi.name AS item_name,
        mi.description,
        mi.price,
        mi.price_text,
        mi.image_url,
        mc.name AS category_name,
        r.restaurant_id,
        r.name AS restaurant_name,
        r.address,
        r.city,
        r.state,
        r.phone,
        r.website,
        r.google_rating,
        r.latitude,
        r.longitude,
        -- Distance calculation (if location provided)
        CASE WHEN @Latitude IS NOT NULL AND @Longitude IS NOT NULL THEN
            6371 * ACOS(
                COS(RADIANS(@Latitude)) * COS(RADIANS(r.latitude)) *
                COS(RADIANS(r.longitude) - RADIANS(@Longitude)) +
                SIN(RADIANS(@Latitude)) * SIN(RADIANS(r.latitude))
            )
        ELSE NULL END AS distance_km,
        -- Relevance score
        CASE 
            WHEN mi.normalized_name = @NormalizedSearch THEN 100
            WHEN mi.normalized_name LIKE @NormalizedSearch + '%' THEN 90
            WHEN mi.normalized_name LIKE '%' + @NormalizedSearch + '%' THEN 70
            WHEN mi.search_tokens LIKE '%' + @NormalizedSearch + '%' THEN 50
            ELSE 30
        END AS relevance_score
    FROM menu_items mi
    INNER JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
    LEFT JOIN menu_categories mc ON mi.category_id = mc.category_id
    WHERE mi.is_available = 1 
      AND r.is_active = 1
      AND (
          mi.normalized_name LIKE '%' + @NormalizedSearch + '%'
          OR mi.search_tokens LIKE '%' + @NormalizedSearch + '%'
          OR mi.name LIKE '%' + @SearchText + '%'
      )
      AND (
          @Latitude IS NULL OR @Longitude IS NULL
          OR (
              6371 * ACOS(
                  COS(RADIANS(@Latitude)) * COS(RADIANS(r.latitude)) *
                  COS(RADIANS(r.longitude) - RADIANS(@Longitude)) +
                  SIN(RADIANS(@Latitude)) * SIN(RADIANS(r.latitude))
              ) <= @RadiusKm
          )
      )
    ORDER BY relevance_score DESC, distance_km ASC, r.google_rating DESC;
    
    -- Update search result count
    UPDATE search_queries 
    SET total_menu_items_found = @@ROWCOUNT,
        execution_time_ms = DATEDIFF(MILLISECOND, @StartTime, GETDATE())
    WHERE query_id = SCOPE_IDENTITY();
END;
GO

-- =============================================================================
-- SECTION 7: INITIAL DATA
-- =============================================================================

-- App configuration
IF NOT EXISTS (SELECT 1 FROM app_config WHERE config_key = 'app_name')
BEGIN
    INSERT INTO app_config (config_key, config_value, config_type, description, is_public) VALUES
    ('app_name', 'FoodFinder', 'string', 'Application name', 1),
    ('app_version', '1.0.0', 'string', 'Current version', 1),
    ('default_search_radius_km', '10', 'number', 'Default search radius', 1),
    ('max_search_results', '50', 'number', 'Maximum search results', 1),
    ('clouddestroyer_db', 'CloudDestroyer', 'string', 'CloudDestroyer database name', 0);
END
GO

-- Chain configurations
IF NOT EXISTS (SELECT 1 FROM chain_configs WHERE chain_name = 'Bubba''s 33')
BEGIN
    INSERT INTO chain_configs (chain_name, normalized_name, root_domain, website_pattern) VALUES
    ('Bubba''s 33', 'bubbas33', 'bubbas33.com', '.*bubbas33\\.com.*'),
    ('McDonald''s', 'mcdonalds', 'mcdonalds.com', '.*mcdonalds\\.com.*'),
    ('Burger King', 'burgerking', 'bk.com', '.*(bk\\.com|burgerking\\.com).*'),
    ('Wendy''s', 'wendys', 'wendys.com', '.*wendys\\.com.*'),
    ('Pizza Hut', 'pizzahut', 'pizzahut.com', '.*pizzahut\\.com.*'),
    ('Domino''s', 'dominos', 'dominos.com', '.*dominos\\.com.*'),
    ('Taco Bell', 'tacobell', 'tacobell.com', '.*tacobell\\.com.*'),
    ('Chipotle', 'chipotle', 'chipotle.com', '.*chipotle\\.com.*'),
    ('Starbucks', 'starbucks', 'starbucks.com', '.*starbucks\\.com.*');
END
GO

-- Popular searches
IF NOT EXISTS (SELECT 1 FROM popular_searches WHERE search_term = 'burger')
BEGIN
    INSERT INTO popular_searches (search_term, search_count) VALUES
    ('burger', 150), ('pizza', 120), ('chicken', 100), ('tacos', 85),
    ('fries', 75), ('sandwich', 70), ('salad', 65), ('wings', 60),
    ('pasta', 50), ('steak', 45), ('breakfast', 90), ('coffee', 80);
END
GO

-- =============================================================================
-- SETUP COMPLETE
-- =============================================================================

SELECT 
    'FoodFinder database setup complete!' AS message,
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = 'FoodFinder') AS total_tables,
    (SELECT COUNT(*) FROM sys.procedures WHERE type = 'P') AS total_procedures,
    (SELECT COUNT(*) FROM sys.views) AS total_views,
    GETDATE() AS completed_at;
GO


