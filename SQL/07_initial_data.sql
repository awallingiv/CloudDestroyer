-- FoodFinder Initial Data Population
-- Sample data and essential configuration

USE FoodFinder;
GO

-- =============================================================================
-- SYSTEM CONFIGURATION
-- =============================================================================

INSERT INTO system_config (config_key, config_value, config_type, description, is_public) VALUES
-- Core application settings
('app_name', 'FoodFinder', 'string', 'Application display name', 1),
('app_version', '1.0.0', 'string', 'Current application version', 1),
('maintenance_mode', 'false', 'boolean', 'Enable maintenance mode', 1),

-- Search and caching
('search_radius_default_km', '10', 'number', 'Default search radius in kilometers', 1),
('search_max_results', '50', 'number', 'Maximum results per search', 1),
('cache_ttl_hours', '24', 'number', 'Menu data cache time-to-live', 0),
('popular_searches_limit', '100', 'number', 'Number of popular searches to track', 0),

-- Scraping configuration
('scraping_enabled', 'true', 'boolean', 'Global scraping enable/disable', 0),
('max_concurrent_scrapes', '5', 'number', 'Maximum simultaneous scraping jobs', 0),
('scraper_rate_limit_ms', '2000', 'number', 'Delay between scraper requests', 0),
('scraper_timeout_ms', '30000', 'number', 'Scraper request timeout', 0),
('scraper_retry_attempts', '3', 'number', 'Maximum retry attempts for failed scrapes', 0),

-- API rate limiting
('google_places_quota_per_day', '1000', 'number', 'Daily Google Places API quota', 0),
('api_rate_limit_per_hour', '1000', 'number', 'General API requests per hour limit', 0),

-- Feature flags
('enable_chain_detection', 'true', 'boolean', 'Enable automatic chain restaurant detection', 0),
('enable_external_apis', 'true', 'boolean', 'Enable DoorDash/UberEats integrations', 0),
('enable_analytics', 'true', 'boolean', 'Enable user analytics tracking', 0),
('enable_geolocation', 'true', 'boolean', 'Enable location-based features', 1),

-- Performance tuning
('database_query_timeout', '30', 'number', 'Database query timeout in seconds', 0),
('search_index_refresh_hours', '6', 'number', 'How often to refresh search indexes', 0);
GO

-- =============================================================================
-- CHAIN CONFIGURATIONS
-- =============================================================================

INSERT INTO chain_configs (
    chain_name, 
    root_domain, 
    doordash_enabled, 
    ubereats_enabled, 
    yelp_enabled,
    website_pattern,
    menu_endpoints,
    scraping_allowed
) VALUES
-- Major burger chains
('McDonald''s', 'mcdonalds.com', 1, 1, 1, 
 '.*mcdonalds\\.com.*', 
 '["menu", "us/en-us/full-menu"]', 
 0),

('Burger King', 'bk.com', 1, 1, 1, 
 '.*(bk\\.com|burgerking\\.com).*', 
 '["menu", "food"]', 
 1),

('Wendy''s', 'wendys.com', 1, 1, 1, 
 '.*wendys\\.com.*', 
 '["menu", "food"]', 
 1),

('In-N-Out', 'in-n-out.com', 0, 0, 1, 
 '.*in-n-out\\.com.*', 
 '["menu"]', 
 1),

-- Pizza chains
('Pizza Hut', 'pizzahut.com', 1, 1, 1, 
 '.*pizzahut\\.com.*', 
 '["menu", "order"]', 
 1),

('Domino''s', 'dominos.com', 1, 1, 1, 
 '.*dominos\\.com.*', 
 '["menu", "en/pages/order"]', 
 0),

('Papa John''s', 'papajohns.com', 1, 1, 1, 
 '.*papajohns\\.com.*', 
 '["menu"]', 
 1),

-- Other major chains
('Subway', 'subway.com', 1, 0, 1, 
 '.*subway\\.com.*', 
 '["menu", "en-us/menunutrition/menu"]', 
 1),

('Taco Bell', 'tacobell.com', 1, 1, 1, 
 '.*tacobell\\.com.*', 
 '["food"]', 
 1),

('KFC', 'kfc.com', 1, 1, 1, 
 '.*kfc\\.com.*', 
 '["menu"]', 
 1),

('Chipotle', 'chipotle.com', 1, 1, 1, 
 '.*chipotle\\.com.*', 
 '["menu"]', 
 0),

('Starbucks', 'starbucks.com', 1, 1, 1, 
 '.*starbucks\\.com.*', 
 '["menu"]', 
 0);
GO

-- =============================================================================
-- SAMPLE MENU ITEM ALIASES
-- =============================================================================

-- Common food aliases that users might search for
INSERT INTO popular_searches (search_term, search_count) VALUES
('burger', 150),
('pizza', 120),
('chicken', 100),
('tacos', 85),
('fries', 75),
('sandwich', 70),
('salad', 65),
('wings', 60),
('nuggets', 55),
('burrito', 50),
('pasta', 45),
('steak', 40),
('fish', 35),
('soup', 30),
('dessert', 25),
('coffee', 80),
('breakfast', 90),
('lunch', 75),
('dinner', 85),
('appetizer', 40);
GO

-- =============================================================================
-- SAMPLE HEALTH CHECK ENTRIES
-- =============================================================================

INSERT INTO health_checks (service_name, status, response_time_ms) VALUES
('Database', 'healthy', 15),
('Redis Cache', 'healthy', 3),
('Menu Scraper', 'healthy', 250),
('Google Places API', 'healthy', 180),
('File Storage', 'healthy', 8);
GO

-- =============================================================================
-- DISPLAY CONFIGURATION SUCCESS
-- =============================================================================

SELECT 
    'Sample data inserted successfully' as status,
    (SELECT COUNT(*) FROM system_config) as config_entries,
    (SELECT COUNT(*) FROM chain_configs) as chain_configs,
    (SELECT COUNT(*) FROM popular_searches) as popular_searches,
    GETDATE() as completed_at;
GO