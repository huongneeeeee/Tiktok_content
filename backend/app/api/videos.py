"""
Video API Router

Handles video upload and URL ingestion endpoints.
"""

import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

from app.services.video_ingestion import (
    save_uploaded_file,
    download_video_from_url,
    VideoIngestionError,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB
)
from app.core.database import get_collection, get_video_document_template


router = APIRouter(prefix="/videos", tags=["Videos"])


# ============================================================
# MODELS
# ============================================================

class URLRequest(BaseModel):
    url: str


class VideoResponse(BaseModel):
    success: bool
    message: str
    video_id: Optional[str] = None
    path: Optional[str] = None
    filename: Optional[str] = None
    size_mb: Optional[float] = None
    source: Optional[str] = None
    platform: Optional[str] = None


# ============================================================
# UPLOAD FILE ENDPOINT
# ============================================================

@router.post("/upload", response_model=VideoResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file.
    
    Supported formats: mp4, mov, avi, mkv, webm
    Maximum size: 500MB
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save file
        result = await save_uploaded_file(content, file.filename)
        
        # Save to database
        videos = await get_collection("videos")
        doc = get_video_document_template()
        doc["video_id"] = result["video_id"]
        doc["title"] = result["filename"]
        doc["url"] = ""
        doc["metadata"]["source_file"] = result["filename"]
        doc["metadata"]["file_size_mb"] = result["size_mb"]
        doc["metadata"]["extension"] = result["extension"]
        doc["status"] = "uploaded"
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        
        await videos.insert_one(doc)
        
        return VideoResponse(
            success=True,
            message="Video uploaded successfully",
            video_id=result["video_id"],
            path=result["path"],
            filename=result["filename"],
            size_mb=result["size_mb"],
            source="upload"
        )
        
    except VideoIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================
# DOWNLOAD FROM URL ENDPOINT
# ============================================================

@router.post("/url", response_model=VideoResponse)
async def download_from_url(request: URLRequest):
    """
    Download video from URL.
    
    Supported platforms: YouTube, TikTok
    """
    try:
        # Download video
        result = await download_video_from_url(request.url)
        
        # Save to database
        videos = await get_collection("videos")
        doc = get_video_document_template()
        doc["video_id"] = result["video_id"]
        doc["title"] = result.get("title", result["filename"])
        doc["url"] = result["original_url"]
        doc["metadata"]["platform"] = result.get("platform", "")
        doc["metadata"]["uploader"] = result.get("uploader", "")
        doc["metadata"]["uploader_name"] = result.get("uploader_name", "")
        doc["metadata"]["duration"] = result.get("duration", 0)
        doc["metadata"]["file_size_mb"] = result["size_mb"]
        doc["metadata"]["extension"] = result["extension"]
        doc["metadata"]["tiktok_id"] = result.get("tiktok_id", "")
        doc["metadata"]["hashtags"] = result.get("hashtags", [])
        doc["metadata"]["view_count"] = result.get("view_count", 0)
        doc["metadata"]["like_count"] = result.get("like_count", 0)
        doc["metadata"]["comment_count"] = result.get("comment_count", 0)
        doc["metadata"]["share_count"] = result.get("share_count", 0)
        doc["metadata"]["tiktok_metadata"] = result.get("tiktok_metadata", {})
        doc["status"] = "downloaded"
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        
        await videos.insert_one(doc)
        
        return VideoResponse(
            success=True,
            message="Video downloaded successfully",
            video_id=result["video_id"],
            path=result["path"],
            filename=result["filename"],
            size_mb=result["size_mb"],
            source="url",
            platform=result.get("platform")
        )
        
    except VideoIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


# ============================================================
# LIST VIDEOS ENDPOINT
# ============================================================

@router.get("/")
async def list_videos(skip: int = 0, limit: int = 20):
    """
    List all videos in database.
    """
    try:
        videos = await get_collection("videos")
        cursor = videos.find({}).sort("created_at", -1).skip(skip).limit(limit)
        
        result = []
        async for doc in cursor:
            result.append({
                "video_id": doc.get("video_id"),
                "title": doc.get("title"),
                "url": doc.get("url"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
            })
        
        total = await videos.count_documents({})
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "videos": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GET VIDEO INFO
# ============================================================

@router.get("/{video_id}")
async def get_video(video_id: str):
    """
    Get video details by ID.
    """
    try:
        videos = await get_collection("videos")
        doc = await videos.find_one({"video_id": video_id})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Convert ObjectId to string
        doc["_id"] = str(doc["_id"])
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat()
        if doc.get("updated_at"):
            doc["updated_at"] = doc["updated_at"].isoformat()
        
        return {
            "success": True,
            "video": doc
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# UPLOAD INFO ENDPOINT
# ============================================================

@router.get("/config/upload-info")
async def get_upload_info():
    """
    Get upload configuration info.
    """
    return {
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "supported_platforms": ["YouTube", "TikTok"]
    }
