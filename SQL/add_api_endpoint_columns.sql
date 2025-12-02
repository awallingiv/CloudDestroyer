-- Add API endpoint tracking columns to target_sites table
USE CloudDestroyer;
GO

-- Check and add columns if they don't exist
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_menu_endpoint')
BEGIN
    ALTER TABLE target_sites ADD api_menu_endpoint VARCHAR(1000) NULL;
    PRINT '+ Added column: api_menu_endpoint';
END
ELSE
    PRINT '- Column already exists: api_menu_endpoint';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_endpoint_type')
BEGIN
    ALTER TABLE target_sites ADD api_endpoint_type VARCHAR(50) NULL;
    PRINT '+ Added column: api_endpoint_type';
END
ELSE
    PRINT '- Column already exists: api_endpoint_type';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_requires_location')
BEGIN
    ALTER TABLE target_sites ADD api_requires_location BIT DEFAULT 0;
    PRINT '+ Added column: api_requires_location';
END
ELSE
    PRINT '- Column already exists: api_requires_location';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_authentication_method')
BEGIN
    ALTER TABLE target_sites ADD api_authentication_method VARCHAR(100) NULL;
    PRINT '+ Added column: api_authentication_method';
END
ELSE
    PRINT '- Column already exists: api_authentication_method';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_endpoint_working')
BEGIN
    ALTER TABLE target_sites ADD api_endpoint_working BIT DEFAULT NULL;
    PRINT '+ Added column: api_endpoint_working';
END
ELSE
    PRINT '- Column already exists: api_endpoint_working';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_last_verified')
BEGIN
    ALTER TABLE target_sites ADD api_last_verified DATETIME2 NULL;
    PRINT '+ Added column: api_last_verified';
END
ELSE
    PRINT '- Column already exists: api_last_verified';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_last_failed')
BEGIN
    ALTER TABLE target_sites ADD api_last_failed DATETIME2 NULL;
    PRINT '+ Added column: api_last_failed';
END
ELSE
    PRINT '- Column already exists: api_last_failed';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_failure_reason')
BEGIN
    ALTER TABLE target_sites ADD api_failure_reason VARCHAR(255) NULL;
    PRINT '+ Added column: api_failure_reason';
END
ELSE
    PRINT '- Column already exists: api_failure_reason';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_verified_count')
BEGIN
    ALTER TABLE target_sites ADD api_verified_count INT DEFAULT 0;
    PRINT '+ Added column: api_verified_count';
END
ELSE
    PRINT '- Column already exists: api_verified_count';

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('target_sites') AND name = 'api_failure_count')
BEGIN
    ALTER TABLE target_sites ADD api_failure_count INT DEFAULT 0;
    PRINT '+ Added column: api_failure_count';
END
ELSE
    PRINT '- Column already exists: api_failure_count';

GO

-- Add index for API endpoint queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_target_sites_api_endpoint' AND object_id = OBJECT_ID('target_sites'))
BEGIN
    CREATE INDEX idx_target_sites_api_endpoint
    ON target_sites (api_endpoint_working, api_last_verified)
    WHERE api_menu_endpoint IS NOT NULL;
    PRINT '+ Created index: idx_target_sites_api_endpoint';
END
ELSE
    PRINT '- Index already exists: idx_target_sites_api_endpoint';
GO

PRINT '';
PRINT '========================================';
PRINT 'API Endpoint Columns Added Successfully';
PRINT '========================================';
GO
