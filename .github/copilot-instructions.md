# CloudDestroyer AI Agent Instructions

## System Architecture

**CloudDestroyer** is a sophisticated Cloudflare bypass engine built for restaurant menu scraping at scale. The architecture uses a **3-layer strategy escalation system**:

### Core Components
- `src/core/cloud_destroyer.py` - Main unified API
- `src/bypass/bypass_orchestrator.py` - Strategy coordination with intelligent fallbacks  
- `src/bypass/strategies/` - Individual bypass methods (cloudscraper, selenium_stealth)
- `src/stealth/fingerprint_manager.py` - Browser fingerprinting and evasion
- `api.py` - Production REST API with `RestaurantMenuScraper` class
- `clouddestroyer_api_service.py` - FastAPI service with database integration

### Key Patterns

**Strategy Escalation Flow:**
```python
# BypassOrchestrator tries strategies in order based on challenge detection
DIRECT → CLOUDSCRAPER → SELENIUM_STEALTH → FULL_ESCALATION
```

**Menu Discovery Process:**
The `find_menu_page()` method uses **15-tier intelligent scoring** returning `(url, score)` tuples:
- **Score ≥8**: Triggers early termination and direct extraction  
- **Score <8**: Continues with API endpoint discovery
- **Tiers**: Direct paths → Extended paths → Sitemap analysis → JS rendering → Fallback

**Database Integration:**
SQL Server integration via `SQL/` directory with job queue, worker management, and result storage.

## Development Workflows

**Testing Menu Extraction:**
```bash
# Quick test with specific restaurant
python test_enhanced_api_discovery.py

# Direct scraper testing  
python test_scraper_directly.py

# API service testing
python test_api_bubbas.py
```

**Debugging Extraction Issues:**
- Use `debug_*.py` scripts for step-by-step analysis
- Check `debug_html/` for saved DOM snapshots  
- Monitor logs for bypass strategy selection and scores

**API Service:**
```bash
python clouddestroyer_api_service.py  # Port 8000, docs at /docs
python api.py  # Alternative service
```

## Project-Specific Conventions

**Error Handling:** Uses `loguru` logger extensively with structured metadata. Always include challenge types and bypass strategies in logs.

**Session Management:** The `SessionManager` persists cookies/tokens across requests. Critical for maintaining Cloudflare bypasses.

**Scoring System:** Menu page discovery uses 0-15 scoring. High scores (8+) indicate confident menu page detection and skip API discovery for efficiency.

**JavaScript Extraction:** Angular/React SPAs require `_extract_menu_with_navigation()` with category-by-category processing. Look for patterns like `/menu/appetizers`, `/menu/wings`.

**Testing Approach:** Each major component has dedicated test files. Prefix test functions with `test_` and include restaurant URLs for validation.

## Critical Integration Points

**Bypass Strategy Selection:** Challenge detection in `ChallengeDetector` determines optimal strategy order. Always check challenge type before selecting approach.

**Menu Item Structure:** Results follow this format:
```python
{
    "items": [{"name": str, "price": str, "description": str, "category": str}],
    "categories": [str],
    "confidence": float,
    "extraction_method": str
}
```

**Database Schema:** SQL files must run in numeric order (00_master_setup.sql first). Core tables: `restaurants`, `menu_items`, `menu_categories`.

When modifying extraction logic, always test with `https://bubbas33.com` as the reference implementation uses Angular navigation patterns typical of modern restaurant sites.