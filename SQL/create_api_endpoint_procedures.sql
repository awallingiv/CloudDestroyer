-- Create stored procedures for API endpoint management
USE CloudDestroyer;
GO

-- Save discovered API endpoint
IF OBJECT_ID('sp_SaveApiEndpoint') IS NOT NULL DROP PROCEDURE sp_SaveApiEndpoint;
GO

CREATE PROCEDURE sp_SaveApiEndpoint
    @Domain VARCHAR(255),
    @ApiMenuEndpoint VARCHAR(1000),
    @ApiEndpointType VARCHAR(50) = 'unknown',
    @RequiresLocation BIT = 0,
    @AuthenticationMethod VARCHAR(100) = 'none',
    @SiteType VARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        DECLARE @SiteId INT;

        -- Get or create site record
        SELECT @SiteId = site_id FROM target_sites WHERE domain = @Domain;

        IF @SiteId IS NULL
        BEGIN
            INSERT INTO target_sites (domain, site_name)
            VALUES (@Domain, @Domain);
            SET @SiteId = SCOPE_IDENTITY();
        END

        -- Update with API endpoint information
        UPDATE target_sites
        SET api_menu_endpoint = @ApiMenuEndpoint,
            api_endpoint_type = @ApiEndpointType,
            api_requires_location = @RequiresLocation,
            api_authentication_method = @AuthenticationMethod,
            api_endpoint_working = 1,
            api_last_verified = GETDATE(),
            api_verified_count = api_verified_count + 1,
            site_type = COALESCE(@SiteType, site_type),
            updated_at = GETDATE()
        WHERE site_id = @SiteId;

        SELECT @SiteId AS site_id, 'API endpoint saved successfully' AS message;

    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- Verify API endpoint (mark as working)
IF OBJECT_ID('sp_VerifyApiEndpoint') IS NOT NULL DROP PROCEDURE sp_VerifyApiEndpoint;
GO

CREATE PROCEDURE sp_VerifyApiEndpoint
    @Domain VARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE target_sites
    SET api_endpoint_working = 1,
        api_last_verified = GETDATE(),
        api_verified_count = api_verified_count + 1,
        api_failure_reason = NULL,
        updated_at = GETDATE()
    WHERE domain = @Domain
      AND api_menu_endpoint IS NOT NULL;

    SELECT @@ROWCOUNT AS rows_updated;
END;
GO

-- Mark API endpoint as failed
IF OBJECT_ID('sp_MarkApiEndpointFailed') IS NOT NULL DROP PROCEDURE sp_MarkApiEndpointFailed;
GO

CREATE PROCEDURE sp_MarkApiEndpointFailed
    @Domain VARCHAR(255),
    @FailureReason VARCHAR(255) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE target_sites
    SET api_endpoint_working = 0,
        api_last_failed = GETDATE(),
        api_failure_count = api_failure_count + 1,
        api_failure_reason = @FailureReason,
        updated_at = GETDATE()
    WHERE domain = @Domain
      AND api_menu_endpoint IS NOT NULL;

    SELECT @@ROWCOUNT AS rows_updated;
END;
GO

-- Get API endpoint for domain
IF OBJECT_ID('sp_GetApiEndpoint') IS NOT NULL DROP PROCEDURE sp_GetApiEndpoint;
GO

CREATE PROCEDURE sp_GetApiEndpoint
    @Domain VARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        site_id,
        domain,
        site_name,
        api_menu_endpoint,
        api_endpoint_type,
        api_requires_location,
        api_authentication_method,
        api_endpoint_working,
        api_last_verified,
        api_last_failed,
        api_failure_reason,
        api_verified_count,
        api_failure_count,
        site_type,
        cloudflare_protected,
        best_extraction_method
    FROM target_sites
    WHERE domain = @Domain;
END;
GO

-- Get working API endpoints
IF OBJECT_ID('sp_GetWorkingApiEndpoints') IS NOT NULL DROP PROCEDURE sp_GetWorkingApiEndpoints;
GO

CREATE PROCEDURE sp_GetWorkingApiEndpoints
    @MinVerifications INT = 1
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        domain,
        site_name,
        api_menu_endpoint,
        api_endpoint_type,
        api_requires_location,
        api_authentication_method,
        api_last_verified,
        api_verified_count,
        site_type
    FROM target_sites
    WHERE api_endpoint_working = 1
      AND api_menu_endpoint IS NOT NULL
      AND api_verified_count >= @MinVerifications
    ORDER BY api_last_verified DESC;
END;
GO

PRINT '';
PRINT '==================================================';
PRINT 'API Endpoint Stored Procedures Created Successfully';
PRINT '==================================================';
PRINT 'Procedures created:';
PRINT '  - sp_SaveApiEndpoint';
PRINT '  - sp_VerifyApiEndpoint';
PRINT '  - sp_MarkApiEndpointFailed';
PRINT '  - sp_GetApiEndpoint';
PRINT '  - sp_GetWorkingApiEndpoints';
GO
