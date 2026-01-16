"""
FastAPI Entry Point - TikTok Content AI Backend

Run with: uvicorn app.main:app --reload
"""

import os
import sys
from datetime import datetime
from contextlib import asynccontextmanager

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Config
from app.core.database import Database, get_collection, get_video_document_template
from app.api.videos import router as videos_router


# ============================================================
# LIFESPAN MANAGEMENT
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    print("🚀 Starting TikTok Content AI Backend...")
    await Database.connect()
    yield
    # Shutdown
    await Database.disconnect()
    print("👋 Shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Video Analysis AI",
    description="AI-powered video content analysis backend",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(videos_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK ENDPOINTS
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TikTok Content AI Backend",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================
# DATABASE TEST ENDPOINTS
# ============================================================

@app.get("/db/test")
async def test_database():
    """Test database connection with insert and find."""
    from datetime import datetime
    
    try:
        videos = await get_collection("videos")
        
        # Create test document
        test_doc = get_video_document_template()
        test_doc["video_id"] = f"test_{int(datetime.now().timestamp())}"
        test_doc["title"] = "Test Video - DB Connection Check"
        test_doc["status"] = "test"
        
        # Insert
        result = await videos.insert_one(test_doc)
        inserted_id = str(result.inserted_id)
        
        # Find
        found = await videos.find_one({"video_id": test_doc["video_id"]})
        
        # Cleanup test document
        await videos.delete_one({"video_id": test_doc["video_id"]})
        
        return {
            "status": "ok",
            "message": "Database connection successful",
            "test_results": {
                "insert": "ok",
                "find": "ok" if found else "failed",
                "delete": "ok",
                "inserted_id": inserted_id,
                "video_id": test_doc["video_id"]
            },
            "database": Config.DB_NAME
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "database": Config.DB_NAME
        }


@app.get("/db/stats")
async def database_stats():
    """Get database statistics."""
    try:
        videos = await get_collection("videos")
        
        # Get counts
        total = await videos.count_documents({})
        pending = await videos.count_documents({"status": "pending"})
        completed = await videos.count_documents({"status": "completed"})
        failed = await videos.count_documents({"status": "failed"})
        
        # Get indexes
        indexes = await videos.index_information()
        
        return {
            "status": "ok",
            "collection": "videos",
            "counts": {
                "total": total,
                "pending": pending,
                "completed": completed,
                "failed": failed
            },
            "indexes": list(indexes.keys())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

