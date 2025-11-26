-- FoodFinder Test Procedures
-- Simple test procedures to verify database functionality

USE FoodFinder;
GO

-- Simple procedure to test basic functionality
CREATE PROCEDURE sp_TestDatabase
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Show table counts
    SELECT 
        'Database Test Results' as test_name,
        (SELECT COUNT(*) FROM restaurants) as restaurants_count,
        (SELECT COUNT(*) FROM menu_categories) as categories_count,
        (SELECT COUNT(*) FROM menu_items) as menu_items_count,
        (SELECT COUNT(*) FROM system_config) as config_count,
        (SELECT COUNT(*) FROM chain_configs) as chain_configs_count,
        GETDATE() as test_timestamp;
        
    -- Show sample restaurant data
    SELECT TOP 3 
        restaurant_id,
        name,
        phone,
        google_rating,
        scrape_status
    FROM restaurants
    ORDER BY created_at DESC;
END;
GO

-- Simple procedure to add a test menu item
CREATE PROCEDURE sp_AddTestMenuItem
    @RestaurantId VARCHAR(50),
    @CategoryName NVARCHAR(100) = 'Test Menu',
    @ItemName NVARCHAR(255),
    @ItemPrice DECIMAL(8,2) = 9.99
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CategoryId INT;
    
    -- Get or create category
    SELECT @CategoryId = category_id 
    FROM menu_categories 
    WHERE restaurant_id = @RestaurantId AND name = @CategoryName;
    
    IF @CategoryId IS NULL
    BEGIN
        INSERT INTO menu_categories (restaurant_id, name, display_order, source)
        VALUES (@RestaurantId, @CategoryName, 1, 'manual');
        
        SET @CategoryId = SCOPE_IDENTITY();
    END
    
    -- Add menu item
    INSERT INTO menu_items (restaurant_id, category_id, name, normalized_name, price, is_available)
    VALUES (@RestaurantId, @CategoryId, @ItemName, LOWER(@ItemName), @ItemPrice, 1);
    
    -- Return result
    SELECT 
        'Menu item added successfully' as result,
        @RestaurantId as restaurant_id,
        @CategoryName as category_name,
        @ItemName as item_name,
        @ItemPrice as price;
END;
GO

-- Simple search procedure that works with current schema
CREATE PROCEDURE sp_SimpleSearch
    @SearchQuery NVARCHAR(255),
    @Latitude DECIMAL(10,8),
    @Longitude DECIMAL(11,8),
    @RadiusKm DECIMAL(5,2) = 10.0
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        r.restaurant_id,
        r.name as restaurant_name,
        r.address,
        r.phone,
        r.google_rating,
        mi.name as menu_item,
        mi.price,
        mc.name as category,
        geography::Point(r.latitude, r.longitude, 4326).STDistance(
            geography::Point(@Latitude, @Longitude, 4326)
        ) / 1000.0 AS distance_km
    FROM restaurants r
    INNER JOIN menu_categories mc ON r.restaurant_id = mc.restaurant_id
    INNER JOIN menu_items mi ON mc.category_id = mi.category_id AND r.restaurant_id = mi.restaurant_id
    WHERE (
        mi.name LIKE '%' + @SearchQuery + '%'
        OR mi.description LIKE '%' + @SearchQuery + '%'
        OR mi.normalized_name LIKE '%' + @SearchQuery + '%'
    )
    AND mi.is_available = 1
    AND geography::Point(r.latitude, r.longitude, 4326).STDistance(
        geography::Point(@Latitude, @Longitude, 4326)
    ) / 1000.0 <= @RadiusKm
    ORDER BY distance_km ASC;
END;
GO