# CloudDestroyer Database Integration

> Universal scraping queue system for SQL Server — powering automated extraction at scale.

---

## What This Provides

A production-ready database layer that transforms CloudDestroyer from a standalone scraper into a managed extraction pipeline:

- **Job Queue Management** — Priority scheduling, retry logic, and batch processing
- **Worker Coordination** — Distributed scraping with health monitoring
- **Result Tracking** — Structured storage with confidence scoring and validation
- **Performance Analytics** — Real-time metrics, alerts, and optimization insights

---

## Quick Setup

### Prerequisites

- SQL Server (Express or higher)
- Existing `FoodFinder` database (or modify scripts for your database)
- `sqlcmd` utility or SQL Server Management Studio

### Installation

**Option A: Master Setup (Recommended)**

```bash
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "16_clouddestroyer_master_setup.sql"
```

**Option B: Sequential Installation**

```bash
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "12_universal_scraping_queue.sql"
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "13_universal_scraping_procedures.sql"
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "14_clouddestroyer_extensions.sql"
sqlcmd -S "localhost\SqlExpressDev01" -U "SaltyUser" -P "saltypass" -d "FoodFinder" -i "15_clouddestroyer_initial_data.sql"
```

---

## Schema Overview

### New Tables

| Table | Purpose |
|-------|---------|
| `universal_scraping_jobs` | Central job queue with priority, retry, and worker assignment |
| `universal_scraping_results` | Raw and structured extraction data with quality metrics |
| `scraping_job_templates` | Reusable configurations for common scraping patterns |
| `scraping_workers` | Worker registration, capabilities, and health tracking |
| `scraping_job_history` | Execution logs for performance analysis |

### Restaurant Table Extensions

The existing `restaurants` table gains automation metadata:

```sql
-- Processing status
clouddestroyer_status        VARCHAR(20)   DEFAULT 'not_processed'
clouddestroyer_last_attempt  DATETIME2     NULL
clouddestroyer_attempts      INT           DEFAULT 0

-- Website analysis
website_type                 VARCHAR(30)   NULL  -- 'react_spa', 'angular_spa', etc.
requires_selenium            BIT           DEFAULT 0
api_endpoints_discovered     NVARCHAR(MAX) NULL  -- JSON array

-- Performance metrics
extraction_success_rate      DECIMAL(3,2)  DEFAULT 0
average_extraction_time      DECIMAL(8,2)  DEFAULT 0
best_extraction_method       VARCHAR(50)   NULL
```

---

## Usage

### Creating Restaurant Extraction Jobs

```sql
DECLARE @JobId INT;

EXEC spcd_CreateRestaurantJob 
    @RestaurantId = 'ChIJAbc123',
    @TargetUrl = 'https://restaurant.com/menu',  -- Optional URL override
    @Priority = 80,                               -- Higher = processed sooner
    @SessionId = 'batch_2024_001',               -- For batch tracking
    @JobId = @JobId OUTPUT;

SELECT @JobId AS CreatedJobId;
```

### Processing Extraction Results

```sql
EXEC spcd_ProcessMenuResult
    @JobId = 123,
    @MenuData = '{
        "categories": [
            {
                "name": "Appetizers",
                "items": [
                    {
                        "name": "Buffalo Wings",
                        "description": "Crispy wings with house sauce",
                        "base_price": 12.99
                    }
                ]
            }
        ]
    }';
```

### Generic Scraping Jobs

The queue supports any scraping task, not just restaurant menus:

```sql
DECLARE @JobId INT;

EXEC spsc_CreateJob
    @JobType = 'price_tracker',
    @TargetUrl = 'https://competitor.com/pricing',
    @JobName = 'Daily Competitor Price Check',
    @EntityType = 'competitor',
    @EntityId = 'comp_acme_001',
    @Priority = 50,
    @ScrapingConfig = '{"frequency": "daily", "notify_on_change": true}',
    @JobId = @JobId OUTPUT;
```

### Worker Job Acquisition

```sql
EXEC spsc_GetNextJob 
    @WorkerId = 'clouddestroyer_worker_1',
    @WorkerType = 'clouddestroyer',
    @SupportedJobTypes = 'clouddestroyer_menu,api_endpoint';
```

### Job Completion

```sql
EXEC spsc_CompleteJob
    @JobId = 123,
    @Status = 'completed',
    @ItemsExtracted = 25,
    @ProcessingTimeSeconds = 45.5,
    @StructuredData = '{"items": [...]}',
    @ConfidenceScore = 0.95;
```

---

## Monitoring

### Built-in Views

| View | Description |
|------|-------------|
| `v_clouddestroyer_monitoring` | System-wide health dashboard |
| `v_clouddestroyer_queue` | Current queue with effective priorities |
| `v_clouddestroyer_analytics` | Historical performance metrics |
| `v_scraping_alerts` | Active warnings and errors |

### Example Queries

```sql
-- System status overview
SELECT * FROM v_clouddestroyer_monitoring;

-- Top 20 pending jobs by priority
SELECT TOP 20 * 
FROM v_clouddestroyer_queue 
ORDER BY effective_priority DESC;

-- Last 7 days of extraction analytics
SELECT * 
FROM v_clouddestroyer_analytics
WHERE extraction_date >= DATEADD(DAY, -7, GETDATE());

-- Current alerts
SELECT * FROM v_scraping_alerts;

-- Queue statistics
EXEC spsc_GetQueueStats;
```

---

## Job Templates

Pre-configured templates for common scenarios:

| Template | Key Features |
|----------|--------------|
| `clouddestroyer_menu` | Cloudflare bypass, API discovery, Selenium SPA support |
| `api_endpoint` | REST extraction with auth and rate limiting |
| `content_monitor` | Change detection and availability tracking |
| `price_tracker` | E-commerce monitoring with historical data |

---

## System Configuration

Default settings (stored in `system_config` table):

| Setting | Default |
|---------|---------|
| Max Concurrent Jobs | 5 |
| Request Timeout | 180 seconds |
| Rate Limit Delay | 2–8 seconds (random) |
| Session Persistence | Enabled |
| Headless Mode | Enabled |

### Registered Workers

| Worker | Type | Concurrent Jobs |
|--------|------|-----------------|
| CloudDestroyer Primary | `clouddestroyer` | 3 |
| API Client | `api_client` | 10 |
| Content Monitor | `monitor` | 5 |

---

## Alerts

Automated monitoring triggers for:

- **Queue Backlog** — More than 50 pending jobs
- **Stuck Jobs** — Running longer than 30 minutes
- **Worker Health** — No heartbeat for 10+ minutes
- **Success Rate** — Below threshold performance
- **Degradation** — Increasing error rates or latency

---

## Python Integration

```python
import pyodbc
import json

def get_next_job(worker_id: str) -> dict | None:
    """Fetch the next available job for this worker."""
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    cursor.execute("""
        EXEC spsc_GetNextJob 
            @WorkerId = ?,
            @WorkerType = 'clouddestroyer',
            @SupportedJobTypes = 'clouddestroyer_menu'
    """, worker_id)
    
    row = cursor.fetchone()
    return dict(row) if row else None


def complete_job(job_id: int, menu_data: dict, processing_time: float):
    """Mark job complete and store results."""
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    cursor.execute("""
        EXEC spsc_CompleteJob
            @JobId = ?,
            @Status = 'completed',
            @ItemsExtracted = ?,
            @ProcessingTimeSeconds = ?,
            @StructuredData = ?,
            @ConfidenceScore = 0.95
    """, job_id, len(menu_data.get('items', [])), processing_time, json.dumps(menu_data))
    
    conn.commit()


# Main processing loop
def run_worker(worker_id: str):
    from src.core.cloud_destroyer import CloudDestroyer
    
    scraper = CloudDestroyer()
    
    while True:
        job = get_next_job(worker_id)
        if not job:
            time.sleep(10)
            continue
        
        start = time.time()
        response = scraper.get(job['target_url'])
        menu_data = extract_menu(response)
        
        complete_job(job['job_id'], menu_data, time.time() - start)
```

---

## Compatibility

- Preserves all existing `restaurants`, `menu_items`, and `menu_categories` data
- Existing search procedures (`sp_SimpleSearch`, etc.) remain unchanged
- Replaces legacy `scraping_jobs` table with enhanced `universal_scraping_jobs`
- Full backward compatibility with existing application code

---

## Validated Performance

Benchmark from Bubba's 33 extraction:

| Metric | Result |
|--------|--------|
| Menu Items | 102 |
| Categories | 13 |
| API Endpoint | `/api/olo/restaurants/236820/menu` |
| Cloudflare | Bypassed |
| SPA Type | Angular |

This integration scales that extraction pattern across hundreds of targets with automated scheduling, monitoring, and result management.

---

## File Reference

| File | Purpose |
|------|---------|
| `12_universal_scraping_queue.sql` | Core queue and result tables |
| `13_universal_scraping_procedures.sql` | Job management stored procedures |
| `14_clouddestroyer_extensions.sql` | Restaurant table enhancements |
| `15_clouddestroyer_initial_data.sql` | Templates, workers, and config |
| `16_clouddestroyer_master_setup.sql` | Combined setup with verification |
