-- CloudDestroyer Job Templates and Initial Data
-- Pre-configured templates for common scraping scenarios

USE FoodFinder;
GO

-- =============================================================================
-- SCRAPING JOB TEMPLATES
-- =============================================================================

-- CloudDestroyer restaurant menu extraction template (based on Bubba's 33 success)
INSERT INTO scraping_job_templates (
    template_name, job_type, description, default_priority, default_max_retries,
    estimated_duration_seconds, default_config, extraction_rules, created_by, version
)
VALUES (
    'CloudDestroyer Restaurant Menu',
    'clouddestroyer_menu',
    'Extract restaurant menu using CloudDestroyer with Cloudflare bypass, API discovery, and Selenium fallback',
    70, -- Higher priority for restaurant jobs
    3,
    120, -- 2 minutes estimated
    JSON_OBJECT(
        'extraction_type', 'restaurant_menu',
        'use_clouddestroyer', 1,
        'bypass_cloudflare', 1,
        'discover_api_endpoints', 1,
        'selenium_fallback', 1,
        'parse_spa', 1,
        'headless_browser', 1,
        'timeout_seconds', 180,
        'rate_limit_delay', JSON_ARRAY(2, 8)
    ),
    JSON_OBJECT(
        'api_patterns', JSON_ARRAY(
            '/api/.*menu.*',
            '/api/olo/.*',
            '/api/.*food.*',
            '/api/.*product.*'
        ),
        'dom_selectors', JSON_ARRAY(
            '.menu-item', '.menu-product', '.dish', '.food-item',
            '[class*="menu"]', '[class*="item"]'
        ),
        'price_patterns', JSON_ARRAY(
            '\$\d+\.\d{2}', '\$\d+', 'price.*\d+'
        ),
        'required_fields', JSON_ARRAY('name'),
        'min_confidence', 0.7
    ),
    'CloudDestroyer_System',
    '1.0'
);

-- Generic API endpoint scraping template
INSERT INTO scraping_job_templates (
    template_name, job_type, description, default_priority, default_max_retries,
    estimated_duration_seconds, default_config, extraction_rules, created_by, version
)
VALUES (
    'Generic API Endpoint',
    'api_endpoint',
    'Generic API endpoint data extraction with authentication and rate limiting',
    50,
    2,
    30,
    JSON_OBJECT(
        'method', 'GET',
        'headers', JSON_OBJECT('User-Agent', 'FoodFinder-Bot/1.0'),
        'timeout_seconds', 30,
        'follow_redirects', 1,
        'verify_ssl', 1
    ),
    JSON_OBJECT(
        'response_format', 'json',
        'required_status_codes', JSON_ARRAY(200, 201),
        'data_path', '$',
        'pagination_support', 0
    ),
    'FoodFinder_System',
    '1.0'
);

-- Content monitoring template
INSERT INTO scraping_job_templates (
    template_name, job_type, description, default_priority, default_max_retries,
    estimated_duration_seconds, default_config, extraction_rules, created_by, version
)
VALUES (
    'Website Content Monitor',
    'content_monitor',
    'Monitor website content changes for price updates, menu changes, etc.',
    30, -- Lower priority for monitoring
    1,
    45,
    JSON_OBJECT(
        'check_frequency', 'daily',
        'store_full_content', 0,
        'detect_changes', 1,
        'notify_on_change', 1
    ),
    JSON_OBJECT(
        'monitor_selectors', JSON_ARRAY(
            '.price', '.menu-item', '.availability'
        ),
        'change_threshold', 0.1,
        'ignore_patterns', JSON_ARRAY(
            'last updated', 'copyright', 'date'
        )
    ),
    'FoodFinder_System',
    '1.0'
);

-- E-commerce price tracking template
INSERT INTO scraping_job_templates (
    template_name, job_type, description, default_priority, default_max_retries,
    estimated_duration_seconds, default_config, extraction_rules, created_by, version
)
VALUES (
    'Price Tracker',
    'price_tracker',
    'Track product prices across e-commerce sites and delivery platforms',
    60,
    2,
    60,
    JSON_OBJECT(
        'track_historical_prices', 1,
        'detect_sales', 1,
        'notify_price_drops', 1,
        'currency', 'USD'
    ),
    JSON_OBJECT(
        'price_selectors', JSON_ARRAY(
            '.price', '.cost', '[class*="price"]', '[data-price]'
        ),
        'availability_selectors', JSON_ARRAY(
            '.in-stock', '.available', '[class*="stock"]'
        ),
        'exclude_patterns', JSON_ARRAY(
            'shipping', 'tax', 'estimated'
        )
    ),
    'FoodFinder_System',
    '1.0'
);

GO

-- =============================================================================
-- WORKER REGISTRATIONS
-- =============================================================================

-- Register CloudDestroyer worker
INSERT INTO scraping_workers (
    worker_id, worker_name, worker_type, specialization,
    supported_job_types, max_concurrent_jobs, requires_browser,
    memory_requirement_mb, average_job_duration_seconds,
    config_json, status
)
VALUES (
    'clouddestroyer_primary',
    'CloudDestroyer Primary Worker',
    'clouddestroyer',
    'restaurant_menus',
    JSON_ARRAY('clouddestroyer_menu', 'api_endpoint'),
    3, -- Can handle 3 concurrent jobs
    1, -- Requires browser for Selenium
    1024, -- 1GB memory requirement
    120, -- 2 minutes average
    JSON_OBJECT(
        'headless_browser', 1,
        'session_persistence', 1,
        'max_retries', 3,
        'timeout', 180,
        'delay_range', JSON_ARRAY(1, 3)
    ),
    'active'
);

-- Register generic API worker
INSERT INTO scraping_workers (
    worker_id, worker_name, worker_type, specialization,
    supported_job_types, max_concurrent_jobs, requires_browser,
    memory_requirement_mb, average_job_duration_seconds,
    config_json, status
)
VALUES (
    'api_client_primary',
    'Generic API Client',
    'api_client',
    'api_endpoints',
    JSON_ARRAY('api_endpoint', 'content_monitor', 'price_tracker'),
    10, -- Lightweight, can handle more jobs
    0, -- No browser needed
    256, -- 256MB memory
    30, -- 30 seconds average
    JSON_OBJECT(
        'rate_limit_requests_per_minute', 60,
        'connection_pool_size', 10,
        'timeout_seconds', 30
    ),
    'active'
);

GO

-- =============================================================================
-- SYSTEM CONFIGURATION
-- =============================================================================

-- Add CloudDestroyer system configuration
INSERT INTO system_config (config_key, config_value, config_type, description, is_public)
VALUES 
    ('clouddestroyer.enabled', 'true', 'boolean', 'Enable CloudDestroyer automation system', 0),
    ('clouddestroyer.max_concurrent_jobs', '5', 'number', 'Maximum concurrent CloudDestroyer jobs', 0),
    ('clouddestroyer.default_timeout', '180', 'number', 'Default job timeout in seconds', 0),
    ('clouddestroyer.rate_limit_delay_min', '2', 'number', 'Minimum delay between requests (seconds)', 0),
    ('clouddestroyer.rate_limit_delay_max', '8', 'number', 'Maximum delay between requests (seconds)', 0),
    ('clouddestroyer.session_persistence', 'true', 'boolean', 'Enable session persistence across requests', 0),
    ('clouddestroyer.headless_browser', 'true', 'boolean', 'Run browser in headless mode', 0),
    
    ('scraping.queue_check_interval', '10', 'number', 'How often to check queue for new jobs (seconds)', 0),
    ('scraping.max_retries_default', '3', 'number', 'Default maximum retries for failed jobs', 0),
    ('scraping.cleanup_completed_jobs_days', '30', 'number', 'Days to keep completed job records', 0),
    ('scraping.priority_boost_high_rating', '20', 'number', 'Priority boost for restaurants with rating >= 4.5', 0),
    
    ('monitoring.job_timeout_alert_minutes', '15', 'number', 'Alert if job runs longer than this (minutes)', 0),
    ('monitoring.worker_heartbeat_timeout_minutes', '5', 'number', 'Consider worker dead after this timeout', 0),
    ('monitoring.queue_size_alert_threshold', '100', 'number', 'Alert if queue grows beyond this size', 0);

GO

-- =============================================================================
-- SAMPLE DATA AND TESTING
-- =============================================================================

-- Create a sample batch for testing (using existing restaurant if available)
DECLARE @SampleSessionId VARCHAR(100) = 'test_session_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss');

-- Insert sample session (if restaurants exist)
IF EXISTS (SELECT 1 FROM restaurants WHERE website IS NOT NULL)
BEGIN
    -- Create sample automation session
    EXEC spsc_CreateJob
        @JobType = 'clouddestroyer_menu',
        @TargetUrl = 'https://bubbas33.com/menu',
        @JobName = 'Test: Bubba''s 33 Menu Extraction',
        @EntityType = 'restaurant',
        @EntityId = 'test_bubbas33',
        @Priority = 90,
        @ScrapingConfig = '{"extraction_type": "restaurant_menu", "bypass_cloudflare": true, "discover_api": true}',
        @SessionId = @SampleSessionId,
        @JobId = NULL;
END;

GO

-- =============================================================================
-- USEFUL QUERIES FOR MONITORING
-- =============================================================================

-- View for monitoring CloudDestroyer job performance
CREATE VIEW v_clouddestroyer_monitoring AS
SELECT 
    -- Current queue status
    (SELECT COUNT(*) FROM universal_scraping_jobs WHERE status = 'pending' AND job_type = 'clouddestroyer_menu') as pending_restaurant_jobs,
    (SELECT COUNT(*) FROM universal_scraping_jobs WHERE status = 'running' AND job_type = 'clouddestroyer_menu') as running_restaurant_jobs,
    (SELECT COUNT(*) FROM universal_scraping_jobs WHERE status = 'completed' AND job_type = 'clouddestroyer_menu' AND completed_at >= CAST(GETDATE() AS DATE)) as completed_today,
    (SELECT COUNT(*) FROM universal_scraping_jobs WHERE status = 'failed' AND job_type = 'clouddestroyer_menu' AND completed_at >= CAST(GETDATE() AS DATE)) as failed_today,
    
    -- Performance metrics
    (SELECT AVG(CAST(actual_duration_seconds AS FLOAT)) FROM universal_scraping_jobs WHERE status = 'completed' AND job_type = 'clouddestroyer_menu' AND completed_at >= DATEADD(HOUR, -24, GETDATE())) as avg_processing_time_24h,
    (SELECT AVG(CAST(items_extracted AS FLOAT)) FROM universal_scraping_jobs WHERE status = 'completed' AND job_type = 'clouddestroyer_menu' AND items_extracted > 0 AND completed_at >= DATEADD(HOUR, -24, GETDATE())) as avg_items_extracted_24h,
    
    -- Success rates
    (SELECT CAST(SUM(CASE WHEN status = 'completed' THEN 1.0 ELSE 0 END) / COUNT(*) AS DECIMAL(3,2)) FROM universal_scraping_jobs WHERE job_type = 'clouddestroyer_menu' AND completed_at >= DATEADD(DAY, -7, GETDATE())) as success_rate_7d,
    
    -- Worker status
    (SELECT COUNT(*) FROM scraping_workers WHERE status = 'active' AND worker_type = 'clouddestroyer') as active_clouddestroyer_workers,
    (SELECT SUM(current_jobs) FROM scraping_workers WHERE status = 'active' AND worker_type = 'clouddestroyer') as total_active_jobs,
    
    -- Last update
    GETDATE() as last_updated;

GO

-- Create alerts view for monitoring dashboard
CREATE VIEW v_scraping_alerts AS
SELECT 
    'High Queue Size' as alert_type,
    'warning' as severity,
    'Queue has ' + CAST(COUNT(*) AS VARCHAR(10)) + ' pending jobs' as message,
    GETDATE() as alert_time
FROM universal_scraping_jobs 
WHERE status = 'pending'
HAVING COUNT(*) > 50

UNION ALL

SELECT 
    'Stuck Jobs' as alert_type,
    'error' as severity,
    'Jobs running for over 30 minutes: ' + CAST(COUNT(*) AS VARCHAR(10)) as message,
    GETDATE() as alert_time
FROM universal_scraping_jobs 
WHERE status = 'running' 
AND started_at < DATEADD(MINUTE, -30, GETDATE())
HAVING COUNT(*) > 0

UNION ALL

SELECT 
    'Dead Workers' as alert_type,
    'error' as severity,
    'Workers with no heartbeat: ' + worker_id as message,
    GETDATE() as alert_time
FROM scraping_workers 
WHERE status = 'active' 
AND (last_heartbeat IS NULL OR last_heartbeat < DATEADD(MINUTE, -10, GETDATE()));

GO

PRINT 'CloudDestroyer integration setup completed successfully!';
PRINT '';
PRINT 'Next steps:';
PRINT '1. Update master setup script to include new files';
PRINT '2. Test with: EXEC spcd_CreateRestaurantJob @RestaurantId=''test'', @TargetUrl=''https://bubbas33.com/menu''';
PRINT '3. Monitor with: SELECT * FROM v_clouddestroyer_monitoring';
PRINT '4. View queue: SELECT * FROM v_clouddestroyer_queue ORDER BY effective_priority DESC';
GO