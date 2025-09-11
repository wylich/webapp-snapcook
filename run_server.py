#!/usr/bin/env python3
"""
Startup script for SnapCook FastAPI backend
"""

import uvicorn
from backend.main import app

if __name__ == "__main__":
    print("🥬 Starting SnapCook FastAPI backend...")
    print("📍 API will be available at: http://localhost:8000")
    print("📋 API documentation at: http://localhost:8000/docs")
    print("🔄 Auto-reload enabled for development")
    print()
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
