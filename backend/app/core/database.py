"""
Database Module - MongoDB Connection Singleton

Provides centralized database access for the entire application.
Uses Motor for async MongoDB operations with FastAPI.

Usage:
    from app.core.database import get_database, get_collection
    
    # In async context
    db = await get_database()
    videos = await get_collection("videos")
"""

import os
import sys
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

# Ensure imports work
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Config


# ============================================================
# SINGLETON CONNECTION
# ============================================================

class Database:
    """
    MongoDB connection singleton.
    Ensures only one connection pool is created.
    """
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls) -> AsyncIOMotorDatabase:
        """
        Connect to MongoDB and return database instance.
        Creates connection if not exists.
        """
        if cls._client is None:
            print(f"📦 [DB] Connecting to MongoDB...")
            print(f"   URI: {Config.MONGO_URI}")
            print(f"   Database: {Config.DB_NAME}")
            cls._client = AsyncIOMotorClient(Config.MONGO_URI)
            cls._database = cls._client[Config.DB_NAME]
            
            # Create indexes on first connection
            await cls._create_indexes()
            
            print(f"✅ [DB] Connected successfully")
        
        return cls._database
    
    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._database = None
            print("🔌 [DB] Disconnected from MongoDB")
    
    @classmethod
    async def get_collection(cls, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name."""
        db = await cls.connect()
        return db[name]
    
    @classmethod
    async def _create_indexes(cls):
        """Create indexes for collections."""
        if cls._database is None:
            return
        
        # Videos collection indexes
        videos = cls._database["videos"]
        
        indexes = [
            IndexModel([("title", TEXT)], name="title_text"),
            IndexModel([("category", ASCENDING)], name="category_asc"),
            IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
            IndexModel([("video_id", ASCENDING)], name="video_id_unique", unique=True),
            IndexModel([("status", ASCENDING)], name="status_asc"),
        ]
        
        try:
            existing = await videos.index_information()
            for idx in indexes:
                idx_name = idx.document.get("name")
                if idx_name and idx_name not in existing:
                    await videos.create_indexes([idx])
                    print(f"   📇 [DB] Created index: {idx_name}")
        except Exception as e:
            print(f"   ⚠️ [DB] Index creation warning: {e}")


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    return await Database.connect()


async def get_collection(name: str) -> AsyncIOMotorCollection:
    """Get collection by name."""
    return await Database.get_collection(name)


async def close_database():
    """Close database connection."""
    await Database.disconnect()


# ============================================================
# VIDEOS COLLECTION SCHEMA
# ============================================================

VIDEOS_SCHEMA = {
    "video_id": "str - Unique TikTok video ID",
    "title": "str - Video title/description",
    "url": "str - Original TikTok URL",
    
    # Metadata
    "metadata": {
        "author": {
            "id": "str",
            "username": "str",
            "nickname": "str"
        },
        "stats": {
            "views": "int",
            "likes": "int",
            "comments": "int",
            "shares": "int"
        },
        "duration": "float - Video duration in seconds",
        "hashtags": "list[str]",
        "music": {
            "title": "str",
            "author": "str"
        }
    },
    
    # Analysis Results
    "analysis": {
        "transcript": "str - STT transcript",
        "ocr_text": "str - Extracted OCR text",
        "normalized_text": "str - Cleaned/normalized content",
        "category": "str - Content category",
        "sub_category": "str - Sub-category",
        "keywords": "list[str]",
        "summary": "str - AI-generated summary",
        "quality_score": "float - 0.0 to 1.0"
    },
    
    # Status
    "status": "str - pending|processing|completed|failed",
    "error": "str - Error message if failed",
    
    # Timestamps
    "created_at": "datetime - When record was created",
    "updated_at": "datetime - Last update time",
    "analyzed_at": "datetime - When analysis completed"
}


def get_video_document_template() -> dict:
    """Return an empty video document template."""
    from datetime import datetime
    
    return {
        "video_id": "",
        "title": "",
        "url": "",
        "metadata": {
            "author": {"id": "", "username": "", "nickname": ""},
            "stats": {"views": 0, "likes": 0, "comments": 0, "shares": 0},
            "duration": 0.0,
            "hashtags": [],
            "music": {"title": "", "author": ""}
        },
        "analysis": {
            "transcript": "",
            "ocr_text": "",
            "normalized_text": "",
            "category": "",
            "sub_category": "",
            "keywords": [],
            "summary": "",
            "quality_score": 0.0
        },
        "status": "pending",
        "error": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "analyzed_at": None
    }
