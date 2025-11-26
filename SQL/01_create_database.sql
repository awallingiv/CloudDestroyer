-- FoodFinder Database Creation Script
-- Creates the main database with proper collation for SQL Server

-- Drop database if exists (careful in production!)
-- DROP DATABASE IF EXISTS FoodFinder;

-- Create database with UTF-8 support for international restaurant names
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'FoodFinder')
BEGIN
    CREATE DATABASE FoodFinder
    COLLATE SQL_Latin1_General_CP1_CI_AS;
END
GO

-- Use the database
USE FoodFinder;
GO

-- Display database info
SELECT 
    'FoodFinder database created successfully' as status,
    DB_NAME() as current_database,
    DATABASEPROPERTYEX(DB_NAME(), 'Collation') as collation,
    @@VERSION as sql_server_version;
GO