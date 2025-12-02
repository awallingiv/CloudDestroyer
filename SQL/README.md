# CloudDestroyer Database Architecture

Two-database architecture separating scraping infrastructure from consumer application data.

---

## Architecture Overview

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│         CloudDestroyer DB           │     │           FoodFinder DB             │
│      (Scraping Infrastructure)      │     │        (Consumer App Data)          │
├─────────────────────────────────────┤     ├─────────────────────────────────────┤
│ • scraping_jobs                     │     │ • restaurants                       │
│ • scraping_results          ───────────►  │ • menu_items                        │
│ • scraping_workers                  │     │ • menu_categories                   │
│ • scraping_job_history              │     │ • chain_configs                     │
│ • scraping_templates                │     │ • search_queries                    │
│ • target_sites                      │     │ • popular_searches                  │
│ • system_config                     │     │ • user_interactions                 │
│ • health_checks                     │     │ • app_config                        │
└─────────────────────────────────────┘     └─────────────────────────────────────┘
```

---

## Quick Setup

### 1. Create CloudDestroyer Database
```bash
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -i "CloudDestroyer_Schema.sql"
```

### 2. Create FoodFinder Database
```bash
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -i "FoodFinder_Schema.sql"
```

### 3. Setup Sync Procedures
```bash
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "CloudDestroyer" -i "Sync_CloudDestroyer_to_FoodFinder.sql"
```

---

## Database Files

| File | Purpose |
|------|---------|
| `CloudDestroyer_Schema.sql` | CloudDestroyer database - scraping jobs, results, workers |
| `FoodFinder_Schema.sql` | FoodFinder database - restaurants, menus, search |
| `Sync_CloudDestroyer_to_FoodFinder.sql` | Cross-database sync procedures |
| `connection_string.txt` | Connection strings for both databases |

---

## CloudDestroyer Database

### Tables

| Table | Purpose |
|-------|---------|
| `scraping_jobs` | Job queue with priority, status, retry logic |
| `scraping_results` | Extraction results with sync tracking |
| `scraping_workers` | Worker registration and health |
| `scraping_job_history` | Execution logs |
| `scraping_templates` | Reusable job configurations |
| `target_sites` | Site-specific settings (Cloudflare, API endpoints) |
| `system_config` | CloudDestroyer settings |
| `health_checks` | Service health monitoring |

### Key Features

- **Price Extraction Tracking**: Jobs track `prices_extracted`, `items_with_prices`, `price_extraction_status`
- **Price Enrichment Queue**: `price_enrichment_needed` flag for helper thread
- **Sync Status**: Results track `sync_status` for FoodFinder synchronization

### Key Procedures

```sql
-- Create a job
DECLARE @JobId INT;
EXEC sp_CreateJob 
    @JobType = 'menu_extraction',
    @TargetUrl = 'https://example.com/menu',
    @EntityType = 'restaurant',
    @EntityId = 'rest_123',
    @JobId = @JobId OUTPUT;

-- Get next job
EXEC sp_GetNextJob @WorkerId = 'worker_1', @WorkerType = 'clouddestroyer';

-- Complete job with results
EXEC sp_CompleteJob 
    @JobId = 123,
    @Status = 'completed',
    @ItemsExtracted = 50,
    @StructuredData = '{"items": [...]}',
    @ItemsWithPrices = 45;

-- Get price enrichment job (for helper thread)
EXEC sp_GetNextPriceEnrichmentJob;
```

---

## FoodFinder Database

### Tables

| Table | Purpose |
|-------|---------|
| `restaurants` | Restaurant data with menu status |
| `menu_items` | Parsed menu items |
| `menu_categories` | Menu organization |
| `chain_configs` | Chain restaurant handling |
| `search_queries` | User search tracking |
| `popular_searches` | Trending searches |
| `user_interactions` | Analytics |

### Key Procedures

```sql
-- Import menu data from CloudDestroyer
EXEC sp_ImportMenuData 
    @RestaurantId = 'rest_123',
    @MenuData = '{"items": [...], "categories": [...]}',
    @MenuSource = 'clouddestroyer';

-- Search menu items
EXEC sp_SearchMenuItems 
    @SearchText = 'burger',
    @Latitude = 33.0198,
    @Longitude = -96.6989,
    @RadiusKm = 10;
```

---

## Sync Process

### Option 1: SQL Job (Recommended)

Schedule `sp_SyncBatchToFoodFinder` to run periodically:

```sql
-- In CloudDestroyer database
EXEC sp_SyncBatchToFoodFinder @BatchSize = 50;
```

### Option 2: Python Integration

```python
from db_config import DatabaseManager

with DatabaseManager() as db:
    # Get pending results
    pending = db.get_pending_sync_results(batch_size=50)
    
    for result in pending:
        success = db.sync_result_to_foodfinder(
            result_id=result['result_id'],
            entity_id=result['entity_id'],
            menu_data=result['structured_data']
        )
```

### Sync Status Views

```sql
-- Check sync statistics
SELECT * FROM v_sync_statistics;

-- View pending sync queue
SELECT * FROM v_results_pending_sync;

-- Full sync report
EXEC sp_GetSyncReport;
```

---

## Python Integration

Use `db_config.py` for database access:

```python
from db_config import DatabaseManager, CLOUDDESTROYER_DB, FOODFINDER_DB

# Connection strings
print(CLOUDDESTROYER_DB.connection_string)
print(FOODFINDER_DB.connection_string)

# Full workflow
with DatabaseManager() as db:
    # Create job
    job_id = db.create_job(
        job_type='menu_extraction',
        target_url='https://bubbas33.com/menu',
        entity_type='restaurant',
        entity_id='bubbas_plano'
    )
    
    # Get and process job
    job = db.get_next_job(worker_id='my_worker')
    
    # Complete with results
    db.complete_job(
        job_id=job_id,
        status='completed',
        items_extracted=102,
        structured_data=json.dumps(menu_data),
        items_with_prices=0,
        price_unavailable_reason='olo_dynamic_pricing'
    )
    
    # Sync to FoodFinder
    db.sync_result_to_foodfinder(
        result_id=result['result_id'],
        entity_id='bubbas_plano',
        menu_data=json.dumps(menu_data)
    )
```

---

## Environment Variables

```bash
# CloudDestroyer Database
CLOUDDESTROYER_DB_SERVER=localhost\SqlExpressDev01
CLOUDDESTROYER_DB_DATABASE=CloudDestroyer
CLOUDDESTROYER_DB_USER=SaltyUser
CLOUDDESTROYER_DB_PASSWORD=saltypass

# FoodFinder Database  
FOODFINDER_DB_SERVER=localhost\SqlExpressDev01
FOODFINDER_DB_DATABASE=FoodFinder
FOODFINDER_DB_USER=SaltyUser
FOODFINDER_DB_PASSWORD=saltypass
```

---

## Price Enrichment Helper Thread

For restaurants where prices weren't extracted (e.g., OLO dynamic pricing):

```sql
-- View enrichment queue
SELECT * FROM v_price_enrichment_queue ORDER BY enrichment_priority DESC;

-- Get next job for helper thread
EXEC sp_GetNextPriceEnrichmentJob @MaxAttempts = 3;

-- Mark enrichment result
EXEC sp_MarkPriceEnrichmentAttempt 
    @JobId = 123,
    @Success = 0,
    @Reason = 'requires_location_selection';
```

---

## Monitoring

### CloudDestroyer Stats
```sql
-- System overview
SELECT * FROM v_system_stats;

-- Job queue with priorities
SELECT * FROM v_job_queue ORDER BY effective_priority DESC;

-- Queue statistics
EXEC sp_GetQueueStats;
```

### FoodFinder Stats
```sql
-- Restaurant statistics
SELECT * FROM v_restaurant_stats;

-- Search view
SELECT TOP 10 * FROM v_menu_item_search WHERE item_name LIKE '%burger%';
```
