-- =============================================================================
-- FoodFinder + CloudDestroyer Complete Database Setup
-- Combined Tables, Procedures, and Initial Data
-- Generated: Production Ready
-- =============================================================================

-- =============================================================================
-- SECTION 1: DATABASE CREATION
-- =============================================================================

-- Create database with UTF-8 support for international restaurant names
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'FoodFinder')
BEGIN
    CREATE DATABASE FoodFinder
    COLLATE SQL_Latin1_General_CP1_CI_AS;
END
GO

USE FoodFinder;
GO

-- Display database info
SELECT 
    'FoodFinder database created successfully' as status,
    DB_NAME() as current_database,
    DATABASEPROPERTYEX(DB_NAME(), 'Collation') as collation;
GO

-- =============================================================================
-- SECTION 2: CORE TABLES
-- =============================================================================

-- Main restaurant information from Google Places API
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'restaurants')
CREATE TABLE restaurants (
    restaurant_id VARCHAR(50) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    address NVARCHAR(MAX),
    phone VARCHAR(50),
    website VARCHAR(500),
    menu_url VARCHAR(500),
    
    -- Google Places data
    google_rating DECIMAL(2,1),
    price_level INT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    timezone VARCHAR(50),
    hours_json NVARCHAR(MAX),
    
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
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_location')
    CREATE INDEX idx_restaurants_location ON restaurants (latitude, longitude);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_chain')
    CREATE INDEX idx_restaurants_chain ON restaurants (is_chain, chain_name);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_scrape_status')
    CREATE INDEX idx_restaurants_scrape_status ON restaurants (scrape_status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_updated')
    CREATE INDEX idx_restaurants_updated ON restaurants (updated_at);
GO

-- Create trigger for updated_at timestamp
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_restaurants_updated_at')
BEGIN
    EXEC('
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
    END');
END
GO

-- Menu categories (Burgers, Pizza, Appetizers, etc.)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_categories')
CREATE TABLE menu_categories (
    category_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    description NVARCHAR(MAX),
    display_order INT DEFAULT 0,
    
    source VARCHAR(20) NOT NULL CHECK (source IN ('scraped', 'api', 'manual')),
    external_category_id VARCHAR(100),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_categories_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT UQ_menu_categories_restaurant_name UNIQUE (restaurant_id, name)
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_categories_restaurant_order')
    CREATE INDEX idx_menu_categories_restaurant_order ON menu_categories (restaurant_id, display_order);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_categories_source')
    CREATE INDEX idx_menu_categories_source ON menu_categories (source);
GO

-- Individual menu items
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_items')
CREATE TABLE menu_items (
    item_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    category_id INT NULL,
    
    name NVARCHAR(255) NOT NULL,
    normalized_name NVARCHAR(255),
    description NVARCHAR(MAX),
    image_url VARCHAR(500),
    
    price DECIMAL(8,2),
    price_text VARCHAR(50),
    
    external_item_id VARCHAR(100),
    is_available BIT DEFAULT 1,
    
    source VARCHAR(20) NOT NULL CHECK (source IN ('scraped', 'api', 'manual')),
    confidence_score INT DEFAULT 0,
    search_tokens NVARCHAR(MAX),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_items_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT FK_menu_items_category 
        FOREIGN KEY (category_id) REFERENCES menu_categories(category_id) ON DELETE SET NULL
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_restaurant')
    CREATE INDEX idx_menu_items_restaurant ON menu_items (restaurant_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_category')
    CREATE INDEX idx_menu_items_category ON menu_items (category_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_normalized_name')
    CREATE INDEX idx_menu_items_normalized_name ON menu_items (normalized_name);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_price')
    CREATE INDEX idx_menu_items_price ON menu_items (price);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_available')
    CREATE INDEX idx_menu_items_available ON menu_items (is_available);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_items_confidence')
    CREATE INDEX idx_menu_items_confidence ON menu_items (confidence_score DESC);
GO

-- Create trigger for menu_items updated_at
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_menu_items_updated_at')
BEGIN
    EXEC('
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
    END');
END
GO

-- Menu item aliases for handling user input variations
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_item_aliases')
CREATE TABLE menu_item_aliases (
    alias_id INT IDENTITY(1,1) PRIMARY KEY,
    item_id INT NOT NULL,
    alias_text NVARCHAR(255) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(20) DEFAULT 'manual' CHECK (source IN ('manual', 'generated', 'user_search')),
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_item_aliases_item 
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE CASCADE,
    CONSTRAINT UQ_menu_item_aliases_item_text UNIQUE (item_id, alias_text)
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_item_aliases_alias')
    CREATE INDEX idx_menu_item_aliases_alias ON menu_item_aliases (alias_text);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_item_aliases_item')
    CREATE INDEX idx_menu_item_aliases_item ON menu_item_aliases (item_id);
GO

-- Raw menu content storage for complete extracted text/HTML
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'raw_menu_content')
CREATE TABLE raw_menu_content (
    content_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    
    -- Content storage
    content_html NVARCHAR(MAX),
    content_text NVARCHAR(MAX),
    content_json NVARCHAR(MAX) CHECK (content_json IS NULL OR ISJSON(content_json) = 1),
    
    -- Extraction metadata
    extraction_url VARCHAR(1000),
    extraction_method VARCHAR(100),
    extraction_timestamp DATETIME2 DEFAULT GETDATE(),
    
    -- Content analysis
    total_content_length INT DEFAULT 0,
    menu_indicators_found INT DEFAULT 0,
    price_patterns_count INT DEFAULT 0,
    food_categories_detected INT DEFAULT 0,
    
    -- Quality metrics
    extraction_confidence DECIMAL(3,2) DEFAULT 0,
    parsing_success BIT DEFAULT 0,
    meets_success_threshold BIT DEFAULT 0,
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'raw' CHECK (processing_status IN ('raw', 'processing', 'processed', 'failed')),
    structured_items_created INT DEFAULT 0,
    last_processed_at DATETIME2 NULL,
    
    -- Debugging data
    discovery_attempts_log NVARCHAR(MAX) CHECK (discovery_attempts_log IS NULL OR ISJSON(discovery_attempts_log) = 1),
    error_details NVARCHAR(MAX),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_raw_menu_content_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_raw_menu_content_restaurant')
    CREATE INDEX idx_raw_menu_content_restaurant ON raw_menu_content (restaurant_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_raw_menu_content_extraction_timestamp')
    CREATE INDEX idx_raw_menu_content_extraction_timestamp ON raw_menu_content (extraction_timestamp DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_raw_menu_content_processing_status')
    CREATE INDEX idx_raw_menu_content_processing_status ON raw_menu_content (processing_status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_raw_menu_content_success_threshold')
    CREATE INDEX idx_raw_menu_content_success_threshold ON raw_menu_content (meets_success_threshold);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_raw_menu_content_confidence')
    CREATE INDEX idx_raw_menu_content_confidence ON raw_menu_content (extraction_confidence DESC);
GO

-- Menu extraction attempts log for tracking discovery methods
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'menu_extraction_attempts')
CREate TABLE menu_extraction_attempts (
    attempt_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    
    attempt_number INT NOT NULL,
    discovery_method VARCHAR(100) NOT NULL,
    target_url VARCHAR(1000),
    
    status VARCHAR(20) CHECK (status IN ('success', 'failed', 'blocked', 'timeout', 'no_content')),
    
    -- Discovery metrics
    response_time_ms INT DEFAULT 0,
    content_length INT DEFAULT 0,
    menu_score INT DEFAULT 0,
    confidence_score DECIMAL(3,2) DEFAULT 0,
    
    -- Content analysis
    menu_items_found INT DEFAULT 0,
    price_patterns_found INT DEFAULT 0,
    categories_found INT DEFAULT 0,
    
    error_message NVARCHAR(MAX),
    raw_response_snippet NVARCHAR(1000),
    
    attempted_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_menu_extraction_attempts_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_extraction_attempts_restaurant')
    CREATE INDEX idx_menu_extraction_attempts_restaurant ON menu_extraction_attempts (restaurant_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_extraction_attempts_method')
    CREATE INDEX idx_menu_extraction_attempts_method ON menu_extraction_attempts (discovery_method);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_extraction_attempts_status')
    CREATE INDEX idx_menu_extraction_attempts_status ON menu_extraction_attempts (status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_menu_extraction_attempts_attempted')
    CREATE INDEX idx_menu_extraction_attempts_attempted ON menu_extraction_attempts (attempted_at DESC);
GO

-- Update trigger for raw_menu_content
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_raw_menu_content_updated_at')
BEGIN
    EXEC('
    CREATE TRIGGER tr_raw_menu_content_updated_at
    ON raw_menu_content
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE raw_menu_content 
        SET updated_at = GETDATE()
        FROM raw_menu_content r
        INNER JOIN inserted i ON r.content_id = i.content_id;
    END');
END
GO

-- =============================================================================
-- SECTION 3: SEARCH & CACHING TABLES
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'search_queries')
CREATE TABLE search_queries (
    query_id INT IDENTITY(1,1) PRIMARY KEY,
    query_text NVARCHAR(255) NOT NULL,
    normalized_query NVARCHAR(255) NOT NULL,
    
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    radius_km DECIMAL(5,2) DEFAULT 5.0,
    
    total_restaurants_found INT DEFAULT 0,
    total_menu_items_found INT DEFAULT 0,
    
    execution_time_ms INT,
    cache_hit BIT DEFAULT 0,
    results_cached_at DATETIME2 NULL,
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_queries_normalized_query')
    CREATE INDEX idx_search_queries_normalized_query ON search_queries (normalized_query);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_queries_location')
    CREATE INDEX idx_search_queries_location ON search_queries (latitude, longitude);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_queries_created')
    CREATE INDEX idx_search_queries_created ON search_queries (created_at);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'search_results')
CREATE TABLE search_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    query_id INT NOT NULL,
    restaurant_id VARCHAR(50) NOT NULL,
    item_id INT NULL,
    
    relevance_score DECIMAL(5,2) DEFAULT 0,
    distance_km DECIMAL(8,2),
    
    CONSTRAINT FK_search_results_query 
        FOREIGN KEY (query_id) REFERENCES search_queries(query_id) ON DELETE CASCADE,
    CONSTRAINT FK_search_results_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT FK_search_results_item 
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_results_query')
    CREATE INDEX idx_search_results_query ON search_results (query_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_search_results_restaurant')
    CREATE INDEX idx_search_results_restaurant ON search_results (restaurant_id);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'popular_searches')
CREATE TABLE popular_searches (
    search_id INT IDENTITY(1,1) PRIMARY KEY,
    search_term NVARCHAR(255) UNIQUE NOT NULL,
    search_count INT DEFAULT 1,
    last_searched DATETIME2 DEFAULT GETDATE(),
    last_seen_at DATETIME2 DEFAULT GETDATE(),
    decay_score DECIMAL(5,2) DEFAULT 1.0
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_popular_searches_count')
    CREATE INDEX idx_popular_searches_count ON popular_searches (search_count DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_popular_searches_term')
    CREATE INDEX idx_popular_searches_term ON popular_searches (search_term);
GO

-- =============================================================================
-- SECTION 4: CHAIN & INTEGRATION TABLES
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'chain_configs')
CREATE TABLE chain_configs (
    chain_id INT IDENTITY(1,1) PRIMARY KEY,
    chain_name VARCHAR(100) UNIQUE NOT NULL,
    root_domain VARCHAR(100),
    
    doordash_enabled BIT DEFAULT 0,
    ubereats_enabled BIT DEFAULT 0,
    yelp_enabled BIT DEFAULT 0,
    grubhub_enabled BIT DEFAULT 0,
    
    menu_endpoints NVARCHAR(MAX) CHECK (ISJSON(menu_endpoints) = 1),
    scraping_allowed BIT DEFAULT 1,
    custom_selectors NVARCHAR(MAX) CHECK (ISJSON(custom_selectors) = 1),
    website_pattern VARCHAR(255),
    logo_url VARCHAR(500),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_chain_configs_name')
    CREATE INDEX idx_chain_configs_name ON chain_configs (chain_name);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_chain_configs_domain')
    CREATE INDEX idx_chain_configs_domain ON chain_configs (root_domain);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'external_menu_data')
CREATE TABLE external_menu_data (
    external_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    
    source_api VARCHAR(20) NOT NULL CHECK (source_api IN ('doordash', 'ubereats', 'yelp', 'grubhub', 'postmates')),
    external_restaurant_id VARCHAR(100),
    entity_type VARCHAR(20) DEFAULT 'restaurant' CHECK (entity_type IN ('restaurant', 'category', 'item')),
    
    menu_data NVARCHAR(MAX) NOT NULL CHECK (ISJSON(menu_data) = 1),
    
    last_updated DATETIME2 DEFAULT GETDATE(),
    is_active BIT DEFAULT 1,
    sync_status VARCHAR(20) DEFAULT 'pending' CHECK (sync_status IN ('pending', 'success', 'failed')),
    
    CONSTRAINT FK_external_menu_data_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);
GO

-- =============================================================================
-- SECTION 5: ANALYTICS TABLES
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_interactions')
CREATE TABLE user_interactions (
    interaction_id INT IDENTITY(1,1) PRIMARY KEY,
    session_hash VARCHAR(64),
    action VARCHAR(30) NOT NULL CHECK (action IN ('search', 'view_restaurant', 'view_menu_item', 'click_website', 'click_phone')),
    query_text VARCHAR(255),
    restaurant_id VARCHAR(50),
    item_id INT,
    user_latitude DECIMAL(10,8),
    user_longitude DECIMAL(11,8),
    device_type VARCHAR(20) DEFAULT 'unknown' CHECK (device_type IN ('web', 'ios', 'android', 'unknown')),
    user_agent NVARCHAR(MAX),
    referrer VARCHAR(500),
    page_load_time_ms INT,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_user_interactions_session')
    CREATE INDEX idx_user_interactions_session ON user_interactions (session_hash);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_user_interactions_action')
    CREATE INDEX idx_user_interactions_action ON user_interactions (action);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_user_interactions_created')
    CREATE INDEX idx_user_interactions_created ON user_interactions (created_at);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'daily_analytics')
CREATE TABLE daily_analytics (
    analytics_id INT IDENTITY(1,1) PRIMARY KEY,
    date_recorded DATE NOT NULL,
    total_searches INT DEFAULT 0,
    unique_sessions INT DEFAULT 0,
    avg_results_per_search DECIMAL(5,2) DEFAULT 0,
    total_restaurant_views INT DEFAULT 0,
    total_menu_item_views INT DEFAULT 0,
    total_website_clicks INT DEFAULT 0,
    avg_search_time_ms INT DEFAULT 0,
    cache_hit_rate DECIMAL(5,2) DEFAULT 0,
    web_users INT DEFAULT 0,
    mobile_users INT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'location_analytics')
CREATE TABLE location_analytics (
    location_id INT IDENTITY(1,1) PRIMARY KEY,
    latitude_center DECIMAL(8,6),
    longitude_center DECIMAL(9,6),
    radius_km DECIMAL(5,2) DEFAULT 1.0,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50) DEFAULT 'US',
    top_search_terms NVARCHAR(MAX) CHECK (ISJSON(top_search_terms) = 1),
    total_searches INT DEFAULT 0,
    unique_users INT DEFAULT 0,
    total_restaurants INT DEFAULT 0,
    restaurants_with_menus INT DEFAULT 0,
    last_updated DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================================================
-- SECTION 6: OPERATIONAL TABLES
-- =============================================================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'system_config')
CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value NVARCHAR(MAX),
    config_type VARCHAR(20) DEFAULT 'string' CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description NVARCHAR(MAX),
    is_public BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'api_usage')
CREATE TABLE api_usage (
    usage_id INT IDENTITY(1,1) PRIMARY KEY,
    api_name VARCHAR(20) NOT NULL CHECK (api_name IN ('google_places', 'doordash', 'ubereats', 'yelp')),
    endpoint VARCHAR(200),
    requests_count INT DEFAULT 1,
    success_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    rate_limit_remaining INT,
    rate_limit_reset_at DATETIME2 NULL,
    estimated_cost DECIMAL(8,4) DEFAULT 0,
    hour_bucket DATETIME2 NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'health_checks')
CREATE TABLE health_checks (
    check_id INT IDENTITY(1,1) PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
    response_time_ms INT,
    error_message NVARCHAR(MAX),
    details NVARCHAR(MAX) CHECK (details IS NULL OR ISJSON(details) = 1),
    alert_sent BIT DEFAULT 0,
    resolved_at DATETIME2 NULL,
    checked_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_health_checks_service_status')
    CREATE INDEX idx_health_checks_service_status ON health_checks (service_name, status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_health_checks_checked')
    CREATE INDEX idx_health_checks_checked ON health_checks (checked_at DESC);
GO

-- =============================================================================
-- SECTION 7: UNIVERSAL SCRAPING QUEUE SYSTEM
-- =============================================================================

-- Drop existing limited scraping_jobs table if it exists
IF OBJECT_ID('scraping_jobs') IS NOT NULL
    DROP TABLE scraping_jobs;
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'universal_scraping_jobs')
CREATE TABLE universal_scraping_jobs (
    job_id INT IDENTITY(1,1) PRIMARY KEY,
    
    job_type VARCHAR(50) NOT NULL,
    job_category VARCHAR(30) NOT NULL DEFAULT 'scraping' CHECK (job_category IN ('scraping', 'api', 'monitoring', 'analysis', 'batch')),
    job_name VARCHAR(255),
    
    target_url VARCHAR(1000),
    target_domain VARCHAR(255),
    target_type VARCHAR(50) DEFAULT 'website',
    
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    
    scraping_config NVARCHAR(MAX) CHECK (scraping_config IS NULL OR ISJSON(scraping_config) = 1),
    extraction_rules NVARCHAR(MAX) CHECK (extraction_rules IS NULL OR ISJSON(extraction_rules) = 1),
    
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'blocked', 'cancelled', 'retry', 'paused')),
    priority INT DEFAULT 50,
    
    scheduled_at DATETIME2 DEFAULT GETDATE(),
    earliest_start_at DATETIME2 DEFAULT GETDATE(),
    started_at DATETIME2 NULL,
    completed_at DATETIME2 NULL,
    
    attempts INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_delay_minutes INT DEFAULT 5,
    next_retry_at DATETIME2 NULL,
    
    last_error_message NVARCHAR(MAX),
    error_code VARCHAR(100),
    error_category VARCHAR(50),
    
    worker_id VARCHAR(100),
    worker_type VARCHAR(50),
    processing_node VARCHAR(100),
    
    estimated_duration_seconds INT DEFAULT 60,
    actual_duration_seconds DECIMAL(8,2),
    
    items_extracted INT DEFAULT 0,
    data_quality_score INT DEFAULT 0,
    success_indicators NVARCHAR(500),
    
    depends_on_job_id INT NULL,
    batch_id VARCHAR(100),
    session_id VARCHAR(100),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    expires_at DATETIME2 NULL,
    
    CONSTRAINT FK_universal_scraping_depends 
        FOREIGN KEY (depends_on_job_id) REFERENCES universal_scraping_jobs(job_id)
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'universal_scraping_results')
CREATE TABLE universal_scraping_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    job_id INT NOT NULL,
    
    result_type VARCHAR(50) NOT NULL,
    data_schema VARCHAR(100),
    
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    completeness_score DECIMAL(3,2) DEFAULT 1.0,
    accuracy_indicators NVARCHAR(MAX) CHECK (accuracy_indicators IS NULL OR ISJSON(accuracy_indicators) = 1),
    
    raw_data NVARCHAR(MAX),
    structured_data NVARCHAR(MAX) CHECK (structured_data IS NULL OR ISJSON(structured_data) = 1),
    summary_data NVARCHAR(MAX) CHECK (summary_data IS NULL OR ISJSON(summary_data) = 1),
    
    data_size_bytes INT DEFAULT 0,
    record_count INT DEFAULT 0,
    unique_fields_found INT DEFAULT 0,
    
    extraction_method VARCHAR(100),
    processing_time_seconds DECIMAL(8,2) DEFAULT 0,
    memory_usage_mb INT DEFAULT 0,
    
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid', 'partial', 'unknown')),
    validation_errors NVARCHAR(MAX),
    verified_at DATETIME2 NULL,
    verified_by VARCHAR(100),
    
    extracted_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_universal_scraping_results_job 
        FOREIGN KEY (job_id) REFERENCES universal_scraping_jobs(job_id) ON DELETE CASCADE
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_job_templates')
CREATE TABLE scraping_job_templates (
    template_id INT IDENTITY(1,1) PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    
    default_config NVARCHAR(MAX) CHECK (default_config IS NULL OR ISJSON(default_config) = 1),
    extraction_rules NVARCHAR(MAX) CHECK (extraction_rules IS NULL OR ISJSON(extraction_rules) = 1),
    
    default_priority INT DEFAULT 50,
    default_max_retries INT DEFAULT 3,
    estimated_duration_seconds INT DEFAULT 60,
    
    description NVARCHAR(MAX),
    created_by VARCHAR(100),
    version VARCHAR(20) DEFAULT '1.0',
    is_active BIT DEFAULT 1,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT UQ_scraping_templates_name UNIQUE (template_name)
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_workers')
CREATE TABLE scraping_workers (
    worker_id VARCHAR(100) PRIMARY KEY,
    worker_name VARCHAR(255) NOT NULL,
    worker_type VARCHAR(50) NOT NULL,
    
    supported_job_types NVARCHAR(MAX) CHECK (supported_job_types IS NULL OR ISJSON(supported_job_types) = 1),
    max_concurrent_jobs INT DEFAULT 1,
    specialization VARCHAR(100),
    
    average_job_duration_seconds INT DEFAULT 60,
    success_rate DECIMAL(3,2) DEFAULT 1.0,
    reliability_score INT DEFAULT 100,
    
    memory_requirement_mb INT DEFAULT 512,
    requires_browser BIT DEFAULT 0,
    requires_proxy BIT DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'error')),
    last_heartbeat DATETIME2 NULL,
    current_jobs INT DEFAULT 0,
    
    config_json NVARCHAR(MAX) CHECK (config_json IS NULL OR ISJSON(config_json) = 1),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_job_history')
CREATE TABLE scraping_job_history (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    job_id INT NOT NULL,
    execution_attempt INT NOT NULL,
    worker_id VARCHAR(100),
    
    started_at DATETIME2 NOT NULL,
    completed_at DATETIME2 NULL,
    duration_seconds DECIMAL(8,2),
    
    status VARCHAR(20) NOT NULL,
    items_found INT DEFAULT 0,
    error_message NVARCHAR(MAX),
    
    cpu_usage_percent DECIMAL(5,2),
    memory_usage_mb INT,
    network_requests INT DEFAULT 0,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_scraping_history_job 
        FOREIGN KEY (job_id) REFERENCES universal_scraping_jobs(job_id) ON DELETE CASCADE
);
GO

-- Create indexes for universal scraping tables
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_status_priority')
    CREATE INDEX idx_universal_scraping_jobs_status_priority ON universal_scraping_jobs (status, priority DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_type_category')
    CREATE INDEX idx_universal_scraping_jobs_type_category ON universal_scraping_jobs (job_type, job_category);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_entity')
    CREATE INDEX idx_universal_scraping_jobs_entity ON universal_scraping_jobs (entity_type, entity_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_domain')
    CREATE INDEX idx_universal_scraping_jobs_domain ON universal_scraping_jobs (target_domain);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_scheduled')
    CREATE INDEX idx_universal_scraping_jobs_scheduled ON universal_scraping_jobs (scheduled_at, earliest_start_at);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_batch')
    CREATE INDEX idx_universal_scraping_jobs_batch ON universal_scraping_jobs (batch_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_session')
    CREATE INDEX idx_universal_scraping_jobs_session ON universal_scraping_jobs (session_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_jobs_worker')
    CREATE INDEX idx_universal_scraping_jobs_worker ON universal_scraping_jobs (worker_id, status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_results_job')
    CREATE INDEX idx_universal_scraping_results_job ON universal_scraping_results (job_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_universal_scraping_results_type')
    CREATE INDEX idx_universal_scraping_results_type ON universal_scraping_results (result_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_templates_type')
    CREATE INDEX idx_scraping_templates_type ON scraping_job_templates (job_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_workers_type')
    CREATE INDEX idx_scraping_workers_type ON scraping_workers (worker_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_workers_status')
    CREATE INDEX idx_scraping_workers_status ON scraping_workers (status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_history_job_attempt')
    CREATE INDEX idx_scraping_history_job_attempt ON scraping_job_history (job_id, execution_attempt);
GO

-- Update trigger for universal_scraping_jobs
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_universal_scraping_jobs_updated_at')
BEGIN
    EXEC('
    CREATE TRIGGER tr_universal_scraping_jobs_updated_at
    ON universal_scraping_jobs
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE universal_scraping_jobs 
        SET updated_at = GETDATE()
        FROM universal_scraping_jobs j
        INNER JOIN inserted i ON j.job_id = i.job_id;
    END');
END
GO

-- =============================================================================
-- SECTION 8: CLOUDDESTROYER EXTENSIONS
-- =============================================================================

-- Add CloudDestroyer-specific columns to existing restaurants table
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('restaurants') AND name = 'clouddestroyer_status')
BEGIN
    ALTER TABLE restaurants ADD 
        clouddestroyer_status VARCHAR(20) DEFAULT 'not_processed' CHECK (clouddestroyer_status IN ('not_processed', 'queued', 'processing', 'success', 'failed', 'blocked', 'no_menu')),
        clouddestroyer_last_attempt DATETIME2 NULL,
        clouddestroyer_attempts INT DEFAULT 0,
        website_type VARCHAR(30) NULL,
        requires_selenium BIT DEFAULT 0,
        api_endpoints_discovered NVARCHAR(MAX) CHECK (api_endpoints_discovered IS NULL OR ISJSON(api_endpoints_discovered) = 1),
        extraction_success_rate DECIMAL(3,2) DEFAULT 0,
        average_extraction_time DECIMAL(8,2) DEFAULT 0,
        best_extraction_method VARCHAR(50) NULL,
        menu_completeness_score INT DEFAULT 0,
        last_successful_extraction DATETIME2 NULL,
        total_items_extracted INT DEFAULT 0,
        
        -- Enhanced menu extraction tracking
        menu_discovery_methods_tried NVARCHAR(MAX) CHECK (menu_discovery_methods_tried IS NULL OR ISJSON(menu_discovery_methods_tried) = 1),
        successful_discovery_method VARCHAR(100) NULL,
        menu_extraction_confidence DECIMAL(3,2) DEFAULT 0,
        raw_content_stored BIT DEFAULT 0,
        structured_items_count INT DEFAULT 0,
        meets_success_threshold BIT DEFAULT 0,
        last_content_hash VARCHAR(64) NULL,
        sitemap_analyzed BIT DEFAULT 0,
        schema_markup_found BIT DEFAULT 0,
        third_party_menu_detected BIT DEFAULT 0;
END
GO

-- Create indexes for CloudDestroyer columns
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_clouddestroyer_status')
    CREATE INDEX idx_restaurants_clouddestroyer_status ON restaurants (clouddestroyer_status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_website_type')
    CREATE INDEX idx_restaurants_website_type ON restaurants (website_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_extraction_success')
    CREATE INDEX idx_restaurants_extraction_success ON restaurants (extraction_success_rate DESC);
GO

-- =============================================================================
-- SECTION 8A: PRICE EXTRACTION TRACKING
-- =============================================================================

-- Add price extraction tracking columns to restaurants table
-- These columns support a helper thread that re-processes restaurants without prices
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('restaurants') AND name = 'prices_extracted')
BEGIN
    ALTER TABLE restaurants ADD 
        -- Core price status
        prices_extracted BIT DEFAULT 0,                                              -- TRUE if any prices were successfully extracted
        items_with_prices INT DEFAULT 0,                                             -- Count of menu items that have price data
        price_extraction_status VARCHAR(20) DEFAULT 'pending'                        -- pending, success, unavailable, failed
            CHECK (price_extraction_status IN ('pending', 'success', 'unavailable', 'failed', 'partial')),
        
        -- Enrichment tracking for helper thread
        price_enrichment_needed BIT DEFAULT 0,                                       -- TRUE if helper thread should attempt price enrichment
        price_enrichment_attempts INT DEFAULT 0,                                     -- Number of enrichment attempts by helper thread
        last_price_enrichment_attempt DATETIME2 NULL,                                -- When helper thread last tried
        
        -- Reason tracking for unavailable prices
        price_unavailable_reason VARCHAR(100) NULL,                                  -- e.g., 'olo_dynamic_pricing', 'requires_location', 'pdf_menu'
        price_source VARCHAR(50) NULL;                                               -- e.g., 'api', 'dom_scrape', 'enriched'
END
GO

-- Index for helper thread to efficiently find restaurants needing price enrichment
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_price_enrichment_needed')
    CREATE INDEX idx_restaurants_price_enrichment_needed 
    ON restaurants (price_enrichment_needed, price_enrichment_attempts, last_price_enrichment_attempt)
    WHERE price_enrichment_needed = 1;
GO

-- Index for querying restaurants by price extraction status
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_restaurants_price_status')
    CREATE INDEX idx_restaurants_price_status ON restaurants (price_extraction_status, prices_extracted);
GO

-- =============================================================================
-- SECTION 9: VIEWS
-- =============================================================================

-- Restaurant scraping status view
IF OBJECT_ID('v_restaurant_scraping_status') IS NOT NULL
    DROP VIEW v_restaurant_scraping_status;
GO

CREATE VIEW v_restaurant_scraping_status AS
SELECT 
    r.restaurant_id,
    r.name as restaurant_name,
    r.website,
    r.clouddestroyer_status,
    r.scrape_status as legacy_scrape_status,
    r.website_type,
    r.extraction_success_rate,
    r.total_items_extracted,
    r.last_successful_extraction,
    j.job_id as current_job_id,
    j.status as current_job_status,
    j.priority as current_job_priority,
    j.attempts as current_job_attempts,
    j.started_at as current_job_started,
    j.worker_id as assigned_worker,
    DATEDIFF(DAY, r.last_successful_extraction, GETDATE()) as days_since_success,
    CASE 
        WHEN r.total_items_extracted > 0 THEN 'Has Menu'
        WHEN r.clouddestroyer_status = 'no_menu' THEN 'No Menu Available'
        WHEN r.clouddestroyer_status IN ('failed', 'blocked') THEN 'Extraction Failed'
        WHEN r.clouddestroyer_status IN ('queued', 'processing') THEN 'In Progress'
        ELSE 'Not Processed'
    END as status_summary,
    (SELECT COUNT(*) FROM menu_items mi WHERE mi.restaurant_id = r.restaurant_id) as current_menu_item_count,
    (SELECT COUNT(DISTINCT category_id) FROM menu_items mi WHERE mi.restaurant_id = r.restaurant_id) as current_category_count
FROM restaurants r
LEFT JOIN universal_scraping_jobs j ON r.restaurant_id = j.entity_id 
    AND j.entity_type = 'restaurant' 
    AND j.status IN ('pending', 'running')
    AND j.job_type = 'clouddestroyer_menu';
GO

-- CloudDestroyer queue view
IF OBJECT_ID('v_clouddestroyer_queue') IS NOT NULL
    DROP VIEW v_clouddestroyer_queue;
GO

CREATE VIEW v_clouddestroyer_queue AS
SELECT 
    j.job_id,
    j.priority,
    j.created_at,
    j.attempts,
    j.max_retries,
    j.next_retry_at,
    r.restaurant_id,
    r.name as restaurant_name,
    r.google_rating,
    r.price_level,
    r.website_type,
    r.clouddestroyer_attempts,
    j.priority + 
    CASE WHEN r.google_rating >= 4.5 THEN 20 WHEN r.google_rating >= 4.0 THEN 10 WHEN r.google_rating >= 3.5 THEN 5 ELSE 0 END +
    CASE WHEN r.website_type IN ('react_spa', 'angular_spa') THEN 15 WHEN r.website_type = 'api_driven' THEN 25 ELSE 0 END +
    CASE WHEN r.clouddestroyer_attempts = 0 THEN 30 WHEN r.clouddestroyer_attempts <= 2 THEN 10 ELSE -10 END
    as effective_priority
FROM universal_scraping_jobs j
INNER JOIN restaurants r ON j.entity_id = r.restaurant_id 
WHERE j.entity_type = 'restaurant' 
AND j.job_type = 'clouddestroyer_menu'
AND j.status IN ('pending', 'retry');
GO

-- Price enrichment queue view for helper thread
IF OBJECT_ID('v_price_enrichment_queue') IS NOT NULL
    DROP VIEW v_price_enrichment_queue;
GO

CREATE VIEW v_price_enrichment_queue AS
SELECT 
    r.restaurant_id,
    r.name AS restaurant_name,
    r.website,
    r.menu_url,
    r.google_rating,
    r.price_level,
    r.website_type,
    r.total_items_extracted,
    r.items_with_prices,
    r.price_extraction_status,
    r.price_unavailable_reason,
    r.price_enrichment_attempts,
    r.last_price_enrichment_attempt,
    r.successful_discovery_method,
    r.api_endpoints_discovered,
    -- Calculate priority score for enrichment
    CASE 
        WHEN r.google_rating >= 4.5 THEN 30 
        WHEN r.google_rating >= 4.0 THEN 20 
        WHEN r.google_rating >= 3.5 THEN 10 
        ELSE 0 
    END +
    CASE 
        WHEN r.total_items_extracted >= 50 THEN 25 
        WHEN r.total_items_extracted >= 20 THEN 15 
        WHEN r.total_items_extracted >= 10 THEN 10 
        ELSE 5 
    END +
    CASE 
        WHEN r.price_enrichment_attempts = 0 THEN 20 
        WHEN r.price_enrichment_attempts = 1 THEN 10 
        ELSE 0 
    END AS enrichment_priority,
    DATEDIFF(HOUR, r.last_price_enrichment_attempt, GETDATE()) AS hours_since_last_attempt
FROM restaurants r
WHERE r.price_enrichment_needed = 1
  AND r.total_items_extracted > 0
  AND r.price_enrichment_attempts < 3
  AND (r.last_price_enrichment_attempt IS NULL 
       OR r.last_price_enrichment_attempt < DATEADD(HOUR, -1, GETDATE()));
GO

-- Price extraction statistics view
IF OBJECT_ID('v_price_extraction_stats') IS NOT NULL
    DROP VIEW v_price_extraction_stats;
GO

CREATE VIEW v_price_extraction_stats AS
SELECT 
    'Price Extraction Overview' AS metric_category,
    COUNT(*) AS total_restaurants_with_menus,
    SUM(CASE WHEN prices_extracted = 1 THEN 1 ELSE 0 END) AS restaurants_with_prices,
    SUM(CASE WHEN price_extraction_status = 'success' THEN 1 ELSE 0 END) AS full_price_success,
    SUM(CASE WHEN price_extraction_status = 'partial' THEN 1 ELSE 0 END) AS partial_prices,
    SUM(CASE WHEN price_extraction_status = 'unavailable' THEN 1 ELSE 0 END) AS prices_unavailable,
    SUM(CASE WHEN price_extraction_status = 'failed' THEN 1 ELSE 0 END) AS price_extraction_failed,
    SUM(CASE WHEN price_enrichment_needed = 1 THEN 1 ELSE 0 END) AS pending_enrichment,
    SUM(items_with_prices) AS total_items_with_prices,
    SUM(total_items_extracted) AS total_menu_items,
    CAST(100.0 * SUM(CASE WHEN prices_extracted = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS price_success_rate_pct
FROM restaurants
WHERE total_items_extracted > 0;
GO

-- =============================================================================
-- SECTION 10: INITIAL DATA
-- =============================================================================

-- System configuration
IF NOT EXISTS (SELECT 1 FROM system_config WHERE config_key = 'app_name')
BEGIN
    INSERT INTO system_config (config_key, config_value, config_type, description, is_public) VALUES
    ('app_name', 'FoodFinder', 'string', 'Application display name', 1),
    ('app_version', '1.0.0', 'string', 'Current application version', 1),
    ('maintenance_mode', 'false', 'boolean', 'Enable maintenance mode', 1),
    ('search_radius_default_km', '10', 'number', 'Default search radius in kilometers', 1),
    ('search_max_results', '50', 'number', 'Maximum results per search', 1),
    ('cache_ttl_hours', '24', 'number', 'Menu data cache time-to-live', 0),
    ('scraping_enabled', 'true', 'boolean', 'Global scraping enable/disable', 0),
    ('max_concurrent_scrapes', '5', 'number', 'Maximum simultaneous scraping jobs', 0),
    ('scraper_rate_limit_ms', '2000', 'number', 'Delay between scraper requests', 0),
    ('scraper_timeout_ms', '30000', 'number', 'Scraper request timeout', 0),
    ('scraper_retry_attempts', '3', 'number', 'Maximum retry attempts for failed scrapes', 0),
    ('enable_chain_detection', 'true', 'boolean', 'Enable automatic chain restaurant detection', 0),
    ('enable_analytics', 'true', 'boolean', 'Enable user analytics tracking', 0),
    ('menu_discovery_max_attempts', '15', 'number', 'Maximum discovery attempts for menu pages', 0),
    ('menu_success_threshold_items', '7', 'number', 'Minimum menu items required for success', 0),
    ('menu_confidence_threshold', '0.7', 'number', 'Minimum confidence score for success', 0),
    ('enable_sitemap_parsing', 'true', 'boolean', 'Enable sitemap.xml parsing for menu discovery', 0),
    ('enable_schema_markup_detection', 'true', 'boolean', 'Enable structured data detection', 0),
    ('enable_third_party_menu_detection', 'true', 'boolean', 'Enable third-party menu service detection', 0),
    ('raw_content_compression', 'true', 'boolean', 'Enable compression for raw menu content storage', 0),
    ('debug_save_raw_html', 'true', 'boolean', 'Save raw HTML for debugging failed extractions', 0);
END
GO

-- Chain configurations
IF NOT EXISTS (SELECT 1 FROM chain_configs WHERE chain_name = 'McDonald''s')
BEGIN
    INSERT INTO chain_configs (chain_name, root_domain, doordash_enabled, ubereats_enabled, yelp_enabled, website_pattern, menu_endpoints, scraping_allowed) VALUES
    ('McDonald''s', 'mcdonalds.com', 1, 1, 1, '.*mcdonalds\\.com.*', '["menu", "us/en-us/full-menu"]', 0),
    ('Burger King', 'bk.com', 1, 1, 1, '.*(bk\\.com|burgerking\\.com).*', '["menu", "food"]', 1),
    ('Wendy''s', 'wendys.com', 1, 1, 1, '.*wendys\\.com.*', '["menu", "food"]', 1),
    ('Pizza Hut', 'pizzahut.com', 1, 1, 1, '.*pizzahut\\.com.*', '["menu", "order"]', 1),
    ('Domino''s', 'dominos.com', 1, 1, 1, '.*dominos\\.com.*', '["menu", "en/pages/order"]', 0),
    ('Subway', 'subway.com', 1, 0, 1, '.*subway\\.com.*', '["menu", "en-us/menunutrition/menu"]', 1),
    ('Taco Bell', 'tacobell.com', 1, 1, 1, '.*tacobell\\.com.*', '["food"]', 1),
    ('KFC', 'kfc.com', 1, 1, 1, '.*kfc\\.com.*', '["menu"]', 1),
    ('Chipotle', 'chipotle.com', 1, 1, 1, '.*chipotle\\.com.*', '["menu"]', 0),
    ('Starbucks', 'starbucks.com', 1, 1, 1, '.*starbucks\\.com.*', '["menu"]', 0);
END
GO

-- Popular searches
IF NOT EXISTS (SELECT 1 FROM popular_searches WHERE search_term = 'burger')
BEGIN
    INSERT INTO popular_searches (search_term, search_count) VALUES
    ('burger', 150), ('pizza', 120), ('chicken', 100), ('tacos', 85), ('fries', 75),
    ('sandwich', 70), ('salad', 65), ('wings', 60), ('nuggets', 55), ('burrito', 50),
    ('pasta', 45), ('steak', 40), ('fish', 35), ('soup', 30), ('dessert', 25),
    ('coffee', 80), ('breakfast', 90), ('lunch', 75), ('dinner', 85), ('appetizer', 40);
END
GO

-- Health checks
IF NOT EXISTS (SELECT 1 FROM health_checks WHERE service_name = 'Database')
BEGIN
    INSERT INTO health_checks (service_name, status, response_time_ms) VALUES
    ('Database', 'healthy', 15),
    ('Menu Scraper', 'healthy', 250),
    ('File Storage', 'healthy', 8);
END
GO

-- Scraping job templates
IF NOT EXISTS (SELECT 1 FROM scraping_job_templates WHERE template_name = 'CloudDestroyer Restaurant Menu')
BEGIN
    INSERT INTO scraping_job_templates (
        template_name, job_type, description, default_priority, default_max_retries,
        estimated_duration_seconds, default_config, extraction_rules, created_by, version
    )
    VALUES (
        'CloudDestroyer Restaurant Menu',
        'clouddestroyer_menu', 
        'Extract restaurant menu using CloudDestroyer with Cloudflare bypass, API discovery, and Selenium fallback',
        70, 3, 120,
        '{"extraction_type": "restaurant_menu", "use_clouddestroyer": true, "bypass_cloudflare": true, "discover_api_endpoints": true, "selenium_fallback": true, "parse_spa": true, "headless_browser": true, "timeout_seconds": 180}',
        '{"api_patterns": ["/api/.*menu.*", "/api/olo/.*", "/api/.*food.*"], "dom_selectors": [".menu-item", ".menu-product", ".dish", ".food-item"], "price_patterns": ["\\\\$\\\\d+\\\\.\\\\d{2}", "\\\\$\\\\d+"], "required_fields": ["name"], "min_confidence": 0.7}',
        'CloudDestroyer_System', '1.0'
    );
    
    INSERT INTO scraping_job_templates (
        template_name, job_type, description, default_priority, default_max_retries,
        estimated_duration_seconds, default_config, extraction_rules, created_by, version
    )
    VALUES (
        'Generic API Endpoint',
        'api_endpoint',
        'Generic API endpoint data extraction with authentication and rate limiting', 
        50, 2, 30,
        '{"method": "GET", "headers": {"User-Agent": "FoodFinder-Bot/1.0"}, "timeout_seconds": 30, "follow_redirects": true, "verify_ssl": true}',
        '{"response_format": "json", "required_status_codes": [200, 201], "data_path": "$", "pagination_support": false}',
        'FoodFinder_System', '1.0'
    );
END
GO

-- Scraping workers
IF NOT EXISTS (SELECT 1 FROM scraping_workers WHERE worker_id = 'clouddestroyer_primary')
BEGIN
    INSERT INTO scraping_workers (
        worker_id, worker_name, worker_type, specialization,
        supported_job_types, max_concurrent_jobs, requires_browser,
        memory_requirement_mb, average_job_duration_seconds, config_json, status
    )
    VALUES (
        'clouddestroyer_primary', 'CloudDestroyer Primary Worker', 'clouddestroyer', 'restaurant_menus',
        '["clouddestroyer_menu", "api_endpoint"]', 3, 1, 1024, 120,
        '{"headless_browser": true, "session_persistence": true, "max_retries": 3, "timeout": 180}', 'active'
    );
    
    INSERT INTO scraping_workers (
        worker_id, worker_name, worker_type, specialization,
        supported_job_types, max_concurrent_jobs, requires_browser,
        memory_requirement_mb, average_job_duration_seconds, config_json, status
    )
    VALUES (
        'api_client_primary', 'Generic API Client', 'api_client', 'api_endpoints',
        '["api_endpoint", "content_monitor", "price_tracker"]', 10, 0, 256, 30,
        '{"rate_limit_requests_per_minute": 60, "connection_pool_size": 10, "timeout_seconds": 30}', 'active'
    );
END
GO

-- =============================================================================
-- SECTION 11: CORE STORED PROCEDURES
-- =============================================================================

-- Insert or update restaurant data
IF OBJECT_ID('sp_UpsertRestaurant') IS NOT NULL DROP PROCEDURE sp_UpsertRestaurant;
GO

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
        IF @Latitude < -90 OR @Latitude > 90
            RAISERROR('Invalid latitude. Must be between -90 and 90.', 16, 1);
        IF @Longitude < -180 OR @Longitude > 180
            RAISERROR('Invalid longitude. Must be between -180 and 180.', 16, 1);
        IF @PriceLevel IS NOT NULL AND (@PriceLevel < 1 OR @PriceLevel > 4)
            RAISERROR('Invalid price level. Must be between 1 and 4.', 16, 1);
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
                name = source.name, address = source.address, phone = source.phone,
                website = source.website, menu_url = source.menu_url,
                google_rating = source.google_rating, price_level = source.price_level,
                latitude = source.latitude, longitude = source.longitude,
                timezone = source.timezone, hours_json = source.hours_json,
                is_chain = source.is_chain, chain_name = source.chain_name,
                updated_at = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (restaurant_id, name, address, phone, website, menu_url,
                   google_rating, price_level, latitude, longitude, timezone,
                   hours_json, is_chain, chain_name, created_at, updated_at)
            VALUES (source.restaurant_id, source.name, source.address, source.phone,
                   source.website, source.menu_url, source.google_rating,
                   source.price_level, source.latitude, source.longitude, source.timezone,
                   source.hours_json, source.is_chain, source.chain_name, GETDATE(), GETDATE());
                   
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

-- =============================================================================
-- SECTION 12: UNIVERSAL SCRAPING PROCEDURES
-- =============================================================================

-- Create a new scraping job
IF OBJECT_ID('spsc_CreateJob') IS NOT NULL DROP PROCEDURE spsc_CreateJob;
GO

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
        IF @JobType IS NULL OR @TargetUrl IS NULL
        BEGIN
            RAISERROR('JobType and TargetUrl are required', 16, 1);
            RETURN;
        END
        
        DECLARE @Domain VARCHAR(255);
        SET @Domain = CASE 
            WHEN CHARINDEX('://', @TargetUrl) > 0 THEN
                SUBSTRING(@TargetUrl, CHARINDEX('://', @TargetUrl) + 3, 
                         CHARINDEX('/', @TargetUrl + '/', CHARINDEX('://', @TargetUrl) + 3) - CHARINDEX('://', @TargetUrl) - 3)
            ELSE @TargetUrl
        END;
        
        IF @JobName IS NULL
            SET @JobName = @JobType + ' - ' + @Domain;
        
        IF EXISTS (SELECT 1 FROM universal_scraping_jobs WHERE job_type = @JobType AND target_url = @TargetUrl AND status IN ('pending', 'running'))
        BEGIN
            SELECT @JobId = job_id FROM universal_scraping_jobs WHERE job_type = @JobType AND target_url = @TargetUrl AND status IN ('pending', 'running');
            RETURN;
        END
        
        INSERT INTO universal_scraping_jobs (job_type, job_name, target_url, target_domain, entity_type, entity_id, priority, scraping_config, batch_id, session_id, created_at)
        VALUES (@JobType, @JobName, @TargetUrl, @Domain, @EntityType, @EntityId, @Priority, @ScrapingConfig, @BatchId, @SessionId, GETDATE());
        
        SET @JobId = SCOPE_IDENTITY();
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- Get next job from queue
IF OBJECT_ID('spsc_GetNextJob') IS NOT NULL DROP PROCEDURE spsc_GetNextJob;
GO

CREATE PROCEDURE spsc_GetNextJob
    @WorkerId VARCHAR(100),
    @WorkerType VARCHAR(50),
    @SupportedJobTypes VARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @JobId INT = NULL;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        UPDATE scraping_workers SET last_heartbeat = GETDATE(), current_jobs = current_jobs + 1 WHERE worker_id = @WorkerId;
        
        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO scraping_workers (worker_id, worker_name, worker_type, supported_job_types, last_heartbeat, current_jobs)
            VALUES (@WorkerId, @WorkerId, @WorkerType,
                CASE WHEN @SupportedJobTypes IS NOT NULL THEN '["' + REPLACE(@SupportedJobTypes, ',', '","') + '"]' ELSE NULL END,
                GETDATE(), 1);
        END
        
        SELECT TOP 1 @JobId = job_id FROM universal_scraping_jobs
        WHERE status = 'pending'
        AND (earliest_start_at IS NULL OR earliest_start_at <= GETDATE())
        AND (next_retry_at IS NULL OR next_retry_at <= GETDATE())
        AND (@SupportedJobTypes IS NULL OR job_type IN (SELECT TRIM(value) FROM STRING_SPLIT(@SupportedJobTypes, ',')))
        ORDER BY priority DESC, created_at ASC;
        
        IF @JobId IS NOT NULL
        BEGIN
            UPDATE universal_scraping_jobs SET status = 'running', worker_id = @WorkerId, worker_type = @WorkerType, started_at = GETDATE(), attempts = attempts + 1 WHERE job_id = @JobId;
            
            INSERT INTO scraping_job_history (job_id, execution_attempt, worker_id, started_at, status)
            VALUES (@JobId, (SELECT attempts FROM universal_scraping_jobs WHERE job_id = @JobId), @WorkerId, GETDATE(), 'running');
            
            SELECT j.job_id, j.job_type, j.job_name, j.target_url, j.target_domain, j.entity_type, j.entity_id, j.scraping_config, j.extraction_rules, j.priority, j.attempts, j.max_retries, j.estimated_duration_seconds, j.batch_id, j.session_id, t.default_config, t.extraction_rules as template_rules
            FROM universal_scraping_jobs j
            LEFT JOIN scraping_job_templates t ON j.job_type = t.job_type AND t.is_active = 1
            WHERE j.job_id = @JobId;
        END
        
        COMMIT TRANSACTION;
        
    END TRY
    BEGIN CATCH
        IF XACT_STATE() != 0 ROLLBACK TRANSACTION;
        UPDATE scraping_workers SET current_jobs = current_jobs - 1 WHERE worker_id = @WorkerId;
        THROW;
    END CATCH
END;
GO

-- Complete scraping job
IF OBJECT_ID('spsc_CompleteJob') IS NOT NULL DROP PROCEDURE spsc_CompleteJob;
GO

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
        
        SELECT @WorkerId = worker_id FROM universal_scraping_jobs WHERE job_id = @JobId;
        
        IF @Status IN ('failed', 'blocked')
        BEGIN
            DECLARE @Attempts INT, @MaxRetries INT, @RetryDelayMinutes INT;
            SELECT @Attempts = attempts, @MaxRetries = max_retries, @RetryDelayMinutes = retry_delay_minutes FROM universal_scraping_jobs WHERE job_id = @JobId;
            
            IF @Attempts < @MaxRetries
            BEGIN
                SET @ShouldRetry = 1;
                SET @Status = 'retry';
                SET @NextRetryAt = DATEADD(MINUTE, @RetryDelayMinutes * POWER(2, @Attempts - 1), GETDATE());
            END
        END
        
        UPDATE universal_scraping_jobs
        SET status = @Status, items_extracted = @ItemsExtracted, actual_duration_seconds = @ProcessingTimeSeconds,
            last_error_message = @ErrorMessage, error_code = @ErrorCode,
            completed_at = CASE WHEN @Status IN ('completed', 'failed', 'cancelled') THEN GETDATE() ELSE NULL END,
            next_retry_at = @NextRetryAt,
            data_quality_score = CASE WHEN @Status = 'completed' THEN CAST(@ConfidenceScore * 100 AS INT) ELSE 0 END
        WHERE job_id = @JobId;
        
        IF (@RawData IS NOT NULL OR @StructuredData IS NOT NULL) AND @Status = 'completed'
        BEGIN
            DECLARE @ResultType VARCHAR(50) = 'extracted_data';
            SELECT @ResultType = CASE WHEN job_type LIKE '%menu%' THEN 'menu_data' WHEN job_type LIKE '%api%' THEN 'api_response' ELSE 'extracted_data' END FROM universal_scraping_jobs WHERE job_id = @JobId;
            
            INSERT INTO universal_scraping_results (job_id, result_type, confidence_score, raw_data, structured_data, data_size_bytes, record_count, processing_time_seconds, extracted_at)
            VALUES (@JobId, @ResultType, @ConfidenceScore, @RawData, @StructuredData, LEN(ISNULL(@RawData, '') + ISNULL(@StructuredData, '')), @ItemsExtracted, @ProcessingTimeSeconds, GETDATE());
        END
        
        UPDATE scraping_job_history SET completed_at = GETDATE(), duration_seconds = @ProcessingTimeSeconds, status = @Status, items_found = @ItemsExtracted, error_message = @ErrorMessage
        WHERE job_id = @JobId AND completed_at IS NULL AND worker_id = @WorkerId;
        
        UPDATE scraping_workers SET current_jobs = current_jobs - 1, last_heartbeat = GETDATE() WHERE worker_id = @WorkerId;
        
        SELECT @JobId as job_id, @Status as final_status, @ItemsExtracted as items_extracted, @ShouldRetry as will_retry, @NextRetryAt as next_retry_at;
        
    END TRY
    BEGIN CATCH
        UPDATE scraping_workers SET current_jobs = current_jobs - 1 WHERE worker_id = @WorkerId;
        THROW;
    END CATCH
END;
GO

-- CloudDestroyer restaurant job creation
IF OBJECT_ID('spcd_CreateRestaurantJob') IS NOT NULL DROP PROCEDURE spcd_CreateRestaurantJob;
GO

CREATE PROCEDURE spcd_CreateRestaurantJob
    @RestaurantId VARCHAR(50),
    @TargetUrl VARCHAR(1000) = NULL,
    @Priority INT = 70,
    @SessionId VARCHAR(100) = NULL,
    @JobId INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM restaurants WHERE restaurant_id = @RestaurantId)
        BEGIN
            RAISERROR('Restaurant not found: %s', 16, 1, @RestaurantId);
            RETURN;
        END
        
        DECLARE @RestaurantName VARCHAR(255);
        DECLARE @Website VARCHAR(500);
        
        SELECT @RestaurantName = name, @Website = ISNULL(@TargetUrl, ISNULL(menu_url, website)) FROM restaurants WHERE restaurant_id = @RestaurantId;
        
        IF @Website IS NULL
        BEGIN
            RAISERROR('No website URL found for restaurant: %s', 16, 1, @RestaurantId);
            RETURN;
        END
        
        DECLARE @Config NVARCHAR(MAX) = '{"extraction_type": "restaurant_menu", "use_selenium": "auto", "bypass_cloudflare": true, "discover_api_endpoints": true, "parse_spa": true}';
        
        EXEC spsc_CreateJob @JobType = 'clouddestroyer_menu', @TargetUrl = @Website, @JobName = 'Extract Menu', @EntityType = 'restaurant', @EntityId = @RestaurantId, @Priority = @Priority, @ScrapingConfig = @Config, @SessionId = @SessionId, @JobId = @JobId OUTPUT;
        
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Process CloudDestroyer menu results
IF OBJECT_ID('spcd_ProcessMenuResult') IS NOT NULL DROP PROCEDURE spcd_ProcessMenuResult;
GO

CREATE PROCEDURE spcd_ProcessMenuResult
    @JobId INT,
    @MenuData NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ItemsInserted INT = 0;
    DECLARE @CategoriesCreated INT = 0;
    DECLARE @RestaurantId VARCHAR(50);
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        SELECT @RestaurantId = entity_id FROM universal_scraping_jobs WHERE job_id = @JobId AND entity_type = 'restaurant';
        
        IF @RestaurantId IS NULL
        BEGIN
            RAISERROR('Invalid job or restaurant not found', 16, 1);
            RETURN;
        END
        
        -- Insert categories
        INSERT INTO menu_categories (restaurant_id, name, description, display_order, source, external_category_id)
        SELECT DISTINCT @RestaurantId, JSON_VALUE(value, '$.name'), JSON_VALUE(value, '$.description'), 0, 'scraped', JSON_VALUE(value, '$.id')
        FROM OPENJSON(@MenuData, '$.categories')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM menu_categories mc WHERE mc.restaurant_id = @RestaurantId AND mc.name = JSON_VALUE(value, '$.name'));
        
        SET @CategoriesCreated = @@ROWCOUNT;
        
        -- Insert menu items
        INSERT INTO menu_items (restaurant_id, category_id, name, normalized_name, description, price, external_item_id, source, confidence_score, search_tokens, is_available)
        SELECT @RestaurantId, mc.category_id, JSON_VALUE(value, '$.name'), LOWER(REPLACE(JSON_VALUE(value, '$.name'), ' ', '')), JSON_VALUE(value, '$.description'),
            CASE WHEN ISNUMERIC(JSON_VALUE(value, '$.base_price')) = 1 THEN CAST(JSON_VALUE(value, '$.base_price') AS DECIMAL(8,2)) ELSE NULL END,
            JSON_VALUE(value, '$.id'), 'scraped', 90,
            LOWER(JSON_VALUE(value, '$.name') + ' ' + ISNULL(JSON_VALUE(value, '$.description'), '')), 1
        FROM OPENJSON(@MenuData, '$.all_items')
        LEFT JOIN menu_categories mc ON mc.restaurant_id = @RestaurantId AND mc.name = JSON_VALUE(value, '$.category')
        WHERE JSON_VALUE(value, '$.name') IS NOT NULL AND LEN(JSON_VALUE(value, '$.name')) > 2
        AND NOT EXISTS (SELECT 1 FROM menu_items mi WHERE mi.restaurant_id = @RestaurantId AND mi.name = JSON_VALUE(value, '$.name'));
        
        SET @ItemsInserted = @@ROWCOUNT;
        
        UPDATE restaurants SET scrape_status = CASE WHEN @ItemsInserted > 0 THEN 'success' ELSE 'no_menu' END, last_scraped_at = GETDATE(), updated_at = GETDATE() WHERE restaurant_id = @RestaurantId;
        
        COMMIT TRANSACTION;
        
        SELECT @RestaurantId AS restaurant_id, @ItemsInserted AS items_inserted, @CategoriesCreated AS categories_created, 'success' AS status;
        
    END TRY
    BEGIN CATCH
        IF XACT_STATE() != 0 ROLLBACK TRANSACTION;
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- =============================================================================
-- SECTION 12A: RAW MENU CONTENT PROCEDURES
-- =============================================================================

-- Store raw menu content with comprehensive analysis
IF OBJECT_ID('sp_StoreRawMenuContent') IS NOT NULL DROP PROCEDURE sp_StoreRawMenuContent;
GO

CREATE PROCEDURE sp_StoreRawMenuContent
    @RestaurantId VARCHAR(50),
    @ContentHtml NVARCHAR(MAX) = NULL,
    @ContentText NVARCHAR(MAX) = NULL,
    @ContentJson NVARCHAR(MAX) = NULL,
    @ExtractionUrl VARCHAR(1000) = NULL,
    @ExtractionMethod VARCHAR(100),
    @DiscoveryAttemptsLog NVARCHAR(MAX) = NULL,
    @ContentId INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Validate input
        IF @RestaurantId IS NULL OR @ExtractionMethod IS NULL
        BEGIN
            RAISERROR('RestaurantId and ExtractionMethod are required', 16, 1);
            RETURN;
        END
        
        IF NOT EXISTS (SELECT 1 FROM restaurants WHERE restaurant_id = @RestaurantId)
        BEGIN
            RAISERROR('Restaurant not found: %s', 16, 1, @RestaurantId);
            RETURN;
        END
        
        -- Analyze content for quality metrics
        DECLARE @TotalContentLength INT = 0;
        DECLARE @MenuIndicatorsFound INT = 0;
        DECLARE @PricePatternsCount INT = 0;
        DECLARE @FoodCategoriesDetected INT = 0;
        DECLARE @ExtractionConfidence DECIMAL(3,2) = 0;
        
        -- Calculate content length
        SET @TotalContentLength = LEN(ISNULL(@ContentHtml, '')) + LEN(ISNULL(@ContentText, '')) + LEN(ISNULL(@ContentJson, ''));
        
        -- Analyze content for menu indicators if text content is provided
        IF @ContentText IS NOT NULL
        BEGIN
            -- Count menu indicator words
            DECLARE @ContentLower NVARCHAR(MAX) = LOWER(@ContentText);
            
            -- Menu indicators
            IF @ContentLower LIKE '%menu%' SET @MenuIndicatorsFound = @MenuIndicatorsFound + 1;
            IF @ContentLower LIKE '%appetizer%' OR @ContentLower LIKE '%starter%' SET @MenuIndicatorsFound = @MenuIndicatorsFound + 1;
            IF @ContentLower LIKE '%entree%' OR @ContentLower LIKE '%main%' SET @MenuIndicatorsFound = @MenuIndicatorsFound + 1;
            IF @ContentLower LIKE '%dessert%' SET @MenuIndicatorsFound = @MenuIndicatorsFound + 1;
            IF @ContentLower LIKE '%beverage%' OR @ContentLower LIKE '%drink%' SET @MenuIndicatorsFound = @MenuIndicatorsFound + 1;
            
            -- Food categories
            IF @ContentLower LIKE '%burger%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%pizza%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%sandwich%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%salad%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%pasta%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%chicken%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%steak%' OR @ContentLower LIKE '%beef%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            IF @ContentLower LIKE '%seafood%' OR @ContentLower LIKE '%fish%' SET @FoodCategoriesDetected = @FoodCategoriesDetected + 1;
            
            -- Estimate price patterns (approximate count)
            SET @PricePatternsCount = (LEN(@ContentText) - LEN(REPLACE(@ContentText, '$', '')));
        END
        
        -- Calculate confidence score
        SET @ExtractionConfidence = CASE
            WHEN @TotalContentLength > 10000 AND @MenuIndicatorsFound >= 3 AND @FoodCategoriesDetected >= 4 THEN 0.9
            WHEN @TotalContentLength > 5000 AND @MenuIndicatorsFound >= 2 AND @FoodCategoriesDetected >= 2 THEN 0.7
            WHEN @TotalContentLength > 2000 AND @MenuIndicatorsFound >= 1 THEN 0.5
            WHEN @TotalContentLength > 500 THEN 0.3
            ELSE 0.1
        END;
        
        -- Determine if meets success threshold (7+ potential menu items)
        DECLARE @MeetsSuccessThreshold BIT = CASE
            WHEN @FoodCategoriesDetected >= 4 AND @PricePatternsCount >= 7 AND @ExtractionConfidence >= 0.7 THEN 1
            ELSE 0
        END;
        
        -- Insert raw content record
        INSERT INTO raw_menu_content (
            restaurant_id, content_html, content_text, content_json,
            extraction_url, extraction_method, total_content_length,
            menu_indicators_found, price_patterns_count, food_categories_detected,
            extraction_confidence, meets_success_threshold, discovery_attempts_log
        )
        VALUES (
            @RestaurantId, @ContentHtml, @ContentText, @ContentJson,
            @ExtractionUrl, @ExtractionMethod, @TotalContentLength,
            @MenuIndicatorsFound, @PricePatternsCount, @FoodCategoriesDetected,
            @ExtractionConfidence, @MeetsSuccessThreshold, @DiscoveryAttemptsLog
        );
        
        SET @ContentId = SCOPE_IDENTITY();
        
        -- Update restaurant tracking
        UPDATE restaurants 
        SET raw_content_stored = 1,
            menu_extraction_confidence = @ExtractionConfidence,
            meets_success_threshold = @MeetsSuccessThreshold,
            last_successful_extraction = CASE WHEN @MeetsSuccessThreshold = 1 THEN GETDATE() ELSE last_successful_extraction END,
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
        SELECT @ContentId as content_id, @ExtractionConfidence as confidence_score, @MeetsSuccessThreshold as meets_threshold;
        
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Log menu extraction attempt
IF OBJECT_ID('sp_LogExtractionAttempt') IS NOT NULL DROP PROCEDURE sp_LogExtractionAttempt;
GO

CREATE PROCEDURE sp_LogExtractionAttempt
    @RestaurantId VARCHAR(50),
    @AttemptNumber INT,
    @DiscoveryMethod VARCHAR(100),
    @TargetUrl VARCHAR(1000) = NULL,
    @Status VARCHAR(20),
    @ResponseTimeMs INT = 0,
    @ContentLength INT = 0,
    @MenuScore INT = 0,
    @ConfidenceScore DECIMAL(3,2) = 0,
    @MenuItemsFound INT = 0,
    @PricePatternsFound INT = 0,
    @CategoriesFound INT = 0,
    @ErrorMessage NVARCHAR(MAX) = NULL,
    @RawResponseSnippet NVARCHAR(1000) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        INSERT INTO menu_extraction_attempts (
            restaurant_id, attempt_number, discovery_method, target_url, status,
            response_time_ms, content_length, menu_score, confidence_score,
            menu_items_found, price_patterns_found, categories_found,
            error_message, raw_response_snippet
        )
        VALUES (
            @RestaurantId, @AttemptNumber, @DiscoveryMethod, @TargetUrl, @Status,
            @ResponseTimeMs, @ContentLength, @MenuScore, @ConfidenceScore,
            @MenuItemsFound, @PricePatternsFound, @CategoriesFound,
            @ErrorMessage, @RawResponseSnippet
        );
        
        -- Update restaurant attempt tracking
        UPDATE restaurants 
        SET clouddestroyer_attempts = @AttemptNumber,
            clouddestroyer_last_attempt = GETDATE(),
            successful_discovery_method = CASE WHEN @Status = 'success' THEN @DiscoveryMethod ELSE successful_discovery_method END,
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
    END TRY
    BEGIN CATCH
        -- Log error but don't fail the main extraction process
        PRINT 'Warning: Failed to log extraction attempt: ' + ERROR_MESSAGE();
    END CATCH
END;
GO

-- Process raw menu content into structured items
IF OBJECT_ID('sp_ProcessRawMenuContent') IS NOT NULL DROP PROCEDURE sp_ProcessRawMenuContent;
GO

CREATE PROCEDURE sp_ProcessRawMenuContent
    @ContentId INT,
    @StructuredMenuData NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ItemsInserted INT = 0;
    DECLARE @CategoriesCreated INT = 0;
    DECLARE @RestaurantId VARCHAR(50);
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Get restaurant ID from content record
        SELECT @RestaurantId = restaurant_id 
        FROM raw_menu_content 
        WHERE content_id = @ContentId;
        
        IF @RestaurantId IS NULL
        BEGIN
            RAISERROR('Content record not found or invalid', 16, 1);
            RETURN;
        END
        
        -- Process categories if they exist in the structured data
        IF JSON_QUERY(@StructuredMenuData, '$.categories') IS NOT NULL
        BEGIN
            INSERT INTO menu_categories (restaurant_id, name, description, display_order, source)
            SELECT DISTINCT 
                @RestaurantId, 
                JSON_VALUE(value, '$.name'), 
                JSON_VALUE(value, '$.description'),
                ISNULL(JSON_VALUE(value, '$.order'), 0),
                'scraped'
            FROM OPENJSON(@StructuredMenuData, '$.categories')
            WHERE JSON_VALUE(value, '$.name') IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM menu_categories mc 
                WHERE mc.restaurant_id = @RestaurantId 
                AND mc.name = JSON_VALUE(value, '$.name')
            );
            
            SET @CategoriesCreated = @@ROWCOUNT;
        END
        
        -- Process menu items
        INSERT INTO menu_items (
            restaurant_id, category_id, name, normalized_name, description, 
            price, price_text, external_item_id, source, confidence_score, 
            search_tokens, is_available
        )
        SELECT 
            @RestaurantId,
            mc.category_id,
            JSON_VALUE(value, '$.name'),
            LOWER(REPLACE(JSON_VALUE(value, '$.name'), ' ', '')),
            JSON_VALUE(value, '$.description'),
            CASE 
                WHEN ISNUMERIC(JSON_VALUE(value, '$.price')) = 1 
                THEN CAST(JSON_VALUE(value, '$.price') AS DECIMAL(8,2)) 
                ELSE NULL 
            END,
            JSON_VALUE(value, '$.price_text'),
            JSON_VALUE(value, '$.id'),
            'scraped',
            ISNULL(CAST(JSON_VALUE(value, '$.confidence') AS INT), 85),
            LOWER(JSON_VALUE(value, '$.name') + ' ' + ISNULL(JSON_VALUE(value, '$.description'), '')),
            ISNULL(CAST(JSON_VALUE(value, '$.available') AS BIT), 1)
        FROM OPENJSON(@StructuredMenuData, '$.items')
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
        
        -- Update raw content processing status
        UPDATE raw_menu_content 
        SET processing_status = 'processed',
            structured_items_created = @ItemsInserted,
            last_processed_at = GETDATE(),
            parsing_success = CASE WHEN @ItemsInserted > 0 THEN 1 ELSE 0 END
        WHERE content_id = @ContentId;
        
        -- Update restaurant statistics
        UPDATE restaurants 
        SET structured_items_count = (
                SELECT COUNT(*) FROM menu_items 
                WHERE restaurant_id = @RestaurantId
            ),
            meets_success_threshold = CASE 
                WHEN (
                    SELECT COUNT(*) FROM menu_items 
                    WHERE restaurant_id = @RestaurantId 
                    AND price IS NOT NULL
                ) >= 7 THEN 1 
                ELSE 0 
            END,
            clouddestroyer_status = CASE 
                WHEN @ItemsInserted >= 7 THEN 'success'
                WHEN @ItemsInserted > 0 THEN 'success'
                ELSE 'no_menu'
            END,
            total_items_extracted = (
                SELECT COUNT(*) FROM menu_items 
                WHERE restaurant_id = @RestaurantId
            ),
            last_scraped_at = GETDATE(),
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
        COMMIT TRANSACTION;
        
        SELECT 
            @RestaurantId AS restaurant_id, 
            @ItemsInserted AS items_inserted, 
            @CategoriesCreated AS categories_created,
            'success' AS status;
        
    END TRY
    BEGIN CATCH
        IF XACT_STATE() != 0 ROLLBACK TRANSACTION;
        
        -- Update processing status to failed
        UPDATE raw_menu_content 
        SET processing_status = 'failed',
            error_details = ERROR_MESSAGE(),
            last_processed_at = GETDATE()
        WHERE content_id = @ContentId;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Get menu extraction statistics
IF OBJECT_ID('sp_GetMenuExtractionStats') IS NOT NULL DROP PROCEDURE sp_GetMenuExtractionStats;
GO

CREATE PROCEDURE sp_GetMenuExtractionStats
    @RestaurantId VARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Restaurant-specific stats if ID provided
    IF @RestaurantId IS NOT NULL
    BEGIN
        SELECT 
            r.restaurant_id,
            r.name,
            r.clouddestroyer_status,
            r.clouddestroyer_attempts,
            r.successful_discovery_method,
            r.menu_extraction_confidence,
            r.structured_items_count,
            r.meets_success_threshold,
            r.last_successful_extraction,
            (
                SELECT COUNT(*) FROM raw_menu_content 
                WHERE restaurant_id = r.restaurant_id
            ) AS raw_content_records,
            (
                SELECT COUNT(*) FROM menu_extraction_attempts 
                WHERE restaurant_id = r.restaurant_id
            ) AS total_attempts,
            (
                SELECT COUNT(*) FROM menu_extraction_attempts 
                WHERE restaurant_id = r.restaurant_id AND status = 'success'
            ) AS successful_attempts
        FROM restaurants r
        WHERE r.restaurant_id = @RestaurantId;
        
        -- Recent attempts for this restaurant
        SELECT TOP 10
            attempt_number, discovery_method, status, confidence_score,
            menu_items_found, attempted_at
        FROM menu_extraction_attempts
        WHERE restaurant_id = @RestaurantId
        ORDER BY attempted_at DESC;
    END
    ELSE
    BEGIN
        -- Overall system stats
        SELECT 
            'Overall Statistics' AS metric_category,
            COUNT(*) AS total_restaurants,
            SUM(CASE WHEN clouddestroyer_status = 'success' THEN 1 ELSE 0 END) AS successful_extractions,
            SUM(CASE WHEN meets_success_threshold = 1 THEN 1 ELSE 0 END) AS meets_threshold_count,
            AVG(CAST(menu_extraction_confidence AS FLOAT)) AS avg_confidence,
            SUM(structured_items_count) AS total_menu_items,
            AVG(CAST(structured_items_count AS FLOAT)) AS avg_items_per_restaurant
        FROM restaurants
        WHERE clouddestroyer_status IS NOT NULL;
        
        -- Method effectiveness
        SELECT 
            successful_discovery_method,
            COUNT(*) AS usage_count,
            AVG(CAST(menu_extraction_confidence AS FLOAT)) AS avg_confidence,
            AVG(CAST(structured_items_count AS FLOAT)) AS avg_items_found
        FROM restaurants
        WHERE successful_discovery_method IS NOT NULL
        GROUP BY successful_discovery_method
        ORDER BY usage_count DESC;
    END
END;
GO

-- =============================================================================
-- SECTION 12B: PRICE EXTRACTION PROCEDURES
-- =============================================================================

-- Update price extraction status for a restaurant after menu extraction
IF OBJECT_ID('sp_UpdatePriceExtractionStatus') IS NOT NULL DROP PROCEDURE sp_UpdatePriceExtractionStatus;
GO

CREATE PROCEDURE sp_UpdatePriceExtractionStatus
    @RestaurantId VARCHAR(50),
    @ItemsWithPrices INT,
    @TotalItems INT,
    @PriceSource VARCHAR(50) = NULL,           -- 'api', 'dom_scrape', 'enriched'
    @PriceUnavailableReason VARCHAR(100) = NULL -- 'olo_dynamic_pricing', 'requires_location', 'pdf_menu'
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        DECLARE @PricesExtracted BIT = CASE WHEN @ItemsWithPrices > 0 THEN 1 ELSE 0 END;
        DECLARE @PriceStatus VARCHAR(20);
        DECLARE @EnrichmentNeeded BIT = 0;
        
        -- Determine price extraction status
        SET @PriceStatus = CASE
            WHEN @ItemsWithPrices >= @TotalItems * 0.8 THEN 'success'      -- 80%+ items have prices
            WHEN @ItemsWithPrices > 0 THEN 'partial'                       -- Some prices found
            WHEN @PriceUnavailableReason IS NOT NULL THEN 'unavailable'    -- Known reason for no prices
            WHEN @TotalItems > 0 THEN 'failed'                             -- Items found but no prices
            ELSE 'pending'
        END;
        
        -- Determine if enrichment should be attempted
        -- Mark for enrichment if: items exist, prices weren't found, and it's not a known unavailable case
        SET @EnrichmentNeeded = CASE
            WHEN @TotalItems > 0 AND @ItemsWithPrices = 0 
                 AND @PriceUnavailableReason IS NULL THEN 1
            WHEN @TotalItems > 0 AND @ItemsWithPrices < @TotalItems * 0.5 
                 AND @PriceUnavailableReason IS NULL THEN 1  -- Less than 50% have prices
            ELSE 0
        END;
        
        UPDATE restaurants
        SET prices_extracted = @PricesExtracted,
            items_with_prices = @ItemsWithPrices,
            price_extraction_status = @PriceStatus,
            price_source = @PriceSource,
            price_unavailable_reason = @PriceUnavailableReason,
            price_enrichment_needed = @EnrichmentNeeded,
            updated_at = GETDATE()
        WHERE restaurant_id = @RestaurantId;
        
        SELECT 
            @RestaurantId AS restaurant_id,
            @PricesExtracted AS prices_extracted,
            @ItemsWithPrices AS items_with_prices,
            @TotalItems AS total_items,
            @PriceStatus AS price_status,
            @EnrichmentNeeded AS enrichment_needed;
            
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO

-- Mark restaurant price enrichment attempt (called by helper thread)
IF OBJECT_ID('sp_MarkPriceEnrichmentAttempt') IS NOT NULL DROP PROCEDURE sp_MarkPriceEnrichmentAttempt;
GO

CREATE PROCEDURE sp_MarkPriceEnrichmentAttempt
    @RestaurantId VARCHAR(50),
    @Success BIT,
    @ItemsEnriched INT = 0,
    @Reason VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE restaurants
    SET price_enrichment_attempts = price_enrichment_attempts + 1,
        last_price_enrichment_attempt = GETDATE(),
        items_with_prices = items_with_prices + @ItemsEnriched,
        prices_extracted = CASE WHEN items_with_prices + @ItemsEnriched > 0 THEN 1 ELSE prices_extracted END,
        price_extraction_status = CASE 
            WHEN @Success = 1 AND items_with_prices + @ItemsEnriched > 0 THEN 'success'
            WHEN @Success = 0 AND @Reason IS NOT NULL THEN 'unavailable'
            ELSE price_extraction_status
        END,
        price_unavailable_reason = CASE WHEN @Success = 0 AND @Reason IS NOT NULL THEN @Reason ELSE price_unavailable_reason END,
        price_source = CASE WHEN @Success = 1 THEN 'enriched' ELSE price_source END,
        -- Stop trying after 3 attempts or if successful
        price_enrichment_needed = CASE 
            WHEN @Success = 1 THEN 0
            WHEN price_enrichment_attempts >= 3 THEN 0
            WHEN @Reason IS NOT NULL THEN 0  -- Known unavailable reason
            ELSE price_enrichment_needed 
        END,
        updated_at = GETDATE()
    WHERE restaurant_id = @RestaurantId;
    
    SELECT 
        restaurant_id,
        prices_extracted,
        items_with_prices,
        price_extraction_status,
        price_enrichment_needed,
        price_enrichment_attempts
    FROM restaurants
    WHERE restaurant_id = @RestaurantId;
END;
GO

-- Get next restaurant needing price enrichment (for helper thread)
IF OBJECT_ID('sp_GetNextPriceEnrichmentJob') IS NOT NULL DROP PROCEDURE sp_GetNextPriceEnrichmentJob;
GO

CREATE PROCEDURE sp_GetNextPriceEnrichmentJob
    @MaxAttempts INT = 3,
    @MinHoursSinceLastAttempt INT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT TOP 1
        r.restaurant_id,
        r.name,
        r.website,
        r.menu_url,
        r.price_enrichment_attempts,
        r.last_price_enrichment_attempt,
        r.total_items_extracted,
        r.items_with_prices,
        r.successful_discovery_method,
        r.api_endpoints_discovered
    FROM restaurants r
    WHERE r.price_enrichment_needed = 1
      AND r.price_enrichment_attempts < @MaxAttempts
      AND r.total_items_extracted > 0
      AND (r.last_price_enrichment_attempt IS NULL 
           OR r.last_price_enrichment_attempt < DATEADD(HOUR, -@MinHoursSinceLastAttempt, GETDATE()))
    ORDER BY 
        r.price_enrichment_attempts ASC,        -- Prioritize fewer attempts
        r.google_rating DESC NULLS LAST,        -- Higher rated restaurants first
        r.total_items_extracted DESC;           -- More items = more value
END;
GO

-- Get queue statistics
IF OBJECT_ID('spsc_GetQueueStats') IS NOT NULL DROP PROCEDURE spsc_GetQueueStats;
GO

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
    WHERE created_at >= DATEADD(DAY, -7, GETDATE());
    
    SELECT w.worker_id, w.worker_type, w.status, w.current_jobs, w.last_heartbeat,
           COUNT(j.job_id) as jobs_processed_today,
           AVG(CAST(j.actual_duration_seconds AS FLOAT)) as avg_processing_time
    FROM scraping_workers w
    LEFT JOIN universal_scraping_jobs j ON w.worker_id = j.worker_id AND j.completed_at >= CAST(GETDATE() AS DATE)
    GROUP BY w.worker_id, w.worker_type, w.status, w.current_jobs, w.last_heartbeat;
END;
GO

-- =============================================================================
-- SECTION 13: TEST PROCEDURES
-- =============================================================================

IF OBJECT_ID('sp_TestDatabase') IS NOT NULL DROP PROCEDURE sp_TestDatabase;
GO

CREATE PROCEDURE sp_TestDatabase
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        'Database Test Results' as test_name,
        (SELECT COUNT(*) FROM restaurants) as restaurants_count,
        (SELECT COUNT(*) FROM menu_categories) as categories_count,
        (SELECT COUNT(*) FROM menu_items) as menu_items_count,
        (SELECT COUNT(*) FROM system_config) as config_count,
        (SELECT COUNT(*) FROM chain_configs) as chain_configs_count,
        GETDATE() as test_timestamp;
        
    SELECT TOP 3 restaurant_id, name, phone, google_rating, scrape_status
    FROM restaurants ORDER BY created_at DESC;
END;
GO

-- =============================================================================
-- SETUP COMPLETE
-- =============================================================================

SELECT 
    'FoodFinder + CloudDestroyer Database Setup Complete!' as message,
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = 'FoodFinder') as total_tables,
    (SELECT COUNT(*) FROM sys.procedures WHERE type = 'P') as total_procedures,
    (SELECT COUNT(*) FROM sys.views) as total_views,
    GETDATE() as completed_at;
GO


