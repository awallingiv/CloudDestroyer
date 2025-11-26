-- CloudDestroyer Integration Extensions
-- Adds CloudDestroyer-specific columns to existing tables and creates integration views

USE FoodFinder;
GO

-- =============================================================================
-- RESTAURANT TABLE EXTENSIONS FOR CLOUDDESTROYER
-- =============================================================================

-- Add CloudDestroyer-specific columns to existing restaurants table
ALTER TABLE restaurants ADD 
    -- CloudDestroyer automation metadata
    clouddestroyer_status VARCHAR(20) DEFAULT 'not_processed' CHECK (clouddestroyer_status IN ('not_processed', 'queued', 'processing', 'success', 'failed', 'blocked', 'no_menu')),
    clouddestroyer_last_attempt DATETIME2 NULL,
    clouddestroyer_attempts INT DEFAULT 0,
    
    -- Website analysis results
    website_type VARCHAR(30) NULL, -- 'react_spa', 'angular_spa', 'static_html', 'api_driven'  
    requires_selenium BIT DEFAULT 0,
    api_endpoints_discovered NVARCHAR(MAX) CHECK (api_endpoints_discovered IS NULL OR ISJSON(api_endpoints_discovered) = 1),
    
    -- Success metrics
    extraction_success_rate DECIMAL(3,2) DEFAULT 0, -- 0.00 to 1.00
    average_extraction_time DECIMAL(8,2) DEFAULT 0,
    best_extraction_method VARCHAR(50) NULL, -- 'api_endpoint', 'selenium_spa', 'dom_scraping'
    
    -- Quality indicators
    menu_completeness_score INT DEFAULT 0, -- 0-100
    last_successful_extraction DATETIME2 NULL,
    total_items_extracted INT DEFAULT 0;
GO

-- Create indexes for new columns
CREATE INDEX idx_restaurants_clouddestroyer_status ON restaurants (clouddestroyer_status);
CREATE INDEX idx_restaurants_website_type ON restaurants (website_type);
CREATE INDEX idx_restaurants_extraction_success ON restaurants (extraction_success_rate DESC);
CREATE INDEX idx_restaurants_last_successful ON restaurants (last_successful_extraction);
GO

-- =============================================================================
-- INTEGRATION VIEWS
-- =============================================================================

-- Comprehensive restaurant scraping status view
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
    
    -- Current job status
    j.job_id as current_job_id,
    j.status as current_job_status,
    j.priority as current_job_priority,
    j.attempts as current_job_attempts,
    j.started_at as current_job_started,
    j.worker_id as assigned_worker,
    
    -- Performance metrics
    DATEDIFF(DAY, r.last_successful_extraction, GETDATE()) as days_since_success,
    CASE 
        WHEN r.total_items_extracted > 0 THEN 'Has Menu'
        WHEN r.clouddestroyer_status = 'no_menu' THEN 'No Menu Available'
        WHEN r.clouddestroyer_status IN ('failed', 'blocked') THEN 'Extraction Failed'
        WHEN r.clouddestroyer_status IN ('queued', 'processing') THEN 'In Progress'
        ELSE 'Not Processed'
    END as status_summary,
    
    -- Menu item counts
    (SELECT COUNT(*) FROM menu_items mi WHERE mi.restaurant_id = r.restaurant_id) as current_menu_item_count,
    (SELECT COUNT(DISTINCT category_id) FROM menu_items mi WHERE mi.restaurant_id = r.restaurant_id) as current_category_count
    
FROM restaurants r
LEFT JOIN universal_scraping_jobs j ON r.restaurant_id = j.entity_id 
    AND j.entity_type = 'restaurant' 
    AND j.status IN ('pending', 'running')
    AND j.job_type = 'clouddestroyer_menu';
GO

-- CloudDestroyer performance analytics view
CREATE VIEW v_clouddestroyer_analytics AS
SELECT 
    -- Time periods
    CAST(j.created_at AS DATE) as extraction_date,
    DATEPART(HOUR, j.created_at) as extraction_hour,
    
    -- Job statistics
    COUNT(*) as total_jobs,
    SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) as successful_jobs,
    SUM(CASE WHEN j.status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
    SUM(CASE WHEN j.status IN ('pending', 'running') THEN 1 ELSE 0 END) as active_jobs,
    
    -- Performance metrics
    AVG(CAST(j.actual_duration_seconds AS FLOAT)) as avg_processing_time,
    SUM(j.items_extracted) as total_items_extracted,
    AVG(CAST(j.data_quality_score AS FLOAT)) as avg_quality_score,
    
    -- Success rates by method
    SUM(CASE WHEN r.extraction_method = 'clouddestroyer_api' AND j.status = 'completed' THEN 1 ELSE 0 END) as api_successes,
    SUM(CASE WHEN r.extraction_method = 'selenium_spa' AND j.status = 'completed' THEN 1 ELSE 0 END) as selenium_successes,
    SUM(CASE WHEN r.extraction_method = 'dom_scraping' AND j.status = 'completed' THEN 1 ELSE 0 END) as dom_successes,
    
    -- Website type analysis
    SUM(CASE WHEN rest.website_type = 'react_spa' THEN 1 ELSE 0 END) as react_sites,
    SUM(CASE WHEN rest.website_type = 'angular_spa' THEN 1 ELSE 0 END) as angular_sites,
    SUM(CASE WHEN rest.website_type = 'static_html' THEN 1 ELSE 0 END) as static_sites,
    SUM(CASE WHEN rest.website_type = 'api_driven' THEN 1 ELSE 0 END) as api_driven_sites

FROM universal_scraping_jobs j
LEFT JOIN universal_scraping_results r ON j.job_id = r.job_id
LEFT JOIN restaurants rest ON j.entity_id = rest.restaurant_id AND j.entity_type = 'restaurant'
WHERE j.job_type = 'clouddestroyer_menu'
AND j.created_at >= DATEADD(DAY, -30, GETDATE())
GROUP BY CAST(j.created_at AS DATE), DATEPART(HOUR, j.created_at);
GO

-- Queue priority view for CloudDestroyer jobs
CREATE VIEW v_clouddestroyer_queue AS
SELECT 
    j.job_id,
    j.priority,
    j.created_at,
    j.attempts,
    j.max_retries,
    j.next_retry_at,
    
    -- Restaurant details
    r.restaurant_id,
    r.name as restaurant_name,
    r.google_rating,
    r.price_level,
    r.website_type,
    r.clouddestroyer_attempts,
    
    -- Priority factors
    CASE 
        WHEN r.google_rating >= 4.5 THEN 20
        WHEN r.google_rating >= 4.0 THEN 10
        WHEN r.google_rating >= 3.5 THEN 5
        ELSE 0
    END as rating_bonus,
    
    CASE 
        WHEN r.website_type IN ('react_spa', 'angular_spa') THEN 15 -- Harder to scrape, higher priority
        WHEN r.website_type = 'api_driven' THEN 25 -- Likely to be successful
        ELSE 0
    END as complexity_bonus,
    
    CASE 
        WHEN r.clouddestroyer_attempts = 0 THEN 30 -- First attempt gets priority
        WHEN r.clouddestroyer_attempts <= 2 THEN 10
        ELSE -10 -- Multiple failures get lower priority
    END as attempt_penalty,
    
    -- Calculated effective priority
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

-- =============================================================================
-- INTEGRATION FUNCTIONS
-- =============================================================================

-- Function to calculate restaurant extraction priority
CREATE FUNCTION fn_CalculateExtractionPriority(
    @GoogleRating DECIMAL(2,1),
    @WebsiteType VARCHAR(30),
    @AttemptCount INT,
    @LastAttempt DATETIME2
)
RETURNS INT
AS
BEGIN
    DECLARE @Priority INT = 50; -- Base priority
    
    -- Rating bonus
    SET @Priority = @Priority + CASE 
        WHEN @GoogleRating >= 4.5 THEN 20
        WHEN @GoogleRating >= 4.0 THEN 10
        WHEN @GoogleRating >= 3.5 THEN 5
        ELSE 0
    END;
    
    -- Website type bonus
    SET @Priority = @Priority + CASE 
        WHEN @WebsiteType = 'api_driven' THEN 25 -- High success rate
        WHEN @WebsiteType IN ('react_spa', 'angular_spa') THEN 15 -- Complex but valuable
        WHEN @WebsiteType = 'static_html' THEN 5 -- Easy to process
        ELSE 0
    END;
    
    -- Attempt penalty
    SET @Priority = @Priority + CASE 
        WHEN @AttemptCount = 0 THEN 30 -- First attempt
        WHEN @AttemptCount <= 2 THEN 10 -- Early attempts
        WHEN @AttemptCount <= 5 THEN 0 -- Normal attempts
        ELSE -20 -- Too many failures
    END;
    
    -- Time-based bonus (older attempts get priority)
    IF @LastAttempt IS NOT NULL
    BEGIN
        DECLARE @DaysOld INT = DATEDIFF(DAY, @LastAttempt, GETDATE());
        SET @Priority = @Priority + CASE 
            WHEN @DaysOld >= 30 THEN 15 -- Long time since last attempt
            WHEN @DaysOld >= 7 THEN 10 -- Weekly retry
            WHEN @DaysOld >= 1 THEN 5 -- Daily retry
            ELSE 0
        END;
    END;
    
    RETURN CASE WHEN @Priority > 100 THEN 100 WHEN @Priority < 1 THEN 1 ELSE @Priority END;
END;
GO