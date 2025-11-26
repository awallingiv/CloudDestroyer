-- FoodFinder Useful Queries for Development and Operations
-- Common queries for testing, debugging, and monitoring

USE FoodFinder;
GO

-- =============================================================================
-- RESTAURANT AND MENU QUERIES
-- =============================================================================

-- Find restaurants with menu data in a specific location
-- Example: San Antonio, TX area
SELECT TOP 20
    r.name,
    r.address,
    r.google_rating,
    r.is_chain,
    r.chain_name,
    COUNT(mi.item_id) as menu_items_count,
    r.scrape_status,
    r.last_scraped_at
FROM restaurants r
LEFT JOIN menu_items mi ON r.restaurant_id = mi.restaurant_id
WHERE r.latitude BETWEEN 29.2 AND 29.5 
  AND r.longitude BETWEEN -98.8 AND -98.4
GROUP BY r.restaurant_id, r.name, r.address, r.google_rating, r.is_chain, r.chain_name, r.scrape_status, r.last_scraped_at
ORDER BY menu_items_count DESC, r.google_rating DESC;
GO

-- Search for menu items by keyword with relevance scoring
SELECT TOP 25
    r.name as restaurant_name,
    r.address,
    mi.name as item_name,
    mi.description,
    mi.price,
    mi.confidence_score,
    mi.source
FROM restaurants r
JOIN menu_items mi ON r.restaurant_id = mi.restaurant_id
WHERE (
    CONTAINS((mi.name, mi.description), 'burger')
    OR mi.name LIKE '%burger%'
    OR mi.normalized_name LIKE '%burger%'
)
AND mi.is_available = 1
ORDER BY mi.confidence_score DESC, mi.price ASC;
GO

-- Find restaurants needing to be scraped
SELECT TOP 50
    r.name,
    r.website,
    r.menu_url,
    r.scrape_status,
    r.last_scraped,
    DATEDIFF(DAY, r.last_scraped, GETDATE()) as days_since_scraped,
    COUNT(mi.item_id) as current_menu_items
FROM restaurants r
LEFT JOIN menu_categories mc ON r.restaurant_id = mc.restaurant_id
LEFT JOIN menu_items mi ON mc.category_id = mi.category_id
WHERE (
    r.scrape_status IN ('pending', 'failed')
    OR (r.last_scraped < DATEADD(DAY, -7, GETDATE()) AND r.scrape_status = 'completed')
    OR r.last_scraped IS NULL
)
AND r.website IS NOT NULL
GROUP BY r.restaurant_id, r.name, r.website, r.menu_url, r.scrape_status, r.last_scraped, r.created_at
ORDER BY days_since_scraped DESC, r.created_at DESC;
GO

-- =============================================================================
-- SEARCH AND ANALYTICS QUERIES
-- =============================================================================

-- Get popular search terms with trends
SELECT TOP 20
    search_term,
    search_count,
    decay_score,
    last_searched,
    DATEDIFF(DAY, last_searched, GETDATE()) as days_since_last_search
FROM popular_searches
ORDER BY search_count DESC, decay_score DESC;
GO

-- Analyze search performance
SELECT 
    CAST(created_at AS DATE) as search_date,
    COUNT(*) as total_searches,
    AVG(execution_time_ms) as avg_execution_time,
    AVG(total_restaurants_found) as avg_restaurants_found,
    AVG(total_menu_items_found) as avg_menu_items_found,
    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits,
    ROUND(SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as cache_hit_rate
FROM search_queries
WHERE created_at >= DATEADD(DAY, -7, GETDATE())
GROUP BY CAST(created_at AS DATE)
ORDER BY search_date DESC;
GO

-- Find most engaged locations
SELECT TOP 15
    city,
    state,
    total_searches,
    unique_users,
    total_restaurants,
    restaurants_with_menus,
    ROUND(restaurants_with_menus * 100.0 / total_restaurants, 2) as menu_coverage_percent
FROM location_analytics
WHERE total_searches > 10
ORDER BY total_searches DESC;
GO

-- =============================================================================
-- OPERATIONAL QUERIES
-- =============================================================================

-- Monitor scraping job queue
SELECT 
    status,
    job_type,
    COUNT(*) as job_count,
    AVG(attempts) as avg_attempts,
    MIN(scheduled_at) as oldest_job,
    MAX(scheduled_at) as newest_job
FROM scraping_jobs
WHERE completed_at IS NULL OR completed_at >= DATEADD(DAY, -1, GETDATE())
GROUP BY status, job_type
ORDER BY 
    CASE status 
        WHEN 'running' THEN 1 
        WHEN 'pending' THEN 2 
        WHEN 'failed' THEN 3 
        ELSE 4 
    END,
    job_count DESC;
GO

-- Check system health
SELECT 
    service_name,
    status,
    AVG(response_time_ms) as avg_response_time,
    COUNT(*) as check_count,
    MAX(checked_at) as last_check,
    COUNT(CASE WHEN status != 'healthy' THEN 1 END) as unhealthy_count
FROM health_checks
WHERE checked_at >= DATEADD(HOUR, -1, GETDATE())
GROUP BY service_name, status
ORDER BY service_name, status;
GO

-- API usage and rate limiting status
SELECT 
    api_name,
    endpoint,
    SUM(requests_count) as total_requests,
    SUM(success_count) as successful_requests,
    SUM(error_count) as error_count,
    ROUND(SUM(success_count) * 100.0 / SUM(requests_count), 2) as success_rate,
    SUM(estimated_cost) as total_estimated_cost,
    MAX(rate_limit_reset_at) as next_rate_limit_reset
FROM api_usage
WHERE hour_bucket >= DATEADD(HOUR, -24, GETDATE())
GROUP BY api_name, endpoint
ORDER BY total_requests DESC;
GO

-- =============================================================================
-- DATA QUALITY QUERIES
-- =============================================================================

-- Find duplicate restaurants (potential data quality issues)
SELECT 
    name,
    COUNT(*) as duplicate_count,
    STRING_AGG(restaurant_id, ', ') as restaurant_ids,
    STRING_AGG(address, '; ') as addresses
FROM restaurants
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
GO

-- Menu items without prices
SELECT TOP 50
    r.name as restaurant_name,
    mi.name as item_name,
    mc.source,
    mi.created_at
FROM menu_items mi
JOIN menu_categories mc ON mi.category_id = mc.category_id
JOIN restaurants r ON mc.restaurant_id = r.restaurant_id
WHERE mi.price IS NULL 
  AND mi.created_at >= DATEADD(DAY, -7, GETDATE())
ORDER BY mi.created_at DESC;
GO

-- Find items with low scrape confidence (using restaurant-level tracking)
SELECT TOP 25
    r.name as restaurant_name,
    mi.name as item_name,
    mc.source,
    mi.created_at
FROM menu_items mi
JOIN menu_categories mc ON mi.category_id = mc.category_id
JOIN restaurants r ON mc.restaurant_id = r.restaurant_id
WHERE r.scrape_status = 'partial'
ORDER BY mi.created_at DESC;
GO

-- =============================================================================
-- PERFORMANCE OPTIMIZATION QUERIES
-- =============================================================================

-- Identify slow queries
SELECT TOP 20
    normalized_query,
    COUNT(*) as query_count,
    AVG(execution_time_ms) as avg_execution_time,
    MAX(execution_time_ms) as max_execution_time,
    AVG(total_restaurants_found) as avg_results
FROM search_queries
WHERE execution_time_ms > 1000  -- Queries taking more than 1 second
  AND created_at >= DATEADD(DAY, -7, GETDATE())
GROUP BY normalized_query
ORDER BY avg_execution_time DESC;
GO

-- Find tables that might need optimization
SELECT 
    t.name as table_name,
    ROUND(((SUM(a.total_pages) * 8) / 1024.0), 2) as table_size_mb,
    SUM(p.rows) as table_rows,
    ROUND(((SUM(a.used_pages) * 8) / 1024.0), 2) as data_size_mb,
    ROUND((((SUM(a.total_pages) - SUM(a.used_pages)) * 8) / 1024.0), 2) as index_size_mb
FROM sys.tables t
INNER JOIN sys.indexes i ON t.object_id = i.object_id
INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE t.name NOT LIKE 'dt%' 
  AND t.is_ms_shipped = 0
  AND i.object_id > 255
GROUP BY t.name
ORDER BY table_size_mb DESC;
GO