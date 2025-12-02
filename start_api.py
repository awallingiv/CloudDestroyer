"""
Start CloudDestroyer API Service
"""

import uvicorn
import os

if __name__ == "__main__":
    # Configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "1"))

    print("=" * 80)
    print("CLOUDDESTROYER API SERVICE")
    print("=" * 80)
    print(f"Starting API server...")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Reload: {reload}")
    print(f"  Workers: {workers}")
    print()
    print(f"API Documentation:")
    print(f"  Swagger UI: http://localhost:{port}/docs")
    print(f"  ReDoc:      http://localhost:{port}/redoc")
    print()
    print(f"Endpoints:")
    print(f"  POST http://localhost:{port}/restaurant/extract")
    print(f"  GET  http://localhost:{port}/health")
    print("=" * 80)
    print()

    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info"
    )
