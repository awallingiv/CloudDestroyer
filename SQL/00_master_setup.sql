-- FoodFinder Database Setup Script
-- Run this to create the complete database from scratch

-- Usage:
--   sqlcmd -S server_name -d master -i 00_master_setup.sql
-- Or run each file individually in SQL Server Management Studio

-- =============================================================================
-- MASTER SETUP SCRIPT FOR SQL SERVER
-- =============================================================================

-- Enable SQLCMD mode for file execution
:setvar DatabaseName "FoodFinder"
GO

-- Display setup information
SELECT 
    'Starting FoodFinder Database Setup' as message,
    GETDATE() as started_at,
    @@VERSION as sql_server_version,
    SYSTEM_USER as current_user;
GO

-- Create database and use it
:r 01_create_database.sql
GO

-- Create all tables in dependency order
:r 02_core_tables.sql
GO
:r 03_search_tables.sql
GO
:r 04_integration_tables.sql
GO
:r 05_analytics_tables.sql
GO
:r 06_operational_tables.sql
GO

-- Populate initial data
:r 07_initial_data.sql
GO

-- =============================================================================
-- SETUP VERIFICATION
-- =============================================================================

-- Verify all tables were created
SELECT 
    'Database setup verification' as check_type,
    COUNT(*) as total_tables
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_CATALOG = 'FoodFinder';
GO

-- Show table information
SELECT 
    t.TABLE_NAME as table_name,
    p.rows as estimated_rows,
    CAST(ROUND(((SUM(a.total_pages) * 8) / 1024.00), 2) AS NUMERIC(36,2)) as size_mb
FROM INFORMATION_SCHEMA.TABLES t
INNER JOIN sys.tables st ON t.TABLE_NAME = st.name
INNER JOIN sys.partitions p ON st.object_id = p.object_id
INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE t.TABLE_CATALOG = 'FoodFinder'
  AND t.TABLE_TYPE = 'BASE TABLE'
GROUP BY t.TABLE_NAME, p.rows
ORDER BY t.TABLE_NAME;
GO

-- Show foreign key relationships
SELECT 
    fk.name as constraint_name,
    tp.name as child_table,
    cp.name as child_column,
    tr.name as parent_table,
    cr.name as parent_column
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
ORDER BY tp.name, fk.name;
GO

-- Display completion message
SELECT 
    'FoodFinder Database Setup Complete!' as message,
    'All tables created successfully' as status,
    DB_NAME() as active_database,
    GETDATE() as completed_at;
GO

-- =============================================================================
-- QUICK START GUIDE
-- =============================================================================

/*
QUICK START GUIDE:

1. Setup Complete! Your FoodFinder database is ready.

2. Key Tables Created:
   - restaurants: Core restaurant data from Google Places
   - menu_items: Individual food items (the main search target)
   - menu_item_aliases: Handle user input variations ("mcdouble", "mc double")
   - search_queries: Cache and optimize searches
   - chain_configs: Major chain integration settings
   - scraping_jobs: Background processing queue

3. Next Steps:
   - Test with sample queries from 08_useful_queries.sql
   - Configure your application database connection
   - Set up your scraping and API integration services
   - Add your first restaurant data via Google Places API

4. Sample Restaurant Insert:
   INSERT INTO restaurants (restaurant_id, name, address, latitude, longitude) 
   VALUES ('ChIJexample123', 'Test Restaurant', '123 Main St', 29.4241, -98.4936);

5. Sample Menu Item Insert:
   INSERT INTO menu_items (restaurant_id, name, price, source) 
   VALUES ('ChIJexample123', 'Classic Burger', 12.99, 'manual');

6. Test Search:
   See queries in 08_useful_queries.sql for examples

Happy coding! 🍔🔍
*/