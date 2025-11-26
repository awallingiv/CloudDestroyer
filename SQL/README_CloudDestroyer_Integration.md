# CloudDestroyer Database Integration

## Overview

This integration extends your existing FoodFinder database with a comprehensive, universal scraping queue system that supports CloudDestroyer restaurant menu extraction AND any other scraping tasks you might need in the future.

## 🎯 **Key Benefits**

✅ **Universal Scraping Queue** - Handles CloudDestroyer AND any future scraping needs  
✅ **Proven Restaurant Extraction** - Built on successful Bubba's 33 extraction (102 menu items)  
✅ **Cloudflare Bypass Integration** - Database tracking for bypass success rates  
✅ **API Endpoint Discovery** - Caches successful patterns like `/api/olo/restaurants/`  
✅ **Intelligent Priority System** - Higher priority for high-rated restaurants  
✅ **Comprehensive Monitoring** - Performance tracking, success rates, error analysis  
✅ **Worker Management** - Support for multiple scraper types and distributed processing  

## 📁 **Files Created**

### Core Database Files
- **`12_universal_scraping_queue.sql`** - Universal job queue tables supporting any scraping task
- **`13_universal_scraping_procedures.sql`** - Job management procedures with `spsc_` and `spcd_` prefixes  
- **`14_clouddestroyer_extensions.sql`** - Extends existing restaurant table with automation metadata
- **`15_clouddestroyer_initial_data.sql`** - Job templates, worker configs, and system settings
- **`16_clouddestroyer_master_setup.sql`** - Complete setup script with verification

## 🚀 **Quick Setup**

### Option 1: Master Setup (Recommended)
```bash
# Run from your SQL directory
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "16_clouddestroyer_master_setup.sql"
```

### Option 2: Individual Files
```bash
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "12_universal_scraping_queue.sql"
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "13_universal_scraping_procedures.sql"
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "14_clouddestroyer_extensions.sql"
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "15_clouddestroyer_initial_data.sql"
```

## 📊 **Database Schema Overview**

### New Tables Added

#### **`universal_scraping_jobs`** - Main job queue
- Supports **any scraping task** (CloudDestroyer, APIs, monitoring, etc.)
- Flexible entity linking (restaurants, products, articles, etc.)
- Priority queue with retry logic
- Worker assignment and tracking
- JSON configuration storage

#### **`universal_scraping_results`** - Flexible result storage  
- Stores raw + structured data from any scraper
- Quality and confidence scoring
- Performance metrics tracking
- Validation workflow support

#### **`scraping_job_templates`** - Reusable configurations
- Pre-configured templates for common tasks
- CloudDestroyer restaurant extraction template
- API endpoint templates
- Content monitoring templates

#### **`scraping_workers`** - Worker management
- Register different scraper types
- Capability tracking and load balancing
- Health monitoring and heartbeat

#### **`scraping_job_history`** - Execution tracking
- Performance analytics per worker
- Error pattern analysis
- Resource usage monitoring

### Extended Existing Tables

#### **`restaurants`** table extensions:
```sql
-- CloudDestroyer automation metadata
clouddestroyer_status VARCHAR(20) DEFAULT 'not_processed'
clouddestroyer_last_attempt DATETIME2 NULL
clouddestroyer_attempts INT DEFAULT 0

-- Website analysis results  
website_type VARCHAR(30) NULL -- 'react_spa', 'angular_spa', etc.
requires_selenium BIT DEFAULT 0
api_endpoints_discovered NVARCHAR(MAX) -- JSON array

-- Success metrics
extraction_success_rate DECIMAL(3,2) DEFAULT 0
average_extraction_time DECIMAL(8,2) DEFAULT 0
best_extraction_method VARCHAR(50) NULL
```

## 🔧 **Usage Examples**

### CloudDestroyer Restaurant Extraction

#### Create a restaurant extraction job:
```sql
DECLARE @JobId INT;

EXEC spcd_CreateRestaurantJob 
    @RestaurantId = 'ChIJAbc123', -- Your restaurant ID
    @TargetUrl = 'https://restaurant.com/menu', -- Optional override
    @Priority = 80, -- High priority
    @SessionId = 'batch_001', -- Optional batch tracking
    @JobId = @JobId OUTPUT;

SELECT @JobId as created_job_id;
```

#### Process extraction results (handles Bubba's 33 JSON format):
```sql
EXEC spcd_ProcessMenuResult
    @JobId = 123,
    @MenuData = '{
        "categories": [
            {
                "name": "Appetizers", 
                "items": [
                    {"name": "Wings", "description": "Buffalo wings", "base_price": 12.99}
                ]
            }
        ]
    }';
```

### Generic Scraping Jobs

#### Create any type of scraping job:
```sql
DECLARE @JobId INT;

EXEC spsc_CreateJob
    @JobType = 'price_tracker', -- Custom job type
    @TargetUrl = 'https://competitor.com/prices',
    @JobName = 'Daily Price Check',
    @EntityType = 'competitor', -- Any entity type
    @EntityId = 'comp_001', -- Any ID
    @Priority = 50,
    @ScrapingConfig = '{"frequency": "daily", "notify_changes": true}',
    @JobId = @JobId OUTPUT;
```

#### Get next job for worker:
```sql
EXEC spsc_GetNextJob 
    @WorkerId = 'clouddestroyer_worker_1',
    @WorkerType = 'clouddestroyer',
    @SupportedJobTypes = 'clouddestroyer_menu,api_endpoint';
```

#### Complete job with results:
```sql
EXEC spsc_CompleteJob
    @JobId = 123,
    @Status = 'completed',
    @ItemsExtracted = 25,
    @ProcessingTimeSeconds = 45.5,
    @StructuredData = '{"items": [...], "categories": [...]}',
    @ConfidenceScore = 0.95;
```

## 📈 **Monitoring and Analytics**

### Real-time monitoring:
```sql
-- Overall system status
SELECT * FROM v_clouddestroyer_monitoring;

-- Current queue with priorities
SELECT TOP 20 * FROM v_clouddestroyer_queue 
ORDER BY effective_priority DESC;

-- Performance analytics  
SELECT * FROM v_clouddestroyer_analytics
WHERE extraction_date >= DATEADD(DAY, -7, GETDATE());

-- System alerts
SELECT * FROM v_scraping_alerts;
```

### Queue statistics:
```sql
EXEC spsc_GetQueueStats;
```

## 🎯 **Job Templates Available**

### 1. **CloudDestroyer Restaurant Menu** (`clouddestroyer_menu`)
- Cloudflare bypass enabled
- API endpoint discovery 
- Selenium SPA support
- Based on successful Bubba's 33 extraction

### 2. **Generic API Endpoint** (`api_endpoint`)  
- REST API data extraction
- Authentication support
- Rate limiting compliance

### 3. **Website Content Monitor** (`content_monitor`)
- Change detection
- Price monitoring  
- Availability tracking

### 4. **Price Tracker** (`price_tracker`)
- E-commerce price monitoring
- Historical tracking
- Alert notifications

## 🔄 **Integration with Existing System**

### Preserves Your Current Data
- All existing `restaurants`, `menu_items`, `menu_categories` unchanged
- CloudDestroyer results integrate seamlessly via `spcd_ProcessMenuResult`
- Maintains data quality with confidence scoring

### Extends Your Current Workflows
- Existing search procedures (`sp_SimpleSearch`, etc.) work unchanged  
- New automation data enhances restaurant profiles
- Monitoring views provide operational insights

### Backward Compatible
- Original `scraping_jobs` table replaced with more powerful `universal_scraping_jobs`
- All existing job processing logic can be migrated to new procedures
- Enhanced retry logic and error handling

## 🛠️ **CloudDestroyer Python Integration**

### Update your CloudDestroyer automation to use the database:

```python
# Get next job from database
job = get_next_clouddestroyer_job("worker_001")

if job:
    # Use existing CloudDestroyer system
    destroyer = CloudDestroyer()
    response = destroyer.get(job['target_url'])
    
    # Process with Selenium if needed  
    menu_data = extract_menu_data(response, job['scraping_config'])
    
    # Store results in database
    store_extraction_results(job['job_id'], menu_data)
```

## 📋 **Pre-configured Settings**

### System Configuration (in `system_config` table):
- **CloudDestroyer enabled**: `true`
- **Max concurrent jobs**: `5`  
- **Default timeout**: `180 seconds`
- **Rate limiting**: `2-8 second delays`
- **Session persistence**: `enabled`
- **Headless browser**: `enabled`

### Worker Registration:
- **CloudDestroyer Primary**: Handles 3 concurrent restaurant jobs
- **API Client**: Handles 10 concurrent API jobs
- **Content Monitor**: Handles monitoring tasks

## 🚨 **Monitoring Alerts**

The system includes automated alerts for:
- High queue size (>50 pending jobs)
- Stuck jobs (running >30 minutes)  
- Dead workers (no heartbeat >10 minutes)
- Low success rates
- Performance degradation

## 🎉 **Success Metrics**

Based on your proven Bubba's 33 extraction:
- **✅ 102 menu items extracted successfully**
- **✅ 13 categories identified**  
- **✅ API endpoint discovered**: `/api/olo/restaurants/236820/menu`
- **✅ Cloudflare bypass successful**
- **✅ Angular SPA parsing working**

This database integration scales that success to handle **hundreds of restaurants automatically** while supporting **any other scraping needs** your application might have.

---

**Ready to power your automated restaurant data extraction at scale! 🍔🤖**