"""
Database Configuration for CloudDestroyer

Two-database architecture:
- CloudDestroyer: Scraping jobs, results, workers (this app's main DB)
- FoodFinder: Restaurant/menu data (consumer app DB for sync)
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 17 for SQL Server"
    trust_cert: bool = True
    
    @property
    def connection_string(self) -> str:
        """Generate pyodbc connection string"""
        trust = "yes" if self.trust_cert else "no"
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"TrustServerCertificate={trust};"
        )
    
    @property
    def sqlalchemy_url(self) -> str:
        """Generate SQLAlchemy connection URL"""
        # URL encode the server name (backslash)
        server = self.server.replace("\\", "%5C")
        return (
            f"mssql+pyodbc://{self.username}:{self.password}@"
            f"{server}/{self.database}?driver={self.driver.replace(' ', '+')}"
        )


# Default configuration - override with environment variables
CLOUDDESTROYER_DB = DatabaseConfig(
    server=os.environ.get("CLOUDDESTROYER_DB_SERVER", r"localhost\SqlExpressDev01"),
    database=os.environ.get("CLOUDDESTROYER_DB_DATABASE", "CloudDestroyer"),
    username=os.environ.get("CLOUDDESTROYER_DB_USER", "SaltyUser"),
    password=os.environ.get("CLOUDDESTROYER_DB_PASSWORD", "saltypass"),
)

FOODFINDER_DB = DatabaseConfig(
    server=os.environ.get("FOODFINDER_DB_SERVER", r"localhost\SqlExpressDev01"),
    database=os.environ.get("FOODFINDER_DB_DATABASE", "FoodFinder"),
    username=os.environ.get("FOODFINDER_DB_USER", "SaltyUser"),
    password=os.environ.get("FOODFINDER_DB_PASSWORD", "saltypass"),
)


def get_clouddestroyer_connection():
    """Get connection to CloudDestroyer database"""
    import pyodbc
    return pyodbc.connect(CLOUDDESTROYER_DB.connection_string)


def get_foodfinder_connection():
    """Get connection to FoodFinder database"""
    import pyodbc
    return pyodbc.connect(FOODFINDER_DB.connection_string)


class DatabaseManager:
    """
    Manages database connections for CloudDestroyer operations.
    
    Usage:
        with DatabaseManager() as db:
            # Create a job
            job_id = db.create_job(
                job_type='menu_extraction',
                target_url='https://example.com/menu',
                entity_type='restaurant',
                entity_id='abc123'
            )
            
            # Get next job
            job = db.get_next_job(worker_id='worker_1')
            
            # Complete job with results
            db.complete_job(
                job_id=job_id,
                status='completed',
                items_extracted=50,
                structured_data=json.dumps(menu_data)
            )
    """
    
    def __init__(self):
        self._clouddestroyer_conn = None
        self._foodfinder_conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @property
    def clouddestroyer(self):
        """Lazy connection to CloudDestroyer database"""
        if self._clouddestroyer_conn is None:
            self._clouddestroyer_conn = get_clouddestroyer_connection()
        return self._clouddestroyer_conn
    
    @property
    def foodfinder(self):
        """Lazy connection to FoodFinder database"""
        if self._foodfinder_conn is None:
            self._foodfinder_conn = get_foodfinder_connection()
        return self._foodfinder_conn
    
    def close(self):
        """Close all connections"""
        if self._clouddestroyer_conn:
            self._clouddestroyer_conn.close()
            self._clouddestroyer_conn = None
        if self._foodfinder_conn:
            self._foodfinder_conn.close()
            self._foodfinder_conn = None
    
    # =========================================================================
    # CloudDestroyer Operations
    # =========================================================================
    
    def create_job(
        self,
        job_type: str,
        target_url: str,
        job_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        priority: int = 50,
        scraping_config: Optional[str] = None,
        batch_id: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> int:
        """Create a new scraping job"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            DECLARE @JobId INT;
            EXEC sp_CreateJob 
                @JobType = ?,
                @TargetUrl = ?,
                @JobName = ?,
                @EntityType = ?,
                @EntityId = ?,
                @Priority = ?,
                @ScrapingConfig = ?,
                @BatchId = ?,
                @CallbackUrl = ?,
                @JobId = @JobId OUTPUT;
            SELECT @JobId;
        """, job_type, target_url, job_name, entity_type, entity_id, 
             priority, scraping_config, batch_id, callback_url)
        
        job_id = cursor.fetchone()[0]
        self.clouddestroyer.commit()
        return job_id
    
    def get_next_job(self, worker_id: str, worker_type: str = 'clouddestroyer', 
                     supported_job_types: Optional[str] = None) -> Optional[dict]:
        """Get next available job from queue"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_GetNextJob 
                @WorkerId = ?,
                @WorkerType = ?,
                @SupportedJobTypes = ?
        """, worker_id, worker_type, supported_job_types)
        
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def complete_job(
        self,
        job_id: int,
        status: str,
        items_extracted: int = 0,
        processing_time_seconds: float = 0,
        error_message: Optional[str] = None,
        raw_data: Optional[str] = None,
        structured_data: Optional[str] = None,
        confidence_score: float = 1.0,
        extraction_method: Optional[str] = None,
        items_with_prices: int = 0,
        price_source: Optional[str] = None,
        price_unavailable_reason: Optional[str] = None
    ) -> dict:
        """Complete a job and store results"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_CompleteJob 
                @JobId = ?,
                @Status = ?,
                @ItemsExtracted = ?,
                @ProcessingTimeSeconds = ?,
                @ErrorMessage = ?,
                @RawData = ?,
                @StructuredData = ?,
                @ConfidenceScore = ?,
                @ExtractionMethod = ?,
                @ItemsWithPrices = ?,
                @PriceSource = ?,
                @PriceUnavailableReason = ?
        """, job_id, status, items_extracted, processing_time_seconds,
             error_message, raw_data, structured_data, confidence_score,
             extraction_method, items_with_prices, price_source, price_unavailable_reason)
        
        row = cursor.fetchone()
        self.clouddestroyer.commit()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return {}
    
    def get_price_enrichment_job(self, max_attempts: int = 3) -> Optional[dict]:
        """Get next job needing price enrichment"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_GetNextPriceEnrichmentJob @MaxAttempts = ?
        """, max_attempts)
        
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def mark_price_enrichment(self, job_id: int, success: bool, 
                              items_enriched: int = 0, reason: Optional[str] = None):
        """Mark price enrichment attempt result"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_MarkPriceEnrichmentAttempt 
                @JobId = ?, @Success = ?, @ItemsEnriched = ?, @Reason = ?
        """, job_id, success, items_enriched, reason)
        self.clouddestroyer.commit()
    
    def get_queue_stats(self) -> list:
        """Get queue statistics"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("EXEC sp_GetQueueStats")
        
        results = []
        while True:
            rows = cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in cursor.description]
                results.append([dict(zip(columns, row)) for row in rows])
            if not cursor.nextset():
                break
        return results
    
    # =========================================================================
    # Sync Operations (CloudDestroyer -> FoodFinder)
    # =========================================================================
    
    def get_pending_sync_results(self, batch_size: int = 100) -> list:
        """Get results pending sync to FoodFinder"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_GetPendingSyncResults @BatchSize = ?
        """, batch_size)
        
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []
    
    def sync_result_to_foodfinder(self, result_id: int, entity_id: str, 
                                   menu_data: str) -> bool:
        """Sync a result to FoodFinder database"""
        try:
            # Import to FoodFinder
            cursor = self.foodfinder.cursor()
            cursor.execute("""
                EXEC sp_ImportMenuData @RestaurantId = ?, @MenuData = ?, @MenuSource = 'clouddestroyer'
            """, entity_id, menu_data)
            self.foodfinder.commit()
            
            # Mark as synced in CloudDestroyer
            cursor = self.clouddestroyer.cursor()
            cursor.execute("""
                EXEC sp_MarkResultSynced @ResultId = ?, @Success = 1
            """, result_id)
            self.clouddestroyer.commit()
            
            return True
            
        except Exception as e:
            # Mark sync as failed
            cursor = self.clouddestroyer.cursor()
            cursor.execute("""
                EXEC sp_MarkResultSynced @ResultId = ?, @Success = 0, @ErrorMessage = ?
            """, result_id, str(e))
            self.clouddestroyer.commit()
            return False
    
    # =========================================================================
    # API Endpoint Management Operations
    # =========================================================================

    def save_api_endpoint(
        self,
        domain: str,
        api_menu_endpoint: str,
        api_endpoint_type: str = 'unknown',
        requires_location: bool = False,
        authentication_method: str = 'none',
        site_type: Optional[str] = None
    ) -> dict:
        """Save discovered API endpoint to database"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_SaveApiEndpoint
                @Domain = ?,
                @ApiMenuEndpoint = ?,
                @ApiEndpointType = ?,
                @RequiresLocation = ?,
                @AuthenticationMethod = ?,
                @SiteType = ?
        """, domain, api_menu_endpoint, api_endpoint_type, requires_location,
             authentication_method, site_type)

        row = cursor.fetchone()
        self.clouddestroyer.commit()

        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return {}

    def verify_api_endpoint(self, domain: str) -> int:
        """Mark API endpoint as working"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_VerifyApiEndpoint @Domain = ?
        """, domain)

        row = cursor.fetchone()
        self.clouddestroyer.commit()

        return row[0] if row else 0

    def mark_api_endpoint_failed(self, domain: str, failure_reason: Optional[str] = None) -> int:
        """Mark API endpoint as failed"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_MarkApiEndpointFailed @Domain = ?, @FailureReason = ?
        """, domain, failure_reason)

        row = cursor.fetchone()
        self.clouddestroyer.commit()

        return row[0] if row else 0

    def get_api_endpoint(self, domain: str) -> Optional[dict]:
        """Get API endpoint information for domain"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_GetApiEndpoint @Domain = ?
        """, domain)

        row = cursor.fetchone()

        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def get_working_api_endpoints(self, min_verifications: int = 1) -> list:
        """Get all working API endpoints"""
        cursor = self.clouddestroyer.cursor()
        cursor.execute("""
            EXEC sp_GetWorkingApiEndpoints @MinVerifications = ?
        """, min_verifications)

        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []

    # =========================================================================
    # FoodFinder Operations
    # =========================================================================
    
    def upsert_restaurant(
        self,
        restaurant_id: str,
        name: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        google_rating: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> dict:
        """Insert or update restaurant in FoodFinder"""
        cursor = self.foodfinder.cursor()
        cursor.execute("""
            EXEC sp_UpsertRestaurant 
                @RestaurantId = ?, @Name = ?, @Address = ?, @City = ?, @State = ?,
                @Phone = ?, @Website = ?, @GoogleRating = ?, @Latitude = ?, @Longitude = ?
        """, restaurant_id, name, address, city, state, phone, website, 
             google_rating, latitude, longitude)
        
        row = cursor.fetchone()
        self.foodfinder.commit()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return {}
    
    def search_menu_items(self, search_text: str, latitude: Optional[float] = None,
                          longitude: Optional[float] = None, radius_km: float = 10.0,
                          max_results: int = 50) -> list:
        """Search menu items in FoodFinder"""
        cursor = self.foodfinder.cursor()
        cursor.execute("""
            EXEC sp_SearchMenuItems 
                @SearchText = ?, @Latitude = ?, @Longitude = ?, 
                @RadiusKm = ?, @MaxResults = ?
        """, search_text, latitude, longitude, radius_km, max_results)
        
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []


# Convenience function for quick database access
def get_db() -> DatabaseManager:
    """Get a new DatabaseManager instance"""
    return DatabaseManager()


if __name__ == "__main__":
    # Test connections
    print("Testing database connections...")
    
    print(f"\nCloudDestroyer connection string:")
    print(f"  {CLOUDDESTROYER_DB.connection_string}")
    
    print(f"\nFoodFinder connection string:")
    print(f"  {FOODFINDER_DB.connection_string}")
    
    try:
        with DatabaseManager() as db:
            # Test CloudDestroyer connection
            cursor = db.clouddestroyer.cursor()
            cursor.execute("SELECT DB_NAME() as db_name")
            result = cursor.fetchone()
            print(f"\n✓ CloudDestroyer connection successful: {result[0]}")
    except Exception as e:
        print(f"\n✗ CloudDestroyer connection failed: {e}")
    
    try:
        with DatabaseManager() as db:
            # Test FoodFinder connection
            cursor = db.foodfinder.cursor()
            cursor.execute("SELECT DB_NAME() as db_name")
            result = cursor.fetchone()
            print(f"✓ FoodFinder connection successful: {result[0]}")
    except Exception as e:
        print(f"✗ FoodFinder connection failed: {e}")


