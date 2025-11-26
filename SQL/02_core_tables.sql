-- FoodFinder Core Tables Schema
-- Main restaurant and menu data structures

USE FoodFinder;
GO

-- =============================================================================
-- CORE RESTAURANT DATA
-- =============================================================================

-- Main restaurant information from Google Places API
CREATE TABLE restaurants (
    restaurant_id VARCHAR(50) PRIMARY KEY, -- Google Places place_id
    name NVARCHAR(255) NOT NULL,
    address NVARCHAR(MAX),
    phone VARCHAR(50),
    website VARCHAR(500),
    menu_url VARCHAR(500), -- Actual scraped page URL
    
    -- Google Places data
    google_rating DECIMAL(2,1),
    price_level INT, -- 1-4 scale from Google Places
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    timezone VARCHAR(50), -- e.g., America/Chicago
    hours_json NVARCHAR(MAX), -- Google operating hours structure (JSON)
    
    -- Chain detection
    is_chain BIT DEFAULT 0,
    chain_name NVARCHAR(100),
    
    -- Scraping metadata
    scrape_status VARCHAR(20) DEFAULT 'pending' CHECK (scrape_status IN ('pending', 'success', 'blocked', 'failed', 'no_menu')),
    last_scraped_at DATETIME2 NULL,
    robots_txt_status VARCHAR(20) DEFAULT 'unknown' CHECK (robots_txt_status IN ('allowed', 'blocked', 'unknown')),
    cloudflare_detected BIT DEFAULT 0,
    
    -- Timestamps
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for restaurants table
CREATE INDEX idx_restaurants_location ON restaurants (latitude, longitude);
CREATE INDEX idx_restaurants_chain ON restaurants (is_chain, chain_name);
CREATE INDEX idx_restaurants_scrape_status ON restaurants (scrape_status);
CREATE INDEX idx_restaurants_updated ON restaurants (updated_at);
CREATE FULLTEXT INDEX idx_restaurants_name ON restaurants (name);
GO

-- Create trigger for updated_at timestamp
CREATE TRIGGER tr_restaurants_updated_at
ON restaurants
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE restaurants 
    SET updated_at = GETDATE()
    FROM restaurants r
    INNER JOIN inserted i ON r.restaurant_id = i.restaurant_id;
END;
GO

-- =============================================================================
-- MENU STRUCTURE
-- =============================================================================

-- Menu categories (Burgers, Pizza, Appetizers, etc.)
CREATE TABLE menu_categories (
    category_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(MAX),
    display_order INT DEFAULT 0,
    
    -- Source tracking
    source VARCHAR(20) NOT NULL CHECK (source IN ('scraped', 'api', 'manual')),
    external_category_id VARCHAR(100), -- DoorDash/UberEats category ID
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_categories_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT UQ_menu_categories_restaurant_name UNIQUE (restaurant_id, name)
);
GO

-- Create indexes for menu_categories
CREATE INDEX idx_menu_categories_restaurant_order ON menu_categories (restaurant_id, display_order);
CREATE INDEX idx_menu_categories_source ON menu_categories (source);
GO

-- Individual menu items (the money table)
CREATE TABLE menu_items (
    item_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    category_id INT NULL, -- Can be null for uncategorized items
    
    -- Core item data
    name NVARCHAR(255) NOT NULL,
    normalized_name NVARCHAR(255), -- For synonyms and deduplication
    description NVARCHAR(MAX),
    image_url VARCHAR(500), -- Chain item images
    
    -- Pricing
    price DECIMAL(8,2), -- Allows up to $999,999.99
    price_text VARCHAR(50), -- Original text like $12.99-$15.99
    
    -- External integration
    external_item_id VARCHAR(100), -- API system ID (DoorDash, etc.)
    is_available BIT DEFAULT 1, -- For seasonal/discontinued items
    
    -- Metadata
    source VARCHAR(20) NOT NULL CHECK (source IN ('scraped', 'api', 'manual')),
    confidence_score INT DEFAULT 0, -- 0-100 confidence in accuracy
    search_tokens NVARCHAR(MAX), -- Space-separated normalized search terms
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_items_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT FK_menu_items_category 
        FOREIGN KEY (category_id) REFERENCES menu_categories(category_id) ON DELETE SET NULL
);
GO

-- Create indexes for menu_items
CREATE INDEX idx_menu_items_restaurant ON menu_items (restaurant_id);
CREATE INDEX idx_menu_items_category ON menu_items (category_id);
CREATE INDEX idx_menu_items_normalized_name ON menu_items (normalized_name);
CREATE INDEX idx_menu_items_price ON menu_items (price);
CREATE INDEX idx_menu_items_available ON menu_items (is_available);
CREATE INDEX idx_menu_items_confidence ON menu_items (confidence_score DESC);
CREATE FULLTEXT INDEX idx_menu_items_search_content ON menu_items (name, description, search_tokens);
GO

-- Create trigger for menu_items updated_at
CREATE TRIGGER tr_menu_items_updated_at
ON menu_items
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE menu_items 
    SET updated_at = GETDATE()
    FROM menu_items m
    INNER JOIN inserted i ON m.item_id = i.item_id;
END;
GO

-- Menu item aliases for handling user input variations
CREATE TABLE menu_item_aliases (
    alias_id INT IDENTITY(1,1) PRIMARY KEY,
    item_id INT NOT NULL,
    alias_text NVARCHAR(255) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0, -- 0.00 to 1.00 confidence score
    
    -- Source of alias
    source VARCHAR(20) DEFAULT 'manual' CHECK (source IN ('manual', 'generated', 'user_search')),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_item_aliases_item 
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE CASCADE,
    CONSTRAINT UQ_menu_item_aliases_item_text UNIQUE (item_id, alias_text)
);
GO

-- Create indexes for menu_item_aliases
CREATE INDEX idx_menu_item_aliases_alias ON menu_item_aliases (alias_text);
CREATE INDEX idx_menu_item_aliases_item ON menu_item_aliases (item_id);
CREATE INDEX idx_menu_item_aliases_confidence ON menu_item_aliases (confidence DESC);
GO