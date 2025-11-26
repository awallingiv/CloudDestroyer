-- SQL Server Compatible Initial Data
-- Fixed templates without JSON_OBJECT function

USE FoodFinder;
GO

-- Clear any failed template insertions
DELETE FROM scraping_job_templates;
DELETE FROM scraping_workers;
GO

-- CloudDestroyer restaurant menu extraction template (SQL Server compatible)
INSERT INTO scraping_job_templates (
    template_name, job_type, description, default_priority, default_max_retries,
    estimated_duration_seconds, default_config, extraction_rules, created_by, version
)
VALUES (
    'CloudDestroyer Restaurant Menu',
    'clouddestroyer_menu', 
    'Extract restaurant menu using CloudDestroyer with Cloudflare bypass, API discovery, and Selenium fallback',
    70,
    3,
    120,
    '{
        "extraction_type": "restaurant_menu",
        "use_clouddestroyer": true,
        "bypass_cloudflare": true,
        "discover_api_endpoints": true,
        "selenium_fallback": true,
        "parse_spa": true,
        "headless_browser": true,
        "timeout_seconds": 180,
        "rate_limit_delay": [2, 8]
    }',
    '{
        "api_patterns": [
            "/api/.*menu.*",
            "/api/olo/.*", 
            "/api/.*food.*",
            "/api/.*product.*"
        ],
        "dom_selectors": [
            ".menu-item", ".menu-product", ".dish", ".food-item",
            "[class*=\"menu\"]", "[class*=\"item\"]"
        ],
        "price_patterns": [
            "\\$\\d+\\.\\d{2}", "\\$\\d+", "price.*\\d+"
        ],
        "required_fields": ["name"],
        "min_confidence": 0.7
    }',
    'CloudDestroyer_System',
    '1.0'
);

-- Generic API endpoint template
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
    '{
        "method": "GET",
        "headers": {"User-Agent": "FoodFinder-Bot/1.0"},
        "timeout_seconds": 30,
        "follow_redirects": true,
        "verify_ssl": true
    }',
    '{
        "response_format": "json",
        "required_status_codes": [200, 201],
        "data_path": "$",
        "pagination_support": false
    }',
    'FoodFinder_System',
    '1.0'
);

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
    '["clouddestroyer_menu", "api_endpoint"]',
    3,
    1,
    1024,
    120,
    '{
        "headless_browser": true,
        "session_persistence": true,
        "max_retries": 3,
        "timeout": 180,
        "delay_range": [1, 3]
    }',
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
    '["api_endpoint", "content_monitor", "price_tracker"]',
    10,
    0,
    256,
    30,
    '{
        "rate_limit_requests_per_minute": 60,
        "connection_pool_size": 10,
        "timeout_seconds": 30
    }',
    'active'
);

PRINT 'Fixed templates and workers inserted successfully!';
GO