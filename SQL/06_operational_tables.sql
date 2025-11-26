-- FoodFinder Operational and System Tables
-- Job queues, configuration, and system management

USE FoodFinder;
GO

-- =============================================================================
-- OPERATIONAL DATA
-- =============================================================================

-- System configuration and feature flags
CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value NVARCHAR(MAX), -- JSON or plain text configuration value
    config_type VARCHAR(20) DEFAULT 'string' CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description NVARCHAR(MAX),
    is_public BIT DEFAULT 0, -- Can be exposed to frontend
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for system_config
CREATE INDEX idx_system_config_public ON system_config (is_public);
CREATE INDEX idx_system_config_type ON system_config (config_type);
GO

-- Create trigger for system_config updated_at
CREATE TRIGGER tr_system_config_updated_at
ON system_config
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE system_config 
    SET updated_at = GETDATE()
    FROM system_config s
    INNER JOIN inserted i ON s.config_key = i.config_key;
END;
GO

-- Scraping job queue and status tracking
CREATE TABLE scraping_jobs (
    job_id INT IDENTITY(1,1) PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL,
    
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'blocked', 'cancelled')),
    job_type VARCHAR(30) DEFAULT 'scrape_menu' CHECK (job_type IN ('scrape_menu', 'scrape_category', 'update_info', 'chain_sync', 'verify_blocked')),
    priority INT DEFAULT 5, -- 1-10, higher is more urgent
    
    -- Job execution details
    attempts INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_error_message NVARCHAR(MAX),
    error_code VARCHAR(50),
    
    -- Results tracking
    items_found INT DEFAULT 0,
    categories_found INT DEFAULT 0,
    processing_time_ms INT,
    
    -- Job scheduling
    scheduled_at DATETIME2 DEFAULT GETDATE(),
    started_at DATETIME2 NULL,
    completed_at DATETIME2 NULL,
    next_retry_at DATETIME2 NULL,
    
    -- Worker information
    worker_id VARCHAR(100), -- ID of the worker processing this job
    
    CONSTRAINT FK_scraping_jobs_restaurant 
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);
GO

-- Create indexes for scraping_jobs
CREATE INDEX idx_scraping_jobs_status_type ON scraping_jobs (status, job_type);
CREATE INDEX idx_scraping_jobs_priority ON scraping_jobs (priority DESC);
CREATE INDEX idx_scraping_jobs_scheduled ON scraping_jobs (scheduled_at);
CREATE INDEX idx_scraping_jobs_next_retry ON scraping_jobs (next_retry_at);
CREATE INDEX idx_scraping_jobs_worker ON scraping_jobs (worker_id);
GO

-- API rate limiting and usage tracking
CREATE TABLE api_usage (
    usage_id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- API details
    api_name VARCHAR(20) NOT NULL CHECK (api_name IN ('google_places', 'doordash', 'ubereats', 'yelp')),
    endpoint VARCHAR(200),
    
    -- Usage metrics
    requests_count INT DEFAULT 1,
    success_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    
    -- Rate limiting
    rate_limit_remaining INT,
    rate_limit_reset_at DATETIME2 NULL,
    
    -- Cost tracking (for paid APIs)
    estimated_cost DECIMAL(8,4) DEFAULT 0, -- Estimated cost in USD
    
    -- Time window
    hour_bucket DATETIME2 NOT NULL, -- Rounded to hour for aggregation
    
    created_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes and constraints for api_usage
CREATE UNIQUE INDEX idx_api_usage_unique ON api_usage (api_name, endpoint, hour_bucket);
CREATE INDEX idx_api_usage_api_hour ON api_usage (api_name, hour_bucket);
CREATE INDEX idx_api_usage_rate_limit ON api_usage (rate_limit_reset_at);
GO

-- System health monitoring
CREATE TABLE health_checks (
    check_id INT IDENTITY(1,1) PRIMARY KEY,
    
    service_name VARCHAR(100) NOT NULL, -- Database, Redis, Scraper, etc.
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
    
    -- Health metrics
    response_time_ms INT,
    error_message NVARCHAR(MAX),
    details NVARCHAR(MAX) CHECK (details IS NULL OR ISJSON(details) = 1), -- Additional health check details
    
    -- Alerting
    alert_sent BIT DEFAULT 0,
    resolved_at DATETIME2 NULL,
    
    checked_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Create indexes for health_checks
CREATE INDEX idx_health_checks_service_status ON health_checks (service_name, status);
CREATE INDEX idx_health_checks_checked ON health_checks (checked_at DESC);
CREATE INDEX idx_health_checks_unresolved ON health_checks (resolved_at, alert_sent);
GO