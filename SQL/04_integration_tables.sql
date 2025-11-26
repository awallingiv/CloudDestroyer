-- FoodFinder Chain and External API Integration Tables
-- Third-party service integration and chain management

USE FoodFinder;
GO

-- =============================================================================
-- CHAIN & API INTEGRATION DATA
-- =============================================================================

-- Major chain configurations
CREATE TABLE chain_configs (
    chain_id INT IDENTITY(1,1) PRIMARY KEY,
    chain_name VARCHAR(100) UNIQUE NOT NULL,
    root_domain VARCHAR(100), -- e.g., mcdonalds.com
    
    -- API integrations available
    doordash_enabled BIT DEFAULT 0,
    ubereats_enabled BIT DEFAULT 0,
    yelp_enabled BIT DEFAULT 0,
    grubhub_enabled BIT DEFAULT 0,
    
    -- Menu endpoints for scraping
    menu_endpoints NVARCHAR(MAX) CHECK (ISJSON(menu_endpoints) = 1), -- Array of menu paths: ["menu", "food", "order-online"]
    
    -- Scraping configuration
    scraping_allowed BIT DEFAULT 1,
    custom_selectors NVARCHAR(MAX) CHECK (ISJSON(custom_selectors) = 1), -- Platform-specific CSS selectors
    
    -- Chain metadata
    website_pattern VARCHAR(255), -- Regex to detect chain websites
    logo_url VARCHAR(500),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for chain_configs
CREATE INDEX idx_chain_configs_name ON chain_configs (chain_name);
CREATE INDEX idx_chain_configs_domain ON chain_configs (root_domain);
CREATE INDEX idx_chain_configs_scraping ON chain_configs (scraping_allowed);
GO

-- Create trigger for updated_at
CREATE TRIGGER tr_chain_configs_updated_at
ON chain_configs
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE chain_configs 
    SET updated_at = GETDATE()
    FROM chain_configs c
    INNER JOIN inserted i ON c.chain_id = i.chain_id;
END;
GO

-- External API menu data (DoorDash, UberEats, etc.)
CREATE TABLE external_menu_data (
    external_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    
    -- Source information
    source_api VARCHAR(20) NOT NULL CHECK (source_api IN ('doordash', 'ubereats', 'yelp', 'grubhub', 'postmates')),
    external_restaurant_id VARCHAR(100), -- ID in the external system
    entity_type VARCHAR(20) DEFAULT 'restaurant' CHECK (entity_type IN ('restaurant', 'category', 'item')),
    
    -- Menu data (stored as JSON for flexibility)
    menu_data NVARCHAR(MAX) NOT NULL CHECK (ISJSON(menu_data) = 1), -- Raw API response data
    
    -- Metadata
    last_updated DATETIME2 DEFAULT GETDATE(),
    is_active BIT DEFAULT 1,
    sync_status VARCHAR(20) DEFAULT 'pending' CHECK (sync_status IN ('pending', 'success', 'failed')),
    
    CONSTRAINT FK_external_menu_data_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);
GO

-- Create indexes and constraints for external_menu_data
CREATE UNIQUE INDEX idx_external_menu_data_unique ON external_menu_data (restaurant_id, source_api, entity_type);
CREATE INDEX idx_external_menu_data_source ON external_menu_data (source_api);
CREATE INDEX idx_external_menu_data_updated ON external_menu_data (last_updated);
CREATE INDEX idx_external_menu_data_status ON external_menu_data (sync_status);
CREATE INDEX idx_external_menu_data_entity_type ON external_menu_data (entity_type);
GO

-- Create trigger for last_updated
CREATE TRIGGER tr_external_menu_data_updated
ON external_menu_data
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE external_menu_data 
    SET last_updated = GETDATE()
    FROM external_menu_data e
    INNER JOIN inserted i ON e.external_id = i.external_id;
END;
GO