-- Universal Scraping Queue System
-- Replaces basic scraping_jobs with comprehensive, generic scraping infrastructure
-- Supports CloudDestroyer, API scraping, content monitoring, and any future scraping needs

USE FoodFinder;
GO

-- =============================================================================
-- UNIVERSAL SCRAPING QUEUE SYSTEM
-- =============================================================================

-- Drop existing limited scraping_jobs table if it exists
IF OBJECT_ID('scraping_jobs') IS NOT NULL
    DROP TABLE scraping_jobs;
GO

-- Universal scraping job queue (supports any scraping task)
CREATE TABLE universal_scraping_jobs (
    job_id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Job identification
    job_type VARCHAR(50) NOT NULL, -- 'clouddestroyer_menu', 'api_endpoint', 'content_monitor', 'price_check', etc.
    job_category VARCHAR(30) NOT NULL DEFAULT 'scraping' CHECK (job_category IN ('scraping', 'api', 'monitoring', 'analysis', 'batch')),
    job_name VARCHAR(255), -- Human-readable job name
    
    -- Target specification (flexible for any source)
    target_url VARCHAR(1000), -- Primary target URL
    target_domain VARCHAR(255), -- Extracted domain for grouping
    target_type VARCHAR(50) DEFAULT 'website', -- 'website', 'api', 'file', 'database'
    
    -- Related entity (optional - for restaurant scraping, this would be restaurant_id)
    entity_type VARCHAR(50), -- 'restaurant', 'product', 'article', 'user', etc.
    entity_id VARCHAR(100), -- Flexible ID that can reference any entity
    
    -- Job configuration (JSON for maximum flexibility)
    scraping_config NVARCHAR(MAX) CHECK (scraping_config IS NULL OR ISJSON(scraping_config) = 1),
    extraction_rules NVARCHAR(MAX) CHECK (extraction_rules IS NULL OR ISJSON(extraction_rules) = 1),
    
    -- Queue management
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'blocked', 'cancelled', 'retry', 'paused')),
    priority INT DEFAULT 50, -- 1-100, higher is more urgent
    
    -- Scheduling and retry logic
    scheduled_at DATETIME2 DEFAULT GETDATE(),
    earliest_start_at DATETIME2 DEFAULT GETDATE(), -- For delayed execution
    started_at DATETIME2 NULL,
    completed_at DATETIME2 NULL,
    
    -- Retry management
    attempts INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_delay_minutes INT DEFAULT 5,
    next_retry_at DATETIME2 NULL,
    
    -- Error handling
    last_error_message NVARCHAR(MAX),
    error_code VARCHAR(100),
    error_category VARCHAR(50), -- 'network', 'parsing', 'blocked', 'rate_limit', 'config'
    
    -- Worker tracking
    worker_id VARCHAR(100),
    worker_type VARCHAR(50), -- 'clouddestroyer', 'selenium', 'api_client', 'custom'
    processing_node VARCHAR(100), -- For distributed processing
    
    -- Performance metrics
    estimated_duration_seconds INT DEFAULT 60,
    actual_duration_seconds DECIMAL(8,2),
    
    -- Results summary (detailed results go in separate table)
    items_extracted INT DEFAULT 0,
    data_quality_score INT DEFAULT 0, -- 0-100 quality assessment
    success_indicators NVARCHAR(500), -- Comma-separated success metrics
    
    -- Dependency management
    depends_on_job_id INT NULL, -- Chain jobs together
    batch_id VARCHAR(100), -- Group related jobs
    session_id VARCHAR(100), -- CloudDestroyer automation sessions
    
    -- Timestamps
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    expires_at DATETIME2 NULL, -- Auto-cleanup old jobs
    
    -- Foreign key constraints (flexible)
    CONSTRAINT FK_universal_scraping_depends 
        FOREIGN KEY (depends_on_job_id) REFERENCES universal_scraping_jobs(job_id)
);
GO

-- Universal scraping results storage
CREATE TABLE universal_scraping_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    job_id INT NOT NULL,
    
    -- Result metadata
    result_type VARCHAR(50) NOT NULL, -- 'menu_data', 'api_response', 'html_content', 'extracted_data'
    data_schema VARCHAR(100), -- Schema/version for data interpretation
    
    -- Quality and confidence metrics
    confidence_score DECIMAL(3,2) DEFAULT 1.0, -- 0.00 to 1.00
    completeness_score DECIMAL(3,2) DEFAULT 1.0, -- How complete is the extraction
    accuracy_indicators NVARCHAR(MAX) CHECK (accuracy_indicators IS NULL OR ISJSON(accuracy_indicators) = 1),
    
    -- Data storage (flexible formats)
    raw_data NVARCHAR(MAX), -- Original scraped content
    structured_data NVARCHAR(MAX) CHECK (structured_data IS NULL OR ISJSON(structured_data) = 1), -- Parsed/structured data
    summary_data NVARCHAR(MAX) CHECK (summary_data IS NULL OR ISJSON(summary_data) = 1), -- Key metrics and summaries
    
    -- Data classification
    data_size_bytes INT DEFAULT 0,
    record_count INT DEFAULT 0,
    unique_fields_found INT DEFAULT 0,
    
    -- Processing metadata
    extraction_method VARCHAR(100), -- 'clouddestroyer_api', 'selenium_dom', 'api_direct', 'regex_parse'
    processing_time_seconds DECIMAL(8,2) DEFAULT 0,
    memory_usage_mb INT DEFAULT 0,
    
    -- Validation and verification
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid', 'partial', 'unknown')),
    validation_errors NVARCHAR(MAX),
    verified_at DATETIME2 NULL,
    verified_by VARCHAR(100),
    
    -- Timestamps
    extracted_at DATETIME2 DEFAULT GETDATE(),
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_universal_scraping_results_job 
        FOREIGN KEY (job_id) REFERENCES universal_scraping_jobs(job_id) ON DELETE CASCADE
);
GO

-- Scraping job templates (reusable configurations)
CREATE TABLE scraping_job_templates (
    template_id INT IDENTITY(1,1) PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    
    -- Template configuration
    default_config NVARCHAR(MAX) CHECK (default_config IS NULL OR ISJSON(default_config) = 1),
    extraction_rules NVARCHAR(MAX) CHECK (extraction_rules IS NULL OR ISJSON(extraction_rules) = 1),
    
    -- Default settings
    default_priority INT DEFAULT 50,
    default_max_retries INT DEFAULT 3,
    estimated_duration_seconds INT DEFAULT 60,
    
    -- Template metadata
    description NVARCHAR(MAX),
    created_by VARCHAR(100),
    version VARCHAR(20) DEFAULT '1.0',
    is_active BIT DEFAULT 1,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT UQ_scraping_templates_name UNIQUE (template_name)
);
GO

-- Worker/scraper registration and capabilities
CREATE TABLE scraping_workers (
    worker_id VARCHAR(100) PRIMARY KEY,
    worker_name VARCHAR(255) NOT NULL,
    worker_type VARCHAR(50) NOT NULL, -- 'clouddestroyer', 'selenium', 'api_client'
    
    -- Capabilities
    supported_job_types NVARCHAR(MAX) CHECK (supported_job_types IS NULL OR ISJSON(supported_job_types) = 1),
    max_concurrent_jobs INT DEFAULT 1,
    specialization VARCHAR(100), -- 'restaurant_menus', 'ecommerce', 'news', 'generic'
    
    -- Performance characteristics
    average_job_duration_seconds INT DEFAULT 60,
    success_rate DECIMAL(3,2) DEFAULT 1.0,
    reliability_score INT DEFAULT 100, -- 0-100
    
    -- Resource requirements
    memory_requirement_mb INT DEFAULT 512,
    requires_browser BIT DEFAULT 0,
    requires_proxy BIT DEFAULT 0,
    
    -- Status and health
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'error')),
    last_heartbeat DATETIME2 NULL,
    current_jobs INT DEFAULT 0,
    
    -- Configuration
    config_json NVARCHAR(MAX) CHECK (config_json IS NULL OR ISJSON(config_json) = 1),
    
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Job execution history and analytics
CREATE TABLE scraping_job_history (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    job_id INT NOT NULL,
    
    -- Execution tracking
    execution_attempt INT NOT NULL,
    worker_id VARCHAR(100),
    
    -- Timing
    started_at DATETIME2 NOT NULL,
    completed_at DATETIME2 NULL,
    duration_seconds DECIMAL(8,2),
    
    -- Results
    status VARCHAR(20) NOT NULL,
    items_found INT DEFAULT 0,
    error_message NVARCHAR(MAX),
    
    -- Performance metrics
    cpu_usage_percent DECIMAL(5,2),
    memory_usage_mb INT,
    network_requests INT DEFAULT 0,
    
    created_at DATETIME2 DEFAULT GETDATE(),
    
    CONSTRAINT FK_scraping_history_job 
        FOREIGN KEY (job_id) REFERENCES universal_scraping_jobs(job_id) ON DELETE CASCADE
);
GO

-- Create comprehensive indexes
CREATE INDEX idx_universal_scraping_jobs_status_priority ON universal_scraping_jobs (status, priority DESC);
CREATE INDEX idx_universal_scraping_jobs_type_category ON universal_scraping_jobs (job_type, job_category);
CREATE INDEX idx_universal_scraping_jobs_entity ON universal_scraping_jobs (entity_type, entity_id);
CREATE INDEX idx_universal_scraping_jobs_domain ON universal_scraping_jobs (target_domain);
CREATE INDEX idx_universal_scraping_jobs_scheduled ON universal_scraping_jobs (scheduled_at, earliest_start_at);
CREATE INDEX idx_universal_scraping_jobs_batch ON universal_scraping_jobs (batch_id);
CREATE INDEX idx_universal_scraping_jobs_session ON universal_scraping_jobs (session_id);
CREATE INDEX idx_universal_scraping_jobs_worker ON universal_scraping_jobs (worker_id, status);
CREATE INDEX idx_universal_scraping_jobs_retry ON universal_scraping_jobs (next_retry_at) WHERE next_retry_at IS NOT NULL;

CREATE INDEX idx_universal_scraping_results_job ON universal_scraping_results (job_id);
CREATE INDEX idx_universal_scraping_results_type ON universal_scraping_results (result_type);
CREATE INDEX idx_universal_scraping_results_confidence ON universal_scraping_results (confidence_score DESC);
CREATE INDEX idx_universal_scraping_results_extracted ON universal_scraping_results (extracted_at);

CREATE INDEX idx_scraping_templates_type ON scraping_job_templates (job_type);
CREATE INDEX idx_scraping_templates_active ON scraping_job_templates (is_active);

CREATE INDEX idx_scraping_workers_type ON scraping_workers (worker_type);
CREATE INDEX idx_scraping_workers_status ON scraping_workers (status);

CREATE INDEX idx_scraping_history_job_attempt ON scraping_job_history (job_id, execution_attempt);
CREATE INDEX idx_scraping_history_worker ON scraping_job_history (worker_id);
GO

-- Update triggers for universal_scraping_jobs
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
END;
GO

-- Update triggers for scraping_job_templates
CREATE TRIGGER tr_scraping_templates_updated_at
ON scraping_job_templates
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE scraping_job_templates 
    SET updated_at = GETDATE()
    FROM scraping_job_templates t
    INNER JOIN inserted i ON t.template_id = i.template_id;
END;
GO

-- Update triggers for scraping_workers
CREATE TRIGGER tr_scraping_workers_updated_at
ON scraping_workers
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE scraping_workers 
    SET updated_at = GETDATE()
    FROM scraping_workers w
    INNER JOIN inserted i ON w.worker_id = i.worker_id;
END;
GO