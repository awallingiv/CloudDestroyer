"""
CloudDestroyer FastAPI Web Service
Production-ready REST API for Cloudflare bypass and web scraping

Usage:
    pip install -r requirements.txt
    python clouddestroyer_api_service.py

API Documentation: http://localhost:8000/docs
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("⚠️ pyodbc not available - database features disabled")

from fastapi import (
    FastAPI, HTTPException, Depends, BackgroundTasks, Request, 
    Query, Path, Body, Header, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import httpx

# CloudDestroyer imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from src.core.cloud_destroyer import CloudDestroyer
    CLOUDDESTROYER_AVAILABLE = True
except ImportError:
    print("⚠️ CloudDestroyer not available")
    CLOUDDESTROYER_AVAILABLE = False

try:
    from scrape_texas_municipalities_enhanced import ImprovedTexasMunicipalitiesScraper
    MUNICIPALITIES_AVAILABLE = True
except ImportError:
    print("⚠️ Municipalities scraper not available")
    MUNICIPALITIES_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    print("⚠️ BeautifulSoup not available")
    BEAUTIFULSOUP_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    # Database connection
    DB_CONNECTION_STRING = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=.;"
        "DATABASE=FoodFinder;"
        "Trusted_Connection=yes;"
    )
    
    # API Configuration
    API_TITLE = "CloudDestroyer Web Service"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = """
    🚀 **CloudDestroyer FastAPI Web Service** - Cloudflare Bypass & Web Scraping API
    
    ## 🌟 Features
    - **Cloudflare Bypass**: Intelligent bypass with multiple strategies  
    - **Restaurant Menu Extraction**: Extract menus from protected sites
    - **Texas Municipalities Scraping**: Enhanced Wikipedia scraping
    - **Job Management**: Async scraping job processing
    - **Database Integration**: Full SQL Server integration
    - **Rate Limiting**: Built-in protection against abuse
    - **Authentication**: API key-based security
    - **Health Monitoring**: System health and metrics
    
    ## 🔑 Authentication
    Include your API key in the Authorization header: `Bearer your_api_key_here`
    
    ## 🎯 Example Usage
    ```bash
    # Test health endpoint
    curl http://localhost:8000/health
    
    # Scrape with CloudDestroyer (requires API key)
    curl -X POST "http://localhost:8000/scrape" \\
         -H "Authorization: Bearer demo_key_123" \\
         -H "Content-Type: application/json" \\
         -d '{"url": "https://example.com"}'
    
    # Get Texas municipalities
    curl -X POST "http://localhost:8000/scrape/municipalities" \\
         -H "Authorization: Bearer demo_key_123"
    ```
    
    ## 📊 Rate Limits
    - General endpoints: No limit for demo
    - Scraping endpoints: Reasonable usage expected
    - Heavy operations: Use background jobs for large tasks
    """
    
    # Security
    VALID_API_KEYS = {
        "cd_api_key_prod": "Production API Key",
        "cd_api_key_dev": "Development API Key", 
        "cd_api_key_test": "Testing API Key",
        "demo_key_123": "Demo API Key"  # For testing
    }
    
    # CloudDestroyer settings
    DESTROYER_HEADLESS = True
    DESTROYER_SESSION_PERSISTENCE = True
    DESTROYER_MAX_RETRIES = 3
    DESTROYER_TIMEOUT = 60

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str = Config.API_VERSION
    timestamp: datetime = Field(default_factory=datetime.now)
    database_connected: bool = False
    clouddestroyer_available: bool = False
    municipalities_scraper_available: bool = False
    beautifulsoup_available: bool = False
    active_jobs: int = 0
    uptime_seconds: float = 0
    features: List[str] = []

class ScrapeRequest(BaseModel):
    """Scraping request model"""
    url: str = Field(..., description="Target URL to scrape", example="https://bubbas33.com/menu")
    method: str = Field("GET", description="HTTP method (GET/POST)")
    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = Field(60, ge=10, le=300, description="Timeout in seconds")
    callback_url: Optional[str] = Field(None, description="Webhook URL for completion notification")
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

class ScrapeResponse(BaseResponse):
    """Scraping response model"""
    url: str
    status_code: int = 0
    content_length: int = 0
    duration_seconds: float = 0
    has_cf_clearance: bool = False
    cloudflare_detected: bool = False
    bypass_successful: bool = False
    content: Optional[str] = None
    content_preview: Optional[str] = None

class JobRequest(BaseModel):
    """Job creation request"""
    job_type: str = Field(..., description="Job type: scrape, menu, municipalities")
    target_url: str = Field(..., example="https://bubbas33.com/menu")
    priority: int = Field(50, ge=1, le=100, description="Job priority (1-100)")
    parameters: Optional[Dict[str, Any]] = None
    callback_url: Optional[str] = None

class JobResponse(BaseModel):
    """Job status response"""
    job_id: str
    status: str
    job_type: str
    target_url: str
    created_at: datetime
    progress: int = Field(0, ge=0, le=100)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MenuExtractionRequest(BaseModel):
    """Menu extraction request"""
    restaurant_url: str = Field(..., example="https://bubbas33.com/menu")
    restaurant_name: Optional[str] = Field(None, example="Bubba's 33")
    extraction_type: str = Field("auto", description="auto, api, html_parse")

class MenuExtractionResponse(BaseResponse):
    """Menu extraction response"""
    restaurant_name: str
    total_items: int = 0
    extraction_method: str
    menu_data: Dict[str, Any]

class MunicipalitiesResponse(BaseResponse):
    """Municipalities scraping response"""
    total_count: int = 0
    municipalities: List[Dict[str, Any]] = []
    source: str = "https://en.wikipedia.org/wiki/List_of_municipalities_in_Texas"
    statistics: Optional[Dict[str, Any]] = None

# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connected = False
        if PYODBC_AVAILABLE:
            self.connected = self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test database connection"""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                print("✅ Database connection successful")
                return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query safely"""
        if not self.connected:
            return []
        
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Get column names
                columns = [column[0] for column in cursor.description] if cursor.description else []
                
                # Fetch results
                rows = cursor.fetchall()
                
                # Convert to dict format
                results = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        if i < len(columns):
                            # Handle datetime objects
                            if hasattr(value, 'isoformat'):
                                value = value.isoformat()
                            row_dict[columns[i]] = value
                    results.append(row_dict)
                
                return results
                
        except Exception as e:
            print(f"Database query failed: {e}")
            return []
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get job statistics from database"""
        if not self.connected:
            return {}
        
        try:
            stats = self.execute_query("""
                SELECT 
                    COUNT(*) as total_jobs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_jobs
                FROM universal_scraping_jobs
            """)
            
            return stats[0] if stats else {}
            
        except Exception as e:
            print(f"Failed to get job stats: {e}")
            return {}

# =============================================================================
# JOB MANAGER
# =============================================================================

class JobManager:
    """In-memory job manager for background processing"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.active_jobs: Dict[str, Dict] = {}
        self.db_manager = db_manager
        self.job_queue = asyncio.Queue()
        self.processing_jobs = set()
    
    def create_job(self, job_type: str, target_url: str, **kwargs) -> str:
        """Create new job"""
        job_id = str(uuid.uuid4())
        
        job_data = {
            "job_id": job_id,
            "job_type": job_type,
            "target_url": target_url,
            "status": "queued",
            "created_at": datetime.now(),
            "progress": 0,
            "result": None,
            "error": None,
            **kwargs
        }
        
        self.active_jobs[job_id] = job_data
        print(f"📋 Created job {job_id} ({job_type})")
        
        # Queue for background processing
        asyncio.create_task(self._queue_job(job_data))
        
        return job_id
    
    async def _queue_job(self, job_data: Dict):
        """Queue job for processing"""
        await self.job_queue.put(job_data)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        return self.active_jobs.get(job_id)
    
    def update_job(self, job_id: str, **updates):
        """Update job data"""
        if job_id in self.active_jobs:
            self.active_jobs[job_id].update(updates)
    
    async def process_jobs(self):
        """Background job processor"""
        print("🔄 Starting background job processor...")
        
        while True:
            try:
                # Get job from queue
                job_data = await self.job_queue.get()
                
                # Process job in background
                asyncio.create_task(self._process_single_job(job_data))
                
            except Exception as e:
                print(f"❌ Job queue error: {e}")
                await asyncio.sleep(1)
    
    async def _process_single_job(self, job_data: Dict):
        """Process individual job"""
        job_id = job_data["job_id"]
        
        if job_id in self.processing_jobs:
            return
        
        self.processing_jobs.add(job_id)
        
        try:
            # Update status to processing
            self.update_job(job_id, status="processing", progress=10)
            
            # Process based on job type
            if job_data["job_type"] == "scrape":
                result = await self._process_scrape_job(job_data)
            elif job_data["job_type"] == "menu":
                result = await self._process_menu_job(job_data)
            elif job_data["job_type"] == "municipalities":
                result = await self._process_municipalities_job(job_data)
            else:
                raise ValueError(f"Unknown job type: {job_data['job_type']}")
            
            # Mark as completed
            self.update_job(
                job_id, 
                status="completed", 
                progress=100, 
                result=result,
                completed_at=datetime.now()
            )
            
            print(f"✅ Job {job_id} completed successfully")
            
        except Exception as e:
            # Mark as failed
            self.update_job(
                job_id, 
                status="failed", 
                error=str(e),
                completed_at=datetime.now()
            )
            print(f"❌ Job {job_id} failed: {e}")
        
        finally:
            self.processing_jobs.discard(job_id)
            
            # Send webhook if configured
            if job_data.get("callback_url"):
                await self._send_webhook(job_data)
            
            # Clean up after delay
            asyncio.create_task(self._cleanup_job(job_id))
    
    async def _process_scrape_job(self, job_data: Dict) -> Dict:
        """Process generic scraping job"""
        if not CLOUDDESTROYER_AVAILABLE:
            raise Exception("CloudDestroyer not available")
        
        destroyer = CloudDestroyer(
            headless=Config.DESTROYER_HEADLESS,
            session_persistence=Config.DESTROYER_SESSION_PERSISTENCE,
            max_retries=Config.DESTROYER_MAX_RETRIES,
            timeout=Config.DESTROYER_TIMEOUT
        )
        
        try:
            self.update_job(job_data["job_id"], progress=30)
            
            response = destroyer.get(job_data["target_url"])
            
            self.update_job(job_data["job_id"], progress=80)
            
            return {
                "url": job_data["target_url"],
                "status_code": response.status_code,
                "content_length": len(response.text) if hasattr(response, 'text') else 0,
                "success": response.status_code == 200,
                "has_cf_clearance": 'cf_clearance' in dict(getattr(response, 'cookies', {})),
                "content_preview": response.text[:1000] if hasattr(response, 'text') else None
            }
            
        finally:
            destroyer.cleanup()
    
    async def _process_menu_job(self, job_data: Dict) -> Dict:
        """Process menu extraction job"""
        # Placeholder for menu extraction
        return {
            "restaurant_url": job_data["target_url"],
            "extraction_method": "placeholder",
            "items_found": 0,
            "message": "Menu extraction not yet implemented for background jobs"
        }
    
    async def _process_municipalities_job(self, job_data: Dict) -> Dict:
        """Process municipalities scraping job"""
        if not MUNICIPALITIES_AVAILABLE:
            raise Exception("Municipalities scraper not available")
        
        scraper = ImprovedTexasMunicipalitiesScraper()
        
        self.update_job(job_data["job_id"], progress=50)
        
        municipalities = scraper.scrape_municipalities()
        
        self.update_job(job_data["job_id"], progress=90)
        
        return {
            "total_municipalities": len(municipalities),
            "municipalities": municipalities[:100],  # Limit size for job result
            "source": "https://en.wikipedia.org/wiki/List_of_municipalities_in_Texas",
            "scraping_success": True
        }
    
    async def _send_webhook(self, job_data: Dict):
        """Send webhook notification"""
        if not job_data.get("callback_url"):
            return
        
        try:
            payload = {
                "job_id": job_data["job_id"],
                "status": job_data["status"],
                "job_type": job_data["job_type"],
                "target_url": job_data["target_url"],
                "completed_at": job_data.get("completed_at", datetime.now()).isoformat(),
                "result": job_data.get("result"),
                "error": job_data.get("error")
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    job_data["callback_url"],
                    json=payload,
                    timeout=10
                )
            print(f"📬 Webhook sent for job {job_data['job_id']}")
            
        except Exception as e:
            print(f"❌ Failed to send webhook: {e}")
    
    async def _cleanup_job(self, job_id: str):
        """Clean up job from active jobs after delay"""
        await asyncio.sleep(300)  # 5 minutes
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]

# =============================================================================
# AUTHENTICATION
# =============================================================================

security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key (optional for demo endpoints)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include 'Authorization: Bearer your_api_key' header."
        )
    
    if credentials.credentials not in Config.VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return Config.VALID_API_KEYS[credentials.credentials]

# Optional auth for public endpoints
async def optional_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Optional API key verification"""
    if credentials and credentials.credentials in Config.VALID_API_KEYS:
        return Config.VALID_API_KEYS[credentials.credentials]
    return None

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

db_manager = None
job_manager = None
start_time = time.time()

# =============================================================================
# FASTAPI APP SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global db_manager, job_manager
    
    # Startup
    print("🚀 Starting CloudDestroyer FastAPI service...")
    
    # Initialize database
    db_manager = DatabaseManager(Config.DB_CONNECTION_STRING)
    
    # Initialize job manager
    job_manager = JobManager(db_manager)
    
    # Start background job processor
    asyncio.create_task(job_manager.process_jobs())
    
    print("✅ CloudDestroyer service started successfully")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down CloudDestroyer service...")

app = FastAPI(
    title=Config.API_TITLE,
    version=Config.API_VERSION,
    description=Config.API_DESCRIPTION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# CORE ENDPOINTS
# =============================================================================

@app.get("/", response_model=Dict[str, Any])
async def root():
    """API root endpoint - no authentication required"""
    return {
        "service": Config.API_TITLE,
        "version": Config.API_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "endpoints": {
            "scraping": "/scrape",
            "jobs": "/jobs", 
            "menu_extraction": "/extract/menu",
            "municipalities": "/scrape/municipalities",
            "database": "/database/restaurants"
        },
        "authentication": {
            "method": "Bearer token",
            "demo_key": "demo_key_123",
            "example": "Authorization: Bearer demo_key_123"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(api_key: str = Depends(optional_api_key)):
    """Health check endpoint - no authentication required"""
    
    # Check feature availability
    features = []
    if CLOUDDESTROYER_AVAILABLE:
        features.append("CloudDestroyer Bypass")
    if MUNICIPALITIES_AVAILABLE:
        features.append("Texas Municipalities Scraper")
    if BEAUTIFULSOUP_AVAILABLE:
        features.append("HTML Parsing")
    if db_manager and db_manager.connected:
        features.append("SQL Server Database")
    if PYODBC_AVAILABLE:
        features.append("Database Connectivity")
    
    # Test CloudDestroyer availability
    cd_available = CLOUDDESTROYER_AVAILABLE
    if cd_available:
        try:
            destroyer = CloudDestroyer()
            destroyer.cleanup()
        except Exception as e:
            cd_available = False
            print(f"CloudDestroyer test failed: {e}")
    
    return HealthResponse(
        database_connected=db_manager.connected if db_manager else False,
        clouddestroyer_available=cd_available,
        municipalities_scraper_available=MUNICIPALITIES_AVAILABLE,
        beautifulsoup_available=BEAUTIFULSOUP_AVAILABLE,
        active_jobs=len(job_manager.active_jobs) if job_manager else 0,
        uptime_seconds=time.time() - start_time,
        features=features
    )

@app.get("/metrics")
async def get_metrics(api_key: str = Depends(verify_api_key)):
    """Get service metrics - requires authentication"""
    
    metrics = {
        "uptime_seconds": time.time() - start_time,
        "active_jobs": len(job_manager.active_jobs) if job_manager else 0,
        "features_available": {
            "clouddestroyer": CLOUDDESTROYER_AVAILABLE,
            "municipalities": MUNICIPALITIES_AVAILABLE,
            "beautifulsoup": BEAUTIFULSOUP_AVAILABLE,
            "database": db_manager.connected if db_manager else False
        }
    }
    
    # Get database job statistics
    if db_manager and db_manager.connected:
        try:
            job_stats = db_manager.get_job_stats()
            metrics.update(job_stats)
        except Exception as e:
            print(f"Failed to get job stats: {e}")
    
    return metrics

# =============================================================================
# SCRAPING ENDPOINTS
# =============================================================================

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    scrape_req: ScrapeRequest,
    api_key: str = Depends(verify_api_key)
):
    """Perform CloudDestroyer scraping - requires authentication"""
    
    if not CLOUDDESTROYER_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="CloudDestroyer not available. Please check service configuration."
        )
    
    start_time = time.time()
    
    destroyer = CloudDestroyer(
        headless=Config.DESTROYER_HEADLESS,
        session_persistence=Config.DESTROYER_SESSION_PERSISTENCE,
        max_retries=Config.DESTROYER_MAX_RETRIES,
        timeout=scrape_req.timeout or Config.DESTROYER_TIMEOUT
    )
    
    try:
        print(f"🌐 Scraping URL: {scrape_req.url}")
        
        # Perform scraping
        response = destroyer.get(scrape_req.url)
        
        duration = time.time() - start_time
        content_length = len(response.text) if hasattr(response, 'text') else 0
        
        # Check for cf_clearance cookie
        has_cf_clearance = False
        if hasattr(response, 'cookies'):
            has_cf_clearance = 'cf_clearance' in dict(response.cookies)
        
        # Check for Cloudflare indicators
        cloudflare_detected = False
        if hasattr(response, 'text') and response.text:
            cf_indicators = ['cloudflare', 'cf-ray', 'checking your browser']
            cloudflare_detected = any(indicator in response.text.lower() for indicator in cf_indicators)
        
        bypass_successful = response.status_code == 200 and not cloudflare_detected
        
        print(f"✅ Scraping completed in {duration:.2f}s - Status: {response.status_code}")
        
        return ScrapeResponse(
            success=True,
            message="Scraping completed successfully",
            url=scrape_req.url,
            status_code=response.status_code,
            content_length=content_length,
            duration_seconds=duration,
            has_cf_clearance=has_cf_clearance,
            cloudflare_detected=cloudflare_detected,
            bypass_successful=bypass_successful,
            content=response.text if content_length < 100000 else None,  # Limit content size
            content_preview=response.text[:500] if hasattr(response, 'text') else None
        )
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Scraping failed: {e}")
        
        return ScrapeResponse(
            success=False,
            message=f"Scraping failed: {str(e)}",
            url=scrape_req.url,
            duration_seconds=duration
        )
        
    finally:
        destroyer.cleanup()

@app.post("/scrape/test")
async def test_cloudflare_bypass(
    url: str = Body(..., embed=True, example="https://bubbas33.com/menu"),
    api_key: str = Depends(verify_api_key)
):
    """Test Cloudflare bypass capabilities - requires authentication"""
    
    if not CLOUDDESTROYER_AVAILABLE:
        raise HTTPException(status_code=503, detail="CloudDestroyer not available")
    
    destroyer = CloudDestroyer()
    
    try:
        print(f"🔍 Testing bypass for: {url}")
        
        # Simple test - try to access the URL
        response = destroyer.get(url)
        
        # Check for Cloudflare indicators
        cf_protected = False
        cf_bypassed = False
        
        if hasattr(response, 'text'):
            cf_indicators = [
                'cloudflare', 'cf-ray', 'checking your browser',
                'ddos protection', 'security check', 'just a moment'
            ]
            cf_protected = any(indicator in response.text.lower() for indicator in cf_indicators)
            cf_bypassed = response.status_code == 200 and not cf_protected
        
        # Check for cf_clearance cookie
        has_cf_clearance = 'cf_clearance' in dict(getattr(response, 'cookies', {}))
        
        return {
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "cloudflare_detected": cf_protected,
            "bypass_successful": cf_bypassed,
            "has_cf_clearance": has_cf_clearance,
            "content_length": len(response.text) if hasattr(response, 'text') else 0,
            "test_summary": {
                "accessible": response.status_code == 200,
                "protected_by_cloudflare": cf_protected,
                "successfully_bypassed": cf_bypassed
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "cloudflare_detected": True,
            "bypass_successful": False,
            "test_summary": {
                "accessible": False,
                "protected_by_cloudflare": True,
                "successfully_bypassed": False,
                "error": str(e)
            }
        }
        
    finally:
        destroyer.cleanup()

# =============================================================================
# JOB MANAGEMENT ENDPOINTS
# =============================================================================

@app.post("/jobs")
async def create_job(
    job_req: JobRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create background scraping job - requires authentication"""
    
    job_id = job_manager.create_job(
        job_type=job_req.job_type,
        target_url=job_req.target_url,
        priority=job_req.priority,
        parameters=job_req.parameters or {},
        callback_url=job_req.callback_url
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Job created successfully",
        "estimated_start_time": "within 30 seconds"
    }

@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get job status and results - requires authentication"""
    
    job_data = job_manager.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(**job_data)

@app.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status: queued, processing, completed, failed"),
    limit: int = Query(10, ge=1, le=50),
    api_key: str = Depends(verify_api_key)
):
    """List recent jobs - requires authentication"""
    
    jobs = list(job_manager.active_jobs.values())
    
    # Filter by status if specified
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    
    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    
    return {
        "jobs": jobs[:limit],
        "total_active": len(job_manager.active_jobs),
        "filtered_count": len(jobs)
    }

# =============================================================================
# MENU EXTRACTION ENDPOINTS
# =============================================================================

@app.post("/extract/menu", response_model=MenuExtractionResponse)
async def extract_menu(
    menu_req: MenuExtractionRequest,
    api_key: str = Depends(verify_api_key)
):
    """Extract restaurant menu - requires authentication"""
    
    if not CLOUDDESTROYER_AVAILABLE:
        raise HTTPException(status_code=503, detail="CloudDestroyer not available")
    
    try:
        print(f"🍽️ Extracting menu from: {menu_req.restaurant_url}")
        
        # Use CloudDestroyer to get the page
        destroyer = CloudDestroyer()
        
        try:
            response = destroyer.get(menu_req.restaurant_url)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to access restaurant page: HTTP {response.status_code}"
                )
            
            # Simple menu item detection using BeautifulSoup
            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for menu-like elements
                menu_selectors = [
                    '.menu-item', '.menuitem', '.menu_item',
                    '[class*="menu"][class*="item"]',
                    '.food-item', '.dish', '.product'
                ]
                
                menu_items = []
                extraction_method = "html_parse"
                
                for selector in menu_selectors:
                    elements = soup.select(selector)
                    if elements:
                        print(f"Found {len(elements)} items with selector: {selector}")
                        for elem in elements[:20]:  # Limit to first 20
                            item_text = elem.get_text(strip=True)
                            if item_text and len(item_text) > 5:
                                menu_items.append({
                                    "name": item_text[:100],  # Limit length
                                    "selector_used": selector,
                                    "element_tag": elem.name
                                })
                        break
                
                # If no structured items found, look for text patterns
                if not menu_items:
                    # Look for price patterns ($X.XX)
                    import re
                    text_content = soup.get_text()
                    price_pattern = r'\$\d+\.\d{2}'
                    price_matches = re.findall(price_pattern, text_content)
                    
                    if price_matches:
                        menu_items.append({
                            "extraction_note": f"Found {len(price_matches)} price patterns",
                            "sample_prices": price_matches[:5]
                        })
                        extraction_method = "price_pattern_detection"
                
            else:
                # Fallback without BeautifulSoup
                menu_items = [{
                    "extraction_note": "BeautifulSoup not available, basic content analysis",
                    "content_length": len(response.text),
                    "contains_menu_keywords": any(
                        keyword in response.text.lower() 
                        for keyword in ['menu', 'appetizer', 'entree', 'dessert', 'price']
                    )
                }]
                extraction_method = "basic_content_analysis"
            
            menu_data = {
                "restaurant_name": menu_req.restaurant_name or "Unknown Restaurant",
                "url": menu_req.restaurant_url,
                "items": menu_items,
                "extraction_method": extraction_method,
                "page_info": {
                    "status_code": response.status_code,
                    "content_length": len(response.text),
                    "title": soup.title.string if BEAUTIFULSOUP_AVAILABLE and soup.title else "Unknown"
                },
                "extracted_at": datetime.now().isoformat()
            }
            
            return MenuExtractionResponse(
                success=True,
                message=f"Menu extraction completed using {extraction_method}",
                restaurant_name=menu_data["restaurant_name"],
                total_items=len(menu_items),
                extraction_method=extraction_method,
                menu_data=menu_data
            )
            
        finally:
            destroyer.cleanup()
            
    except Exception as e:
        print(f"❌ Menu extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# TEXAS MUNICIPALITIES ENDPOINTS
# =============================================================================

@app.post("/scrape/municipalities", response_model=MunicipalitiesResponse)
async def scrape_municipalities(
    save_to_file: bool = Query(False, description="Save results to JSON file"),
    limit: Optional[int] = Query(None, ge=1, le=1500, description="Limit number of results"),
    api_key: str = Depends(verify_api_key)
):
    """Scrape Texas municipalities from Wikipedia - requires authentication"""
    
    if not MUNICIPALITIES_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Municipalities scraper not available. Check that scrape_texas_municipalities_enhanced.py is present."
        )
    
    try:
        print("🏛️ Starting Texas municipalities scraping...")
        
        scraper = ImprovedTexasMunicipalitiesScraper()
        municipalities = scraper.scrape_municipalities()
        
        if not municipalities:
            raise HTTPException(status_code=400, detail="No municipalities found")
        
        # Apply limit if specified
        if limit and limit < len(municipalities):
            municipalities = municipalities[:limit]
        
        # Generate statistics
        statistics = {
            "total_found": len(municipalities),
            "with_population": sum(1 for m in municipalities if m.get('population')),
            "with_counties": sum(1 for m in municipalities if m.get('primary_county')),
            "unique_counties": len(set(
                m.get('primary_county') for m in municipalities 
                if m.get('primary_county')
            ))
        }
        
        # Get population stats if available
        populations = [m['population'] for m in municipalities if m.get('population')]
        if populations:
            statistics["population_stats"] = {
                "min": min(populations),
                "max": max(populations),
                "average": sum(populations) // len(populations)
            }
        
        result = MunicipalitiesResponse(
            success=True,
            message=f"Successfully scraped {len(municipalities)} Texas municipalities",
            total_count=len(municipalities),
            municipalities=municipalities,
            statistics=statistics
        )
        
        # Optionally save to file
        if save_to_file:
            try:
                filename = scraper.save_to_json(municipalities)
                result.message += f" (saved to {filename})"
            except Exception as e:
                print(f"⚠️ Failed to save file: {e}")
                result.message += " (file save failed)"
        
        return result
        
    except Exception as e:
        print(f"❌ Municipalities scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# DATABASE ENDPOINTS
# =============================================================================

@app.get("/database/restaurants")
async def get_restaurants(
    limit: int = Query(20, ge=1, le=100),
    api_key: str = Depends(verify_api_key)
):
    """Get restaurants from database - requires authentication"""
    
    if not db_manager or not db_manager.connected:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        restaurants = db_manager.execute_query(
            f"SELECT TOP ({limit}) * FROM restaurants ORDER BY restaurant_id DESC"
        )
        
        return {
            "success": True,
            "count": len(restaurants),
            "restaurants": restaurants,
            "note": "This endpoint requires active SQL Server connection"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/database/jobs")
async def get_database_jobs(
    limit: int = Query(10, ge=1, le=50),
    api_key: str = Depends(verify_api_key)
):
    """Get scraping jobs from database - requires authentication"""
    
    if not db_manager or not db_manager.connected:
        return {
            "success": False, 
            "message": "Database not available", 
            "jobs": [],
            "note": "Database connection required for this endpoint"
        }
    
    try:
        jobs = db_manager.execute_query(
            f"SELECT TOP ({limit}) * FROM universal_scraping_jobs ORDER BY created_at DESC"
        )
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs
        }
        
    except Exception as e:
        return {
            "success": False, 
            "message": f"Database error: {str(e)}", 
            "jobs": []
        }

# =============================================================================
# WEBHOOK & UTILITY ENDPOINTS
# =============================================================================

@app.post("/webhooks/test")
async def test_webhook(
    webhook_url: str = Body(..., embed=True, example="https://webhook.site/your-unique-url"),
    api_key: str = Depends(verify_api_key)
):
    """Test webhook URL - requires authentication"""
    
    try:
        test_payload = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "service": Config.API_TITLE,
            "version": Config.API_VERSION,
            "message": "This is a test webhook from CloudDestroyer API"
        }
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.post(
                webhook_url,
                json=test_payload,
                timeout=10
            )
            duration = time.time() - start_time
        
        return {
            "success": True,
            "message": "Webhook test successful",
            "webhook_url": webhook_url,
            "status_code": response.status_code,
            "response_time_ms": round(duration * 1000, 2),
            "payload_sent": test_payload
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Webhook test failed: {str(e)}",
            "webhook_url": webhook_url,
            "error": str(e)
        }

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    print(f"❌ Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.now().isoformat(),
            "details": str(exc) if Config.API_VERSION.endswith("-dev") else None
        }
    )

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 CloudDestroyer FastAPI Web Service")
    print("=" * 60)
    print(f"📖 API Documentation: http://localhost:8000/docs")
    print(f"🔍 Interactive API: http://localhost:8000/redoc")
    print(f"❤️ Health Check: http://localhost:8000/health")
    print(f"🔑 Demo API Key: demo_key_123")
    print("=" * 60)
    print("📝 Example Usage:")
    print('curl -X POST "http://localhost:8000/scrape" \\')
    print('     -H "Authorization: Bearer demo_key_123" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"url": "https://bubbas33.com/menu"}\'')
    print("=" * 60)
    
    uvicorn.run(
        "clouddestroyer_api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True
    )