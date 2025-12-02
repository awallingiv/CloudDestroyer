#!/usr/bin/env python3
"""
Simple test to see if API starts correctly
"""

# Try to directly import and run a simplified version
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
import uvicorn

def create_simple_app():
    app = FastAPI(title="Test API")
    
    @app.get("/")
    def root():
        return {"message": "API is working"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    return app

if __name__ == "__main__":
    print("Starting simple test API...")
    app = create_simple_app()
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")