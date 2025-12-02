#!/usr/bin/env python3
"""
Test basic API connectivity
"""
import requests
import time
import threading
import subprocess
import sys
import os

def start_api():
    """Start the API in a subprocess"""
    try:
        process = subprocess.Popen([sys.executable, "api.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        return process
    except Exception as e:
        print(f"Failed to start API: {e}")
        return None

def test_basic_connectivity():
    """Test basic API endpoints"""
    
    print("Starting API server...")
    api_process = start_api()
    
    if not api_process:
        print("Failed to start API")
        return
    
    # Wait for startup
    time.sleep(5)
    
    try:
        # Test health endpoint
        print("Testing health endpoint...")
        response = requests.get("http://localhost:8000/health", timeout=10)
        print(f"Health check: {response.status_code} - {response.text}")
        
        # Test root endpoint  
        print("Testing root endpoint...")
        response = requests.get("http://localhost:8000/", timeout=10)
        print(f"Root endpoint: {response.status_code} - {response.text}")
        
    except Exception as e:
        print(f"Connection error: {e}")
    
    finally:
        # Stop API
        print("Stopping API...")
        api_process.terminate()
        
        # Get output
        stdout, stderr = api_process.communicate(timeout=5)
        if stdout:
            print("STDOUT:")
            print(stdout)
        if stderr:
            print("STDERR:")  
            print(stderr)

if __name__ == "__main__":
    test_basic_connectivity()