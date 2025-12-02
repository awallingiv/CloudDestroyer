#!/usr/bin/env python3
"""
Minimal API test to isolate the crash issue
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
import uvicorn

# Test if basic imports work
try:
    from src.core.cloud_destroyer import CloudDestroyer
    print("✓ CloudDestroyer import successful")
except Exception as e:
    print(f"✗ CloudDestroyer import failed: {e}")

try:
    from src.bypass.bypass_orchestrator import BypassOrchestrator
    print("✓ BypassOrchestrator import successful")
except Exception as e:
    print(f"✗ BypassOrchestrator import failed: {e}")

# Create minimal app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "working"}

@app.get("/test-destroyer")
def test_destroyer():
    try:
        # Test if CloudDestroyer can be instantiated
        destroyer = CloudDestroyer()
        return {"status": "CloudDestroyer works"}
    except Exception as e:
        return {"status": "CloudDestroyer failed", "error": str(e)}

if __name__ == "__main__":
    print("Starting minimal test API...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")