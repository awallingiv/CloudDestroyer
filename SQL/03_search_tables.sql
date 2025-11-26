-- FoodFinder Search and Caching Tables
-- Query optimization and result caching

USE FoodFinder;
GO

-- =============================================================================
-- SEARCH & CACHING INFRASTRUCTURE
-- =============================================================================

-- Cache user search queries and results
CREATE TABLE search_queries (
    query_id INT IDENTITY(1,1) PRIMARY KEY,
    query_text NVARCHAR(255) NOT NULL,
    normalized_query NVARCHAR(255) NOT NULL, -- Cleaned/normalized version
    
    -- Location context
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    radius_km DECIMAL(5,2) DEFAULT 5.0,
    
    -- Results metadata
    total_restaurants_found INT DEFAULT 0,
    total_menu_items_found INT DEFAULT 0,
    
    -- Performance tracking
    execution_time_ms INT,
    cache_hit BIT DEFAULT 0,
    results_cached_at DATETIME2 NULL, -- When results were cached
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for search_queries
CREATE INDEX idx_search_queries_normalized_query ON search_queries (normalized_query);
CREATE INDEX idx_search_queries_location ON search_queries (latitude, longitude);
CREATE INDEX idx_search_queries_created ON search_queries (created_at);
CREATE INDEX idx_search_queries_cache_time ON search_queries (results_cached_at);
GO

-- Link queries to specific results for caching
CREATE TABLE search_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    query_id INT NOT NULL,
    restaurant_id VARCHAR(50) NOT NULL,
    item_id INT NULL, -- Specific menu item match, nullable for restaurant-only matches
    
    relevance_score DECIMAL(5,2) DEFAULT 0, -- How well it matches the query
    distance_km DECIMAL(8,2), -- Distance from search location
    
    CONSTRAINT FK_search_results_query 
        FOREIGN KEY (query_id) REFERENCES search_queries(query_id) ON DELETE CASCADE,
    CONSTRAINT FK_search_results_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT FK_search_results_item 
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE CASCADE
);
GO

-- Create indexes for search_results
CREATE INDEX idx_search_results_query ON search_results (query_id);
CREATE INDEX idx_search_results_restaurant ON search_results (restaurant_id);
CREATE INDEX idx_search_results_relevance ON search_results (relevance_score DESC);
CREATE INDEX idx_search_results_distance ON search_results (distance_km ASC);
GO

-- Popular searches for optimization and cache warming
CREATE TABLE popular_searches (
    search_id INT IDENTITY(1,1) PRIMARY KEY,
    search_term NVARCHAR(255) UNIQUE NOT NULL,
    search_count INT DEFAULT 1,
    last_searched DATETIME2 DEFAULT GETDATE(),
    last_seen_at DATETIME2 DEFAULT GETDATE(), -- For decay tracking
    decay_score DECIMAL(5,2) DEFAULT 1.0 -- Algorithmic trending score
);
GO

-- Create indexes for popular_searches
CREATE INDEX idx_popular_searches_count ON popular_searches (search_count DESC);
CREATE INDEX idx_popular_searches_decay ON popular_searches (decay_score DESC);
CREATE INDEX idx_popular_searches_last_seen ON popular_searches (last_seen_at DESC);
CREATE INDEX idx_popular_searches_term ON popular_searches (search_term);
GO

-- Create trigger for popular_searches last_searched update
CREATE TRIGGER tr_popular_searches_last_searched
ON popular_searches
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(search_count)
    BEGIN
        UPDATE popular_searches 
        SET last_searched = GETDATE()
        FROM popular_searches p
        INNER JOIN inserted i ON p.search_id = i.search_id;
    END
END;
GO