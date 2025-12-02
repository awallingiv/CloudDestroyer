-- =============================================================================
-- CloudDestroyer Database Schema
-- Standalone scraping service database for job management and extraction
-- =============================================================================

-- Create database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'CloudDestroyer')
BEGIN
    CREATE DATABASE CloudDestroyer
    COLLATE SQL_Latin1_General_CP1_CI_AS;
END
GO

USE CloudDestroyer;
GO

SELECT 
    'CloudDestroyer database created successfully' as status,
    DB_NAME() as current_database,
    DATABASEPROPERTYEX(DB_NAME(), 'Collation') as collation;
GO

-- =============================================================================
-- SECTION 1: CORE SCRAPING TABLES
-- =============================================================================

-- Target sites configuration (site-specific settings)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'target_sites')
CREATE TABLE target_sites (
    site_id INT IDENTITY(1,1) PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE,
    site_name VARCHAR(255),
    
    -- Site characteristics
    cloudflare_protected BIT DEFAULT 0,
    requires_selenium BIT DEFAULT 0,
    requires_javascript BIT DEFAULT 0,
    site_type VARCHAR(50) NULL,                    -- 'static', 'react_spa', 'angular_spa', 'api_driven'
    
    -- API discovery
    api_endpoints_discovered NVARCHAR(MAX) CHECK (api_endpoints_discovered IS NULL OR ISJSON(api_endpoints_discovered) = 1),
    api_base_url VARCHAR(500) NULL,

    -- Direct API endpoint tracking (for OLO and similar systems)
    api_menu_endpoint VARCHAR(1000) NULL,              -- Direct menu API URL
    api_endpoint_type VARCHAR(50) NULL,                -- 'olo', 'custom', 'graphql', 'rest'
    api_requires_location BIT DEFAULT 0,               -- Whether API needs location/restaurant ID
    api_authentication_method VARCHAR(100) NULL,       -- 'none', 'session', 'api_key', 'oauth'
    api_endpoint_working BIT DEFAULT NULL,             -- NULL = unknown, 1 = working, 0 = broken
    api_last_verified DATETIME2 NULL,                  -- When endpoint was last successfully used
    api_last_failed DATETIME2 NULL,                    -- When endpoint last failed
    api_failure_reason VARCHAR(255) NULL,              -- Why endpoint failed
    api_verified_count INT DEFAULT 0,                  -- Number of successful verifications
    api_failure_count INT DEFAULT 0,                   -- Number of failures
    
    -- Scraping configuration
    rate_limit_ms INT DEFAULT 2000,                -- Delay between requests
    max_concurrent_requests INT DEFAULT 1,
    custom_headers NVARCHAR(MAX) CHECK (custom_headers IS NULL OR ISJSON(custom_headers) = 1),
    custom_selectors NVARCHAR(MAX) CHECK (custom_selectors IS NULL OR ISJSON(custom_selectors) = 1),
    
    -- Success tracking
    total_scrapes INT DEFAULT 0,
    successful_scrapes INT DEFAULT 0,
    last_successful_scrape DATETIME2 NULL,
    best_extraction_method VARCHAR(100) NULL,
    average_extraction_time_seconds DECIMAL(8,2) DEFAULT 0,
    
    -- Status
    is_active BIT DEFAULT 1,
    blocked_until DATETIME2 NULL,
    block_reason VARCHAR(255) NULL,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Scraping job queue
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_jobs')
CREATE TABLE scraping_jobs (
    job_id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Job identification
    job_type VARCHAR(50) NOT NULL,                 -- 'menu_extraction', 'price_enrichment', 'content_monitor', etc.
    job_name VARCHAR(255),
    
    -- Target
    target_url VARCHAR(1000) NOT NULL,
    target_domain VARCHAR(255),
    site_id INT NULL,                              -- Reference to target_sites
    
    -- Entity reference (what this job is for)
    entity_type VARCHAR(50) NULL,                  -- 'restaurant', 'product', 'page', etc.
    entity_id VARCHAR(100) NULL,                   -- External ID from consuming app
    
    -- Configuration
    scraping_config NVARCHAR(MAX) CHECK (scraping_config IS NULL OR ISJSON(scraping_config) = 1),
    extraction_rules NVARCHAR(MAX) CHECK (extraction_rules IS NULL OR ISJSON(extraction_rules) = 1),
    
    -- Priority and scheduling
    priority INT DEFAULT 50,                       -- Higher = processed sooner
    scheduled_at DATETIME2 DEFAULT GETDATE(),
    earliest_start_at DATETIME2 DEFAULT GETDATE(),
    expires_at DATETIME2 NULL,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'blocked', 'cancelled', 'retry', 'paused')),
    started_at DATETIME2 NULL,
    completed_at DATETIME2 NULL,
    
    -- Retry logic
    attempts INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_delay_minutes INT DEFAULT 5,
    next_retry_at DATETIME2 NULL,
    
    -- Error tracking
    last_error_message NVARCHAR(MAX),
    error_code VARCHAR(100),
    error_category VARCHAR(50),                    -- 'cloudflare', 'timeout', 'parse_error', 'network', etc.
    
    -- Worker assignment
    worker_id VARCHAR(100),
    worker_type VARCHAR(50),
    processing_node VARCHAR(100),
    
    -- Results summary
    items_extracted INT DEFAULT 0,
    data_quality_score INT DEFAULT 0,
    actual_duration_seconds DECIMAL(8,2),
    
    -- Price extraction tracking
    prices_extracted BIT DEFAULT 0,
    items_with_prices INT DEFAULT 0,
    price_extraction_status VARCHAR(20) DEFAULT 'pending'
        CHECK (price_extraction_status IN ('pending', 'success', 'unavailable', 'failed', 'partial')),
    price_unavailable_reason VARCHAR(100) NULL,
    price_source VARCHAR(50) NULL,
    
    -- Enrichment tracking
    price_enrichment_needed BIT DEFAULT 0,
    price_enrichment_attempts INT DEFAULT 0,
    last_price_enrichment_attempt DATETIME2 NULL,
    
    -- Batch tracking
    batch_id VARCHAR(100),
    session_id VARCHAR(100),
    depends_on_job_id INT NULL,
    
    -- Callback configuration
    callback_url VARCHAR(500) NULL,                -- URL to call when job completes
    callback_method VARCHAR(10) DEFAULT 'POST',
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_scraping_jobs_site FOREIGN KEY (site_id) REFERENCES target_sites(site_id),
    CONSTRAINT FK_scraping_jobs_depends FOREIGN KEY (depends_on_job_id) REFERENCES scraping_jobs(job_id)
);
GO

-- Scraping results storage
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_results')
CREATE TABLE scraping_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    job_id INT NOT NULL,
    
    -- Result classification
    result_type VARCHAR(50) NOT NULL,              -- 'menu_data', 'price_data', 'raw_html', 'api_response'
    data_schema VARCHAR(100),                      -- Schema version for structured data
    
    -- Quality metrics
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    completeness_score DECIMAL(3,2) DEFAULT 1.0,
    accuracy_indicators NVARCHAR(MAX) CHECK (accuracy_indicators IS NULL OR ISJSON(accuracy_indicators) = 1),
    
    -- Data storage
    raw_data NVARCHAR(MAX),                        -- Raw extracted content
    structured_data NVARCHAR(MAX) CHECK (structured_data IS NULL OR ISJSON(structured_data) = 1),
    summary_data NVARCHAR(MAX) CHECK (summary_data IS NULL OR ISJSON(summary_data) = 1),
    
    -- Extraction metadata
    extraction_method VARCHAR(100),                -- 'api', 'dom_scrape', 'selenium', etc.
    extraction_url VARCHAR(1000),
    response_status_code INT,
    
    -- Size metrics
    data_size_bytes INT DEFAULT 0,
    record_count INT DEFAULT 0,
    unique_fields_found INT DEFAULT 0,
    
    -- Performance
    processing_time_seconds DECIMAL(8,2) DEFAULT 0,
    memory_usage_mb INT DEFAULT 0,
    
    -- Validation
    validation_status VARCHAR(20) DEFAULT 'pending' 
        CHECK (validation_status IN ('pending', 'valid', 'invalid', 'partial', 'unknown')),
    validation_errors NVARCHAR(MAX),
    verified_at DATETIME2 NULL,
    verified_by VARCHAR(100),
    
    -- Sync tracking (for pushing to consumer apps)
    sync_status VARCHAR(20) DEFAULT 'pending'
        CHECK (sync_status IN ('pending', 'synced', 'failed', 'skipped')),
    synced_at DATETIME2 NULL,
    sync_target VARCHAR(100),                      -- 'foodfinder', 'other_app', etc.
    sync_error NVARCHAR(MAX),
    
    extracted_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_scraping_results_job FOREIGN KEY (job_id) REFERENCES scraping_jobs(job_id) ON DELETE CASCADE
);
GO

-- Scraping workers registry
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_workers')
CREATE TABLE scraping_workers (
    worker_id VARCHAR(100) PRIMARY KEY,
    worker_name VARCHAR(255) NOT NULL,
    worker_type VARCHAR(50) NOT NULL,              -- 'clouddestroyer', 'api_client', 'browser'
    
    -- Capabilities
    supported_job_types NVARCHAR(MAX) CHECK (supported_job_types IS NULL OR ISJSON(supported_job_types) = 1),
    max_concurrent_jobs INT DEFAULT 1,
    specialization VARCHAR(100),                   -- 'cloudflare_bypass', 'spa_rendering', etc.
    
    -- Requirements
    memory_requirement_mb INT DEFAULT 512,
    requires_browser BIT DEFAULT 0,
    requires_proxy BIT DEFAULT 0,
    
    -- Performance metrics
    average_job_duration_seconds INT DEFAULT 60,
    success_rate DECIMAL(3,2) DEFAULT 1.0,
    reliability_score INT DEFAULT 100,
    total_jobs_completed INT DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' 
        CHECK (status IN ('active', 'inactive', 'maintenance', 'error')),
    last_heartbeat DATETIME2 NULL,
    current_jobs INT DEFAULT 0,
    last_error NVARCHAR(MAX),
    
    -- Configuration
    config_json NVARCHAR(MAX) CHECK (config_json IS NULL OR ISJSON(config_json) = 1),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Job execution history
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_job_history')
CREATE TABLE scraping_job_history (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    job_id INT NOT NULL,
    execution_attempt INT NOT NULL,
    worker_id VARCHAR(100),
    
    -- Timing
    started_at DATETIME2 NOT NULL,
    completed_at DATETIME2 NULL,
    duration_seconds DECIMAL(8,2),
    
    -- Outcome
    status VARCHAR(20) NOT NULL,
    items_found INT DEFAULT 0,
    error_message NVARCHAR(MAX),
    
    -- Resource usage
    cpu_usage_percent DECIMAL(5,2),
    memory_usage_mb INT,
    network_requests INT DEFAULT 0,
    bytes_downloaded INT DEFAULT 0,
    
    -- Method used
    extraction_method VARCHAR(100),
    bypass_strategy VARCHAR(100),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_scraping_history_job FOREIGN KEY (job_id) REFERENCES scraping_jobs(job_id) ON DELETE CASCADE
);
GO

-- Job templates for reusable configurations
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'scraping_templates')
CREATE TABLE scraping_templates (
    template_id INT IDENTITY(1,1) PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL UNIQUE,
    job_type VARCHAR(50) NOT NULL,
    
    -- Default configuration
    default_config NVARCHAR(MAX) CHECK (default_config IS NULL OR ISJSON(default_config) = 1),
    extraction_rules NVARCHAR(MAX) CHECK (extraction_rules IS NULL OR ISJSON(extraction_rules) = 1),
    
    -- Defaults
    default_priority INT DEFAULT 50,
    default_max_retries INT DEFAULT 3,
    estimated_duration_seconds INT DEFAULT 60,
    
    -- Metadata
    description NVARCHAR(MAX),
    created_by VARCHAR(100),
    version VARCHAR(20) DEFAULT '1.0',
    is_active BIT DEFAULT 1,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================================================
-- SECTION 2: SYSTEM TABLES
-- =============================================================================

-- System configuration
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'system_config')
CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value NVARCHAR(MAX),
    config_type VARCHAR(20) DEFAULT 'string' 
        CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description NVARCHAR(MAX),
    is_sensitive BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Health checks
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'health_checks')
CREATE TABLE health_checks (
    check_id INT IDENTITY(1,1) PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL 
        CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
    response_time_ms INT,
    error_message NVARCHAR(MAX),
    details NVARCHAR(MAX) CHECK (details IS NULL OR ISJSON(details) = 1),
    alert_sent BIT DEFAULT 0,
    resolved_at DATETIME2 NULL,
    checked_at DATETIME2 DEFAULT GETDATE()
);
GO

-- =============================================================================
-- SECTION 3: INDEXES
-- =============================================================================

-- Target sites indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_target_sites_domain')
    CREATE INDEX idx_target_sites_domain ON target_sites (domain);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_target_sites_active')
    CREATE INDEX idx_target_sites_active ON target_sites (is_active) WHERE is_active = 1;
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_target_sites_api_endpoint')
    CREATE INDEX idx_target_sites_api_endpoint ON target_sites (api_endpoint_working, api_last_verified)
    WHERE api_menu_endpoint IS NOT NULL;
GO

-- Scraping jobs indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_status_priority')
    CREATE INDEX idx_scraping_jobs_status_priority ON scraping_jobs (status, priority DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_type')
    CREATE INDEX idx_scraping_jobs_type ON scraping_jobs (job_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_entity')
    CREATE INDEX idx_scraping_jobs_entity ON scraping_jobs (entity_type, entity_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_domain')
    CREATE INDEX idx_scraping_jobs_domain ON scraping_jobs (target_domain);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_scheduled')
    CREATE INDEX idx_scraping_jobs_scheduled ON scraping_jobs (scheduled_at, earliest_start_at);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_batch')
    CREATE INDEX idx_scraping_jobs_batch ON scraping_jobs (batch_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_worker')
    CREATE INDEX idx_scraping_jobs_worker ON scraping_jobs (worker_id, status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_jobs_price_enrichment')
    CREATE INDEX idx_scraping_jobs_price_enrichment ON scraping_jobs (price_enrichment_needed, price_enrichment_attempts)
    WHERE price_enrichment_needed = 1;
GO

-- Scraping results indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_results_job')
    CREATE INDEX idx_scraping_results_job ON scraping_results (job_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_results_type')
    CREATE INDEX idx_scraping_results_type ON scraping_results (result_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_results_sync')
    CREATE INDEX idx_scraping_results_sync ON scraping_results (sync_status) WHERE sync_status = 'pending';
GO

-- Worker indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_workers_type')
    CREATE INDEX idx_scraping_workers_type ON scraping_workers (worker_type);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_workers_status')
    CREATE INDEX idx_scraping_workers_status ON scraping_workers (status);
GO

-- History indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_scraping_history_job')
    CREATE INDEX idx_scraping_history_job ON scraping_job_history (job_id, execution_attempt);
GO

-- Health check indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_health_checks_service')
    CREATE INDEX idx_health_checks_service ON health_checks (service_name, status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_health_checks_checked')
    CREATE INDEX idx_health_checks_checked ON health_checks (checked_at DESC);
GO

-- =============================================================================
-- SECTION 4: TRIGGERS
-- =============================================================================

-- Update trigger for scraping_jobs
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_scraping_jobs_updated')
BEGIN
    EXEC('
    CREATE TRIGGER tr_scraping_jobs_updated
    ON scraping_jobs
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE scraping_jobs 
        SET updated_at = GETDATE()
        FROM scraping_jobs j
        INNER JOIN inserted i ON j.job_id = i.job_id;
    END');
END
GO

-- Update trigger for target_sites
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_target_sites_updated')
BEGIN
    EXEC('
    CREATE TRIGGER tr_target_sites_updated
    ON target_sites
    AFTER UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;
        UPDATE target_sites 
        SET updated_at = GETDATE()
        FROM target_sites t
        INNER JOIN inserted i ON t.site_id = i.site_id;
    END');
END
GO

-- =============================================================================
-- SECTION 5: VIEWS
-- =============================================================================

-- Job queue view with effective priority
IF OBJECT_ID('v_job_queue') IS NOT NULL DROP VIEW v_job_queue;
GO

CREATE VIEW v_job_queue AS
SELECT 
    j.job_id,
    j.job_type,
    j.job_name,
    j.target_url,
    j.target_domain,
    j.entity_type,
    j.entity_id,
    j.status,
    j.priority,
    j.attempts,
    j.max_retries,
    j.created_at,
    j.scheduled_at,
    j.next_retry_at,
    j.worker_id,
    ts.cloudflare_protected,
    ts.site_type,
    -- Calculate effective priority
    j.priority + 
    CASE WHEN j.attempts = 0 THEN 20 WHEN j.attempts = 1 THEN 10 ELSE 0 END +
    CASE WHEN ts.cloudflare_protected = 1 THEN -10 ELSE 0 END +
    CASE WHEN ts.site_type = 'api_driven' THEN 15 ELSE 0 END
    AS effective_priority
FROM scraping_jobs j
LEFT JOIN target_sites ts ON j.site_id = ts.site_id
WHERE j.status IN ('pending', 'retry');
GO

-- Price enrichment queue view
IF OBJECT_ID('v_price_enrichment_queue') IS NOT NULL DROP VIEW v_price_enrichment_queue;
GO

CREATE VIEW v_price_enrichment_queue AS
SELECT 
    j.job_id,
    j.job_name,
    j.target_url,
    j.target_domain,
    j.entity_type,
    j.entity_id,
    j.items_extracted,
    j.items_with_prices,
    j.price_extraction_status,
    j.price_unavailable_reason,
    j.price_enrichment_attempts,
    j.last_price_enrichment_attempt,
    -- Priority calculation
    CASE 
        WHEN j.items_extracted >= 50 THEN 25
        WHEN j.items_extracted >= 20 THEN 15
        WHEN j.items_extracted >= 10 THEN 10
        ELSE 5
    END +
    CASE 
        WHEN j.price_enrichment_attempts = 0 THEN 20
        WHEN j.price_enrichment_attempts = 1 THEN 10
        ELSE 0
    END AS enrichment_priority,
    DATEDIFF(HOUR, j.last_price_enrichment_attempt, GETDATE()) AS hours_since_last_attempt
FROM scraping_jobs j
WHERE j.price_enrichment_needed = 1
  AND j.items_extracted > 0
  AND j.price_enrichment_attempts < 3
  AND j.status = 'completed'
  AND (j.last_price_enrichment_attempt IS NULL 
       OR j.last_price_enrichment_attempt < DATEADD(HOUR, -1, GETDATE()));
GO

-- Results pending sync view
IF OBJECT_ID('v_results_pending_sync') IS NOT NULL DROP VIEW v_results_pending_sync;
GO

CREATE VIEW v_results_pending_sync AS
SELECT 
    r.result_id,
    r.job_id,
    j.entity_type,
    j.entity_id,
    r.result_type,
    r.record_count,
    r.confidence_score,
    r.validation_status,
    r.sync_status,
    r.extracted_at,
    j.target_domain
FROM scraping_results r
INNER JOIN scraping_jobs j ON r.job_id = j.job_id
WHERE r.sync_status = 'pending'
  AND r.validation_status IN ('valid', 'partial')
  AND j.status = 'completed';
GO

-- System statistics view
IF OBJECT_ID('v_system_stats') IS NOT NULL DROP VIEW v_system_stats;
GO

CREATE VIEW v_system_stats AS
SELECT 
    'Scraping Overview' AS metric_category,
    (SELECT COUNT(*) FROM scraping_jobs WHERE status = 'pending') AS pending_jobs,
    (SELECT COUNT(*) FROM scraping_jobs WHERE status = 'running') AS running_jobs,
    (SELECT COUNT(*) FROM scraping_jobs WHERE status = 'completed' AND completed_at >= CAST(GETDATE() AS DATE)) AS completed_today,
    (SELECT COUNT(*) FROM scraping_jobs WHERE status = 'failed' AND completed_at >= CAST(GETDATE() AS DATE)) AS failed_today,
    (SELECT COUNT(*) FROM scraping_jobs WHERE price_enrichment_needed = 1) AS pending_enrichment,
    (SELECT COUNT(*) FROM scraping_results WHERE sync_status = 'pending') AS pending_sync,
    (SELECT COUNT(*) FROM scraping_workers WHERE status = 'active') AS active_workers,
    (SELECT AVG(CAST(actual_duration_seconds AS FLOAT)) FROM scraping_jobs WHERE completed_at >= DATEADD(DAY, -1, GETDATE())) AS avg_duration_24h;
GO

-- =============================================================================
-- SECTION 6: STORED PROCEDURES
-- =============================================================================

-- Create a new scraping job
IF OBJECT_ID('sp_CreateJob') IS NOT NULL DROP PROCEDURE sp_CreateJob;
GO

CREATE PROCEDURE sp_CreateJob
    @JobType VARCHAR(50),
    @TargetUrl VARCHAR(1000),
    @JobName VARCHAR(255) = NULL,
    @EntityType VARCHAR(50) = NULL,
    @EntityId VARCHAR(100) = NULL,
    @Priority INT = 50,
    @ScrapingConfig NVARCHAR(MAX) = NULL,
    @BatchId VARCHAR(100) = NULL,
    @SessionId VARCHAR(100) = NULL,
    @CallbackUrl VARCHAR(500) = NULL,
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
        
        -- Extract domain from URL
        DECLARE @Domain VARCHAR(255);
        SET @Domain = CASE 
            WHEN CHARINDEX('://', @TargetUrl) > 0 THEN
                SUBSTRING(@TargetUrl, CHARINDEX('://', @TargetUrl) + 3, 
                         CHARINDEX('/', @TargetUrl + '/', CHARINDEX('://', @TargetUrl) + 3) - CHARINDEX('://', @TargetUrl) - 3)
            ELSE @TargetUrl
        END;
        
        -- Get or create site record
        DECLARE @SiteId INT;
        SELECT @SiteId = site_id FROM target_sites WHERE domain = @Domain;
        
        IF @SiteId IS NULL
        BEGIN
            INSERT INTO target_sites (domain, site_name) VALUES (@Domain, @Domain);
            SET @SiteId = SCOPE_IDENTITY();
        END
        
        IF @JobName IS NULL
            SET @JobName = @JobType + ' - ' + @Domain;
        
        -- Check for duplicate pending job
        IF EXISTS (SELECT 1 FROM scraping_jobs 
                   WHERE job_type = @JobType AND target_url = @TargetUrl 
                   AND status IN ('pending', 'running'))
        BEGIN
            SELECT @JobId = job_id FROM scraping_jobs 
            WHERE job_type = @JobType AND target_url = @TargetUrl 
            AND status IN ('pending', 'running');
            RETURN;
        END
        
        INSERT INTO scraping_jobs (
            job_type, job_name, target_url, target_domain, site_id,
            entity_type, entity_id, priority, scraping_config,
            batch_id, session_id, callback_url
        )
        VALUES (
            @JobType, @JobName, @TargetUrl, @Domain, @SiteId,
            @EntityType, @EntityId, @Priority, @ScrapingConfig,
            @BatchId, @SessionId, @CallbackUrl
        );
        
        SET @JobId = SCOPE_IDENTITY();
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- Get next job from queue
IF OBJECT_ID('sp_GetNextJob') IS NOT NULL DROP PROCEDURE sp_GetNextJob;
GO

CREATE PROCEDURE sp_GetNextJob
    @WorkerId VARCHAR(100),
    @WorkerType VARCHAR(50),
    @SupportedJobTypes VARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @JobId INT = NULL;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Update worker heartbeat
        UPDATE scraping_workers 
        SET last_heartbeat = GETDATE(), current_jobs = current_jobs + 1 
        WHERE worker_id = @WorkerId;
        
        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO scraping_workers (worker_id, worker_name, worker_type, supported_job_types, last_heartbeat, current_jobs)
            VALUES (@WorkerId, @WorkerId, @WorkerType,
                CASE WHEN @SupportedJobTypes IS NOT NULL 
                     THEN '["' + REPLACE(@SupportedJobTypes, ',', '","') + '"]' 
                     ELSE NULL END,
                GETDATE(), 1);
        END
        
        -- Get next job
        SELECT TOP 1 @JobId = job_id 
        FROM scraping_jobs
        WHERE status = 'pending'
          AND (earliest_start_at IS NULL OR earliest_start_at <= GETDATE())
          AND (next_retry_at IS NULL OR next_retry_at <= GETDATE())
          AND (expires_at IS NULL OR expires_at > GETDATE())
          AND (@SupportedJobTypes IS NULL OR job_type IN (SELECT TRIM(value) FROM STRING_SPLIT(@SupportedJobTypes, ',')))
        ORDER BY priority DESC, created_at ASC;
        
        IF @JobId IS NOT NULL
        BEGIN
            UPDATE scraping_jobs 
            SET status = 'running', 
                worker_id = @WorkerId, 
                worker_type = @WorkerType, 
                started_at = GETDATE(), 
                attempts = attempts + 1 
            WHERE job_id = @JobId;
            
            INSERT INTO scraping_job_history (job_id, execution_attempt, worker_id, started_at, status)
            VALUES (@JobId, (SELECT attempts FROM scraping_jobs WHERE job_id = @JobId), @WorkerId, GETDATE(), 'running');
            
            -- Return job details
            SELECT 
                j.job_id, j.job_type, j.job_name, j.target_url, j.target_domain,
                j.entity_type, j.entity_id, j.scraping_config, j.extraction_rules,
                j.priority, j.attempts, j.max_retries, j.batch_id, j.session_id,
                j.callback_url,
                ts.cloudflare_protected, ts.requires_selenium, ts.site_type,
                ts.api_endpoints_discovered, ts.custom_headers, ts.custom_selectors,
                t.default_config AS template_config, t.extraction_rules AS template_rules
            FROM scraping_jobs j
            LEFT JOIN target_sites ts ON j.site_id = ts.site_id
            LEFT JOIN scraping_templates t ON j.job_type = t.job_type AND t.is_active = 1
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

-- Complete a job
IF OBJECT_ID('sp_CompleteJob') IS NOT NULL DROP PROCEDURE sp_CompleteJob;
GO

CREATE PROCEDURE sp_CompleteJob
    @JobId INT,
    @Status VARCHAR(20),
    @ItemsExtracted INT = 0,
    @ProcessingTimeSeconds DECIMAL(8,2) = 0,
    @ErrorMessage NVARCHAR(MAX) = NULL,
    @ErrorCode VARCHAR(100) = NULL,
    @RawData NVARCHAR(MAX) = NULL,
    @StructuredData NVARCHAR(MAX) = NULL,
    @ConfidenceScore DECIMAL(3,2) = 1.0,
    @ExtractionMethod VARCHAR(100) = NULL,
    @ItemsWithPrices INT = 0,
    @PriceSource VARCHAR(50) = NULL,
    @PriceUnavailableReason VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        DECLARE @WorkerId VARCHAR(100);
        DECLARE @ShouldRetry BIT = 0;
        DECLARE @NextRetryAt DATETIME2 = NULL;
        DECLARE @SiteId INT;
        
        SELECT @WorkerId = worker_id, @SiteId = site_id 
        FROM scraping_jobs WHERE job_id = @JobId;
        
        -- Determine retry logic
        IF @Status IN ('failed', 'blocked')
        BEGIN
            DECLARE @Attempts INT, @MaxRetries INT, @RetryDelayMinutes INT;
            SELECT @Attempts = attempts, @MaxRetries = max_retries, @RetryDelayMinutes = retry_delay_minutes 
            FROM scraping_jobs WHERE job_id = @JobId;
            
            IF @Attempts < @MaxRetries
            BEGIN
                SET @ShouldRetry = 1;
                SET @Status = 'retry';
                SET @NextRetryAt = DATEADD(MINUTE, @RetryDelayMinutes * POWER(2, @Attempts - 1), GETDATE());
            END
        END
        
        -- Determine price status
        DECLARE @PriceStatus VARCHAR(20) = 'pending';
        DECLARE @PricesExtracted BIT = CASE WHEN @ItemsWithPrices > 0 THEN 1 ELSE 0 END;
        DECLARE @EnrichmentNeeded BIT = 0;
        
        IF @ItemsExtracted > 0
        BEGIN
            SET @PriceStatus = CASE
                WHEN @ItemsWithPrices >= @ItemsExtracted * 0.8 THEN 'success'
                WHEN @ItemsWithPrices > 0 THEN 'partial'
                WHEN @PriceUnavailableReason IS NOT NULL THEN 'unavailable'
                ELSE 'failed'
            END;
            
            SET @EnrichmentNeeded = CASE
                WHEN @ItemsWithPrices = 0 AND @PriceUnavailableReason IS NULL THEN 1
                WHEN @ItemsWithPrices < @ItemsExtracted * 0.5 AND @PriceUnavailableReason IS NULL THEN 1
                ELSE 0
            END;
        END
        
        -- Update job
        UPDATE scraping_jobs
        SET status = @Status,
            items_extracted = @ItemsExtracted,
            actual_duration_seconds = @ProcessingTimeSeconds,
            last_error_message = @ErrorMessage,
            error_code = @ErrorCode,
            completed_at = CASE WHEN @Status IN ('completed', 'failed', 'cancelled') THEN GETDATE() ELSE NULL END,
            next_retry_at = @NextRetryAt,
            data_quality_score = CAST(@ConfidenceScore * 100 AS INT),
            prices_extracted = @PricesExtracted,
            items_with_prices = @ItemsWithPrices,
            price_extraction_status = @PriceStatus,
            price_source = @PriceSource,
            price_unavailable_reason = @PriceUnavailableReason,
            price_enrichment_needed = @EnrichmentNeeded
        WHERE job_id = @JobId;
        
        -- Store results if provided
        IF (@RawData IS NOT NULL OR @StructuredData IS NOT NULL) AND @Status = 'completed'
        BEGIN
            INSERT INTO scraping_results (
                job_id, result_type, confidence_score, raw_data, structured_data,
                data_size_bytes, record_count, processing_time_seconds, extraction_method
            )
            VALUES (
                @JobId, 
                CASE WHEN @StructuredData IS NOT NULL THEN 'structured_data' ELSE 'raw_data' END,
                @ConfidenceScore, @RawData, @StructuredData,
                LEN(ISNULL(@RawData, '') + ISNULL(@StructuredData, '')),
                @ItemsExtracted, @ProcessingTimeSeconds, @ExtractionMethod
            );
        END
        
        -- Update job history
        UPDATE scraping_job_history 
        SET completed_at = GETDATE(), 
            duration_seconds = @ProcessingTimeSeconds, 
            status = @Status, 
            items_found = @ItemsExtracted, 
            error_message = @ErrorMessage,
            extraction_method = @ExtractionMethod
        WHERE job_id = @JobId AND completed_at IS NULL AND worker_id = @WorkerId;
        
        -- Update site statistics
        IF @SiteId IS NOT NULL
        BEGIN
            UPDATE target_sites
            SET total_scrapes = total_scrapes + 1,
                successful_scrapes = successful_scrapes + CASE WHEN @Status = 'completed' THEN 1 ELSE 0 END,
                last_successful_scrape = CASE WHEN @Status = 'completed' THEN GETDATE() ELSE last_successful_scrape END,
                best_extraction_method = CASE WHEN @Status = 'completed' THEN @ExtractionMethod ELSE best_extraction_method END
            WHERE site_id = @SiteId;
        END
        
        -- Update worker
        UPDATE scraping_workers 
        SET current_jobs = current_jobs - 1, 
            last_heartbeat = GETDATE(),
            total_jobs_completed = total_jobs_completed + 1
        WHERE worker_id = @WorkerId;
        
        SELECT @JobId AS job_id, @Status AS final_status, @ItemsExtracted AS items_extracted,
               @ShouldRetry AS will_retry, @NextRetryAt AS next_retry_at,
               @PriceStatus AS price_status, @EnrichmentNeeded AS enrichment_needed;
        
    END TRY
    BEGIN CATCH
        UPDATE scraping_workers SET current_jobs = current_jobs - 1 WHERE worker_id = @WorkerId;
        THROW;
    END CATCH
END;
GO

-- Get next price enrichment job
IF OBJECT_ID('sp_GetNextPriceEnrichmentJob') IS NOT NULL DROP PROCEDURE sp_GetNextPriceEnrichmentJob;
GO

CREATE PROCEDURE sp_GetNextPriceEnrichmentJob
    @MaxAttempts INT = 3,
    @MinHoursSinceLastAttempt INT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT TOP 1
        j.job_id,
        j.job_name,
        j.target_url,
        j.target_domain,
        j.entity_type,
        j.entity_id,
        j.items_extracted,
        j.items_with_prices,
        j.price_enrichment_attempts,
        j.last_price_enrichment_attempt,
        ts.api_endpoints_discovered,
        ts.site_type,
        r.structured_data AS last_extraction_data
    FROM scraping_jobs j
    LEFT JOIN target_sites ts ON j.site_id = ts.site_id
    LEFT JOIN scraping_results r ON j.job_id = r.job_id AND r.result_type = 'structured_data'
    WHERE j.price_enrichment_needed = 1
      AND j.price_enrichment_attempts < @MaxAttempts
      AND j.items_extracted > 0
      AND j.status = 'completed'
      AND (j.last_price_enrichment_attempt IS NULL 
           OR j.last_price_enrichment_attempt < DATEADD(HOUR, -@MinHoursSinceLastAttempt, GETDATE()))
    ORDER BY 
        j.price_enrichment_attempts ASC,
        j.items_extracted DESC;
END;
GO

-- Mark price enrichment attempt
IF OBJECT_ID('sp_MarkPriceEnrichmentAttempt') IS NOT NULL DROP PROCEDURE sp_MarkPriceEnrichmentAttempt;
GO

CREATE PROCEDURE sp_MarkPriceEnrichmentAttempt
    @JobId INT,
    @Success BIT,
    @ItemsEnriched INT = 0,
    @Reason VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE scraping_jobs
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
        price_enrichment_needed = CASE 
            WHEN @Success = 1 THEN 0
            WHEN price_enrichment_attempts >= 3 THEN 0
            WHEN @Reason IS NOT NULL THEN 0
            ELSE price_enrichment_needed 
        END
    WHERE job_id = @JobId;
    
    SELECT job_id, prices_extracted, items_with_prices, price_extraction_status, price_enrichment_needed
    FROM scraping_jobs WHERE job_id = @JobId;
END;
GO

-- Get queue statistics
IF OBJECT_ID('sp_GetQueueStats') IS NOT NULL DROP PROCEDURE sp_GetQueueStats;
GO

CREATE PROCEDURE sp_GetQueueStats
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Overall queue stats
    SELECT 
        'Queue Overview' AS metric_category,
        COUNT(*) AS total_jobs,
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_jobs,
        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_jobs,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_jobs,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_jobs,
        SUM(CASE WHEN price_enrichment_needed = 1 THEN 1 ELSE 0 END) AS pending_enrichment,
        AVG(CAST(actual_duration_seconds AS FLOAT)) AS avg_duration_seconds
    FROM scraping_jobs
    WHERE created_at >= DATEADD(DAY, -7, GETDATE());
    
    -- Worker stats
    SELECT 
        worker_id, worker_type, status, current_jobs, 
        last_heartbeat, total_jobs_completed, success_rate
    FROM scraping_workers
    ORDER BY status, worker_id;
    
    -- Job type breakdown
    SELECT 
        job_type,
        COUNT(*) AS total,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
        AVG(CAST(actual_duration_seconds AS FLOAT)) AS avg_duration
    FROM scraping_jobs
    WHERE created_at >= DATEADD(DAY, -7, GETDATE())
    GROUP BY job_type;
END;
GO

-- Save discovered API endpoint
IF OBJECT_ID('sp_SaveApiEndpoint') IS NOT NULL DROP PROCEDURE sp_SaveApiEndpoint;
GO

CREATE PROCEDURE sp_SaveApiEndpoint
    @Domain VARCHAR(255),
    @ApiMenuEndpoint VARCHAR(1000),
    @ApiEndpointType VARCHAR(50) = 'unknown',
    @RequiresLocation BIT = 0,
    @AuthenticationMethod VARCHAR(100) = 'none',
    @SiteType VARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        DECLARE @SiteId INT;

        -- Get or create site record
        SELECT @SiteId = site_id FROM target_sites WHERE domain = @Domain;

        IF @SiteId IS NULL
        BEGIN
            INSERT INTO target_sites (domain, site_name)
            VALUES (@Domain, @Domain);
            SET @SiteId = SCOPE_IDENTITY();
        END

        -- Update with API endpoint information
        UPDATE target_sites
        SET api_menu_endpoint = @ApiMenuEndpoint,
            api_endpoint_type = @ApiEndpointType,
            api_requires_location = @RequiresLocation,
            api_authentication_method = @AuthenticationMethod,
            api_endpoint_working = 1,
            api_last_verified = GETDATE(),
            api_verified_count = api_verified_count + 1,
            site_type = COALESCE(@SiteType, site_type),
            updated_at = GETDATE()
        WHERE site_id = @SiteId;

        SELECT @SiteId AS site_id, 'API endpoint saved successfully' AS message;

    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- Verify API endpoint (mark as working)
IF OBJECT_ID('sp_VerifyApiEndpoint') IS NOT NULL DROP PROCEDURE sp_VerifyApiEndpoint;
GO

CREATE PROCEDURE sp_VerifyApiEndpoint
    @Domain VARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE target_sites
    SET api_endpoint_working = 1,
        api_last_verified = GETDATE(),
        api_verified_count = api_verified_count + 1,
        api_failure_reason = NULL,
        updated_at = GETDATE()
    WHERE domain = @Domain
      AND api_menu_endpoint IS NOT NULL;

    SELECT @@ROWCOUNT AS rows_updated;
END;
GO

-- Mark API endpoint as failed
IF OBJECT_ID('sp_MarkApiEndpointFailed') IS NOT NULL DROP PROCEDURE sp_MarkApiEndpointFailed;
GO

CREATE PROCEDURE sp_MarkApiEndpointFailed
    @Domain VARCHAR(255),
    @FailureReason VARCHAR(255) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE target_sites
    SET api_endpoint_working = 0,
        api_last_failed = GETDATE(),
        api_failure_count = api_failure_count + 1,
        api_failure_reason = @FailureReason,
        updated_at = GETDATE()
    WHERE domain = @Domain
      AND api_menu_endpoint IS NOT NULL;

    SELECT @@ROWCOUNT AS rows_updated;
END;
GO

-- Get API endpoint for domain
IF OBJECT_ID('sp_GetApiEndpoint') IS NOT NULL DROP PROCEDURE sp_GetApiEndpoint;
GO

CREATE PROCEDURE sp_GetApiEndpoint
    @Domain VARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        site_id,
        domain,
        site_name,
        api_menu_endpoint,
        api_endpoint_type,
        api_requires_location,
        api_authentication_method,
        api_endpoint_working,
        api_last_verified,
        api_last_failed,
        api_failure_reason,
        api_verified_count,
        api_failure_count,
        site_type,
        cloudflare_protected,
        best_extraction_method
    FROM target_sites
    WHERE domain = @Domain;
END;
GO

-- Get working API endpoints
IF OBJECT_ID('sp_GetWorkingApiEndpoints') IS NOT NULL DROP PROCEDURE sp_GetWorkingApiEndpoints;
GO

CREATE PROCEDURE sp_GetWorkingApiEndpoints
    @MinVerifications INT = 1
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        domain,
        site_name,
        api_menu_endpoint,
        api_endpoint_type,
        api_requires_location,
        api_authentication_method,
        api_last_verified,
        api_verified_count,
        site_type
    FROM target_sites
    WHERE api_endpoint_working = 1
      AND api_menu_endpoint IS NOT NULL
      AND api_verified_count >= @MinVerifications
    ORDER BY api_last_verified DESC;
END;
GO

-- =============================================================================
-- SECTION 7: INITIAL DATA
-- =============================================================================

-- System configuration
IF NOT EXISTS (SELECT 1 FROM system_config WHERE config_key = 'service_name')
BEGIN
    INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
    ('service_name', 'CloudDestroyer', 'string', 'Service name'),
    ('version', '1.0.0', 'string', 'Current version'),
    ('max_concurrent_jobs', '5', 'number', 'Maximum simultaneous scraping jobs'),
    ('default_timeout_seconds', '180', 'number', 'Default request timeout'),
    ('default_rate_limit_ms', '2000', 'number', 'Default delay between requests'),
    ('enable_cloudflare_bypass', 'true', 'boolean', 'Enable Cloudflare bypass'),
    ('enable_selenium_fallback', 'true', 'boolean', 'Enable Selenium for JS rendering'),
    ('session_persistence', 'true', 'boolean', 'Enable session persistence'),
    ('headless_mode', 'true', 'boolean', 'Run browser in headless mode'),
    ('price_enrichment_max_attempts', '3', 'number', 'Max price enrichment attempts'),
    ('price_enrichment_delay_hours', '1', 'number', 'Hours between enrichment attempts');
END
GO

-- Default templates
IF NOT EXISTS (SELECT 1 FROM scraping_templates WHERE template_name = 'menu_extraction')
BEGIN
    INSERT INTO scraping_templates (template_name, job_type, description, default_priority, default_max_retries, estimated_duration_seconds, default_config, extraction_rules)
    VALUES 
    ('menu_extraction', 'menu_extraction', 
     'Extract restaurant menu with Cloudflare bypass and API discovery',
     70, 3, 120,
     '{"bypass_cloudflare": true, "discover_api_endpoints": true, "selenium_fallback": true, "parse_spa": true}',
     '{"api_patterns": ["/api/.*menu.*", "/api/olo/.*"], "dom_selectors": [".menu-item", ".menu-product"], "required_fields": ["name"]}'),
    
    ('price_enrichment', 'price_enrichment',
     'Enrich existing menu data with prices from DOM',
     50, 2, 60,
     '{"use_selenium": true, "wait_for_prices": true}',
     '{"price_patterns": ["\\\\$\\\\d+\\\\.\\\\d{2}"], "price_selectors": [".price", "[class*=price]"]}'),
    
    ('api_endpoint', 'api_endpoint',
     'Direct API endpoint extraction',
     60, 2, 30,
     '{"method": "GET", "timeout_seconds": 30}',
     '{"response_format": "json", "required_status_codes": [200]}');
END
GO

-- Default worker
IF NOT EXISTS (SELECT 1 FROM scraping_workers WHERE worker_id = 'clouddestroyer_primary')
BEGIN
    INSERT INTO scraping_workers (worker_id, worker_name, worker_type, specialization, supported_job_types, max_concurrent_jobs, requires_browser, memory_requirement_mb, config_json, status)
    VALUES 
    ('clouddestroyer_primary', 'CloudDestroyer Primary', 'clouddestroyer', 'cloudflare_bypass',
     '["menu_extraction", "price_enrichment", "api_endpoint"]', 3, 1, 1024,
     '{"headless": true, "session_persistence": true}', 'active');
END
GO

-- Initial health check
IF NOT EXISTS (SELECT 1 FROM health_checks WHERE service_name = 'CloudDestroyer')
BEGIN
    INSERT INTO health_checks (service_name, status, response_time_ms)
    VALUES ('CloudDestroyer', 'healthy', 0);
END
GO

-- =============================================================================
-- SETUP COMPLETE
-- =============================================================================

SELECT 
    'CloudDestroyer database setup complete!' AS message,
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = 'CloudDestroyer') AS total_tables,
    (SELECT COUNT(*) FROM sys.procedures WHERE type = 'P') AS total_procedures,
    (SELECT COUNT(*) FROM sys.views) AS total_views,
    GETDATE() AS completed_at;
GO


