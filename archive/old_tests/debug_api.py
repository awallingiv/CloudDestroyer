#!/usr/bin/env python3
"""
Run the API with better error handling to see what's crashing it
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from fastapi import FastAPI
import uvicorn

# Import the API components directly
from api import app, RestaurantMenuScraper

def test_scraper_only():
    """Test just the scraper part to isolate the issue"""
    print("Testing scraper initialization...")
    
    try:
        scraper = RestaurantMenuScraper()
        print("✓ Scraper initialized successfully")
        
        # Test a simple URL bypass
        print("Testing simple bypass...")
        response = scraper._get_with_orchestrator_bypass("https://bubbas33.com")
        
        if response:
            print("✓ Bypass successful")
            print(f"Response type: {type(response)}")
            if hasattr(response, 'text'):
                print(f"Text length: {len(response.text)}")
            elif isinstance(response, dict):
                print(f"Dict keys: {response.keys()}")
        else:
            print("✗ Bypass failed")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scraper_only()