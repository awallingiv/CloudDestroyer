# FoodFinder Database Documentation

## Overview
Complete SQL database schema for FoodFinder - a restaurant menu search and discovery system.

## Files Structure

### Setup Files (Run in Order)
1. **00_master_setup.sql** - Master setup script (runs all others)
2. **01_create_database.sql** - Database creation with UTF-8 support
3. **02_core_tables.sql** - Core restaurant and menu tables
4. **03_search_tables.sql** - Search optimization and caching
5. **04_integration_tables.sql** - Chain configs and external APIs
6. **05_analytics_tables.sql** - User behavior and analytics
7. **06_operational_tables.sql** - Jobs, config, and system health
8. **07_initial_data.sql** - Sample data and essential configuration
9. **08_useful_queries.sql** - Development and monitoring queries

## Quick Setup

### Option 1: Master Script (Recommended)
```bash
mysql -u root -p < 00_master_setup.sql
```

### Option 2: Individual Files
```bash
mysql -u root -p < 01_create_database.sql
mysql -u root -p < 02_core_tables.sql
mysql -u root -p < 03_search_tables.sql
mysql -u root -p < 04_integration_tables.sql
mysql -u root -p < 05_analytics_tables.sql
mysql -u root -p < 06_operational_tables.sql
mysql -u root -p < 07_initial_data.sql
```

## Core Tables

### Primary Data
- **restaurants** - Google Places restaurant data
- **menu_categories** - Menu organization (Burgers, Pizza, etc.)
- **menu_items** - Individual food items with pricing
- **menu_item_aliases** - Handle user input variations

### Search & Performance
- **search_queries** - Query caching and analytics
- **search_results** - Materialized search results
- **popular_searches** - Trending terms

### Integrations
- **chain_configs** - Major chain API settings
- **external_menu_data** - DoorDash/UberEats data

### Operations
- **scraping_jobs** - Background processing queue
- **system_config** - Feature flags and settings
- **api_usage** - Rate limiting and monitoring

## Key Features

✅ **Scalable Design** - Handles millions of restaurants and menu items  
✅ **FULLTEXT Search** - Optimized menu item searching  
✅ **Chain Intelligence** - Automatic detection and API preferences  
✅ **Fuzzy Matching** - Handles typos and variations via aliases  
✅ **Privacy-Focused** - Session-based analytics, no PII  
✅ **API Integration Ready** - DoorDash, UberEats, Yelp support  
✅ **Operational Monitoring** - Health checks and job queues  

## Sample Usage

### Add a Restaurant
```sql
INSERT INTO restaurants (restaurant_id, name, address, latitude, longitude, website) 
VALUES ('ChIJAbc123', 'Joe\'s Burger Joint', '123 Main St', 29.4241, -98.4936, 'https://joesburgers.com');
```

### Add Menu Items
```sql
INSERT INTO menu_items (restaurant_id, name, description, price, source) VALUES
('ChIJAbc123', 'Classic Burger', 'Beef patty with lettuce, tomato, onion', 12.99, 'scraped'),
('ChIJAbc123', 'Cheese Fries', 'Crispy fries topped with melted cheese', 6.99, 'scraped');
```

### Add Aliases for Fuzzy Search
```sql
INSERT INTO menu_item_aliases (item_id, alias_text, confidence) VALUES
(1, 'hamburger', 0.95),
(1, 'beef burger', 0.90),
(2, 'loaded fries', 0.85);
```

### Search for Menu Items
```sql
SELECT r.name, mi.name, mi.price 
FROM restaurants r 
JOIN menu_items mi ON r.restaurant_id = mi.restaurant_id 
WHERE MATCH(mi.name, mi.description, mi.search_tokens) AGAINST('burger' IN NATURAL LANGUAGE MODE)
ORDER BY mi.confidence_score DESC;
```

## Monitoring

### Check System Health
```sql
SELECT service_name, status, response_time_ms 
FROM health_checks 
WHERE checked_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR);
```

### Monitor Scraping Jobs
```sql
SELECT status, COUNT(*) as job_count 
FROM scraping_jobs 
GROUP BY status;
```

### Popular Searches
```sql
SELECT search_term, search_count 
FROM popular_searches 
ORDER BY search_count DESC 
LIMIT 10;
```

## Requirements
- MySQL 5.7+ or MySQL 8.0+ (recommended)
- InnoDB storage engine
- UTF-8 (utf8mb4) character set support

## Performance Notes
- All tables use InnoDB for ACID compliance and foreign keys
- FULLTEXT indexes on searchable content
- Proper indexing for location-based queries
- Partitioning recommended for analytics tables in high-volume scenarios

## Security Considerations
- No personally identifiable information (PII) stored
- Session-based tracking using hashed identifiers
- Location data rounded for privacy
- API keys should be stored in application config, not database

---

**Ready to power your restaurant discovery app! 🍔🔍**