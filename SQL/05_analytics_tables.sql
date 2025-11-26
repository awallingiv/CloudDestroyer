-- FoodFinder Analytics and User Behavior Tables
-- User interaction tracking and system analytics

USE FoodFinder;
GO

-- =============================================================================
-- USER BEHAVIOR & ANALYTICS
-- =============================================================================

-- Track user interactions for analytics (privacy-focused)
CREATE TABLE user_interactions (
    interaction_id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Session tracking (no personal data, GDPR compliant)
    session_hash VARCHAR(64), -- Hashed session identifier
    
    -- Interaction details
    action VARCHAR(30) NOT NULL CHECK (action IN ('search', 'view_restaurant', 'view_menu_item', 'click_website', 'click_phone')),
    query_text VARCHAR(255),
    restaurant_id VARCHAR(50),
    item_id INT,
    
    -- Enhanced context (rounded for privacy)
    user_latitude DECIMAL(10,8), -- Rounded to ~100m precision for heatmaps
    user_longitude DECIMAL(11,8),
    device_type VARCHAR(20) DEFAULT 'unknown' CHECK (device_type IN ('web', 'ios', 'android', 'unknown')),
    user_agent NVARCHAR(MAX),
    
    -- Additional metadata
    referrer VARCHAR(500),
    page_load_time_ms INT,
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for user_interactions
CREATE INDEX idx_user_interactions_session ON user_interactions (session_hash);
CREATE INDEX idx_user_interactions_action ON user_interactions (action);
CREATE INDEX idx_user_interactions_created ON user_interactions (created_at);
CREATE INDEX idx_user_interactions_restaurant ON user_interactions (restaurant_id);
CREATE INDEX idx_user_interactions_device ON user_interactions (device_type);
CREATE INDEX idx_user_interactions_location ON user_interactions (user_latitude, user_longitude);
GO

-- Aggregate analytics for dashboards
CREATE TABLE daily_analytics (
    analytics_id INT IDENTITY(1,1) PRIMARY KEY,
    date_recorded DATE NOT NULL,
    
    -- Search metrics
    total_searches INT DEFAULT 0,
    unique_sessions INT DEFAULT 0,
    avg_results_per_search DECIMAL(5,2) DEFAULT 0,
    
    -- User engagement
    total_restaurant_views INT DEFAULT 0,
    total_menu_item_views INT DEFAULT 0,
    total_website_clicks INT DEFAULT 0,
    
    -- Performance metrics
    avg_search_time_ms INT DEFAULT 0,
    cache_hit_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Device breakdown
    web_users INT DEFAULT 0,
    mobile_users INT DEFAULT 0,
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes and constraints for daily_analytics
CREATE UNIQUE INDEX idx_daily_analytics_unique_date ON daily_analytics (date_recorded);
CREATE INDEX idx_daily_analytics_date ON daily_analytics (date_recorded DESC);
GO

-- Geographic analytics for market insights
CREATE TABLE location_analytics (
    location_id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Geographic area (rounded for privacy)
    latitude_center DECIMAL(8,6),
    longitude_center DECIMAL(9,6),
    radius_km DECIMAL(5,2) DEFAULT 1.0,
    
    -- Area metadata
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50) DEFAULT 'US',
    
    -- Search patterns
    top_search_terms NVARCHAR(MAX) CHECK (ISJSON(top_search_terms) = 1), -- Most popular searches in this area
    total_searches INT DEFAULT 0,
    unique_users INT DEFAULT 0,
    
    -- Restaurant density
    total_restaurants INT DEFAULT 0,
    restaurants_with_menus INT DEFAULT 0,
    
    last_updated DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for location_analytics
CREATE INDEX idx_location_analytics_location ON location_analytics (latitude_center, longitude_center);
CREATE INDEX idx_location_analytics_city ON location_analytics (city, state);
CREATE INDEX idx_location_analytics_searches ON location_analytics (total_searches DESC);
GO

-- Create trigger for location_analytics last_updated
CREATE TRIGGER tr_location_analytics_updated
ON location_analytics
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE location_analytics 
    SET last_updated = GETDATE()
    FROM location_analytics l
    INNER JOIN inserted i ON l.location_id = i.location_id;
END;
GO