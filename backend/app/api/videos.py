"""
Video API Router

Handles video upload, URL ingestion, and AI analysis endpoints.
"""

import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

from app.services.video_ingestion import (
    save_uploaded_file,
    download_video_from_url,
    VideoIngestionError,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB
)
from app.core.database import get_collection, get_video_document_template
from app.services.analysis.gemini_video_analyzer import GeminiVideoAnalyzer
from app.models.video_analysis_models import VideoAnalysisResult


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



# ============================================================
# VIDEO ANALYSIS ENDPOINTS
# ============================================================

@router.post("/analyze")
async def analyze_video_sync(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """
    Directly analyze a video from File or URL.
    
    1. Ingests video (Upload or Download)
    2. Runs Gemini Analysis immediately
    3. Saves result to DB
    4. Returns full JSON result
    """
    if not file and not url:
        raise HTTPException(status_code=400, detail="Must provide either 'file' or 'url'")

    temp_path = None
    video_id = None
    
    try:
        # 1. Ingest Video
        if file:
            content = await file.read()
            ingest_result = await save_uploaded_file(content, file.filename)
            source_type = "upload"
        else:
            ingest_result = await download_video_from_url(url)
            source_type = "url"
            
        video_id = ingest_result["video_id"]
        temp_path = ingest_result["path"]
        
        # 2. Save Initial DB Record
        videos = await get_collection("videos")
        doc = get_video_document_template()
        doc["video_id"] = video_id
        doc["title"] = ingest_result.get("filename", "Untitled")
        doc["status"] = "processing"
        
        if source_type == "url":
             doc["url"] = ingest_result["original_url"]
             doc["metadata"]["platform"] = ingest_result.get("platform")
        
        doc["created_at"] = datetime.utcnow()
        await videos.insert_one(doc)

        # 3. Run Analysis (Synchronous in ThreadPool)
        from starlette.concurrency import run_in_threadpool
        analyzer = GeminiVideoAnalyzer()
        
        # Run blocking analysis in threadpool to avoid blocking event loop
        analysis_result = await run_in_threadpool(analyzer.analyze_video, temp_path)
        
        # 4. Update DB with Result
        if analysis_result.get("success"):
            update_data = {
                "status": "analyzed",
                "analysis": analysis_result["analysis"],
                "title": analysis_result["analysis"]["general_info"]["title"],
                "analyzed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "analysis_processing_time_ms": analysis_result.get("processing_time_ms")
            }
            await videos.update_one({"video_id": video_id}, {"$set": update_data})
            
            return {
                "success": True,
                "video_id": video_id,
                "analysis": analysis_result["analysis"]
            }
        else:
            await videos.update_one(
                {"video_id": video_id}, 
                {"$set": {"status": "failed", "error": analysis_result.get("error")}}
            )
            raise HTTPException(status_code=500, detail=f"Analysis failed: {analysis_result.get('error')}")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{video_id}/analyze")
async def analyze_video(video_id: str, background_tasks: BackgroundTasks):
    """
    Trigger AI analysis for an uploaded video.
    
    The analysis runs in the background and updates the video document
    when complete. Poll GET /videos/{video_id} to check status.
    """
    try:
        videos = await get_collection("videos")
        doc = await videos.find_one({"video_id": video_id})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if video has a local path
        local_path = doc.get("local_path", "")
        
        # Try to find video file if local_path is empty
        if not local_path or not os.path.exists(local_path):
            # Look in common directories
            possible_paths = [
                os.path.join("uploads", f"{video_id}.mp4"),
                os.path.join("scraper_data", "content_files", f"tiktok_video_{video_id}.mp4"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    local_path = p
                    break
        
        if not local_path or not os.path.exists(local_path):
            raise HTTPException(
                status_code=400, 
                detail="Video file not found. Please ensure the video is uploaded."
            )
        
        # Update status to processing
        await videos.update_one(
            {"video_id": video_id},
            {"$set": {"status": "processing", "updated_at": datetime.utcnow()}}
        )
        
        # Run analysis in background
        background_tasks.add_task(_run_analysis, video_id, local_path)
        
        return {
            "success": True,
            "message": "Analysis started",
            "video_id": video_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_analysis(video_id: str, video_path: str):
    """Background task to run video analysis."""
    from app.core.database import Database
    
    try:
        # Initialize analyzer
        analyzer = GeminiVideoAnalyzer()
        
        # Run analysis
        result = analyzer.analyze_video(video_path)
        
        # Get collection (need to reconnect for background task)
        videos = await Database.get_collection("videos")
        
        if result.get("success"):
            # Update with analysis results
            await videos.update_one(
                {"video_id": video_id},
                {
                    "$set": {
                        "status": "analyzed",
                        "analysis": result["analysis"],
                        "title": result["analysis"]["general_info"]["title"],
                        "analyzed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "analysis_processing_time_ms": result.get("processing_time_ms")
                    }
                }
            )
            print(f"✅ Analysis complete for video: {video_id}")
        else:
            # Update with error
            await videos.update_one(
                {"video_id": video_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": result.get("error", "Unknown error"),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            print(f"❌ Analysis failed for video: {video_id}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        try:
            videos = await Database.get_collection("videos")
            await videos.update_one(
                {"video_id": video_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except:
            pass


@router.get("/{video_id}/analysis")
async def get_video_analysis(video_id: str):
    """
    Get the analysis results for a video.
    """
    try:
        videos = await get_collection("videos")
        doc = await videos.find_one({"video_id": video_id})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Video not found")
        
        status = doc.get("status", "pending")
        analysis = doc.get("analysis", {})
        
        # Check if analysis has actual content
        has_analysis = bool(
            analysis.get("general_info", {}).get("title") or 
            analysis.get("virality_factors", {}).get("score")
        )
        
        return {
            "success": True,
            "video_id": video_id,
            "status": status,
            "has_analysis": has_analysis,
            "analysis": analysis if has_analysis else None,
            "analyzed_at": doc.get("analyzed_at").isoformat() if doc.get("analyzed_at") else None,
            "processing_time_ms": doc.get("analysis_processing_time_ms"),
            "error": doc.get("error") if status == "failed" else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SEARCH ENDPOINT
# ============================================================

@router.get("/search/query")
async def search_videos(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_viral_score: Optional[int] = Query(None, ge=1, le=10, description="Minimum viral score"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search videos by title, category, or key message.
    """
    try:
        videos = await get_collection("videos")
        
        # Build query
        query = {
            "status": "analyzed"  # Only return analyzed videos
        }
        
        # Text search on title and analysis fields
        if q:
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"analysis.general_info.title": {"$regex": q, "$options": "i"}},
                {"analysis.general_info.category": {"$regex": q, "$options": "i"}},
                {"analysis.content_analysis.key_message": {"$regex": q, "$options": "i"}},
            ]
        
        # Category filter
        if category:
            query["analysis.general_info.category"] = {"$regex": category, "$options": "i"}
        
        # Viral score filter
        if min_viral_score:
            query["analysis.virality_factors.score"] = {"$gte": min_viral_score}
        
        # Execute query
        cursor = videos.find(query).sort("analyzed_at", -1).skip(skip).limit(limit)
        
        results = []
        async for doc in cursor:
            analysis = doc.get("analysis", {})
            results.append({
                "video_id": doc.get("video_id"),
                "title": analysis.get("general_info", {}).get("title") or doc.get("title"),
                "category": analysis.get("general_info", {}).get("category"),
                "viral_score": analysis.get("virality_factors", {}).get("score"),
                "key_message": analysis.get("content_analysis", {}).get("key_message"),
                "target_audience": analysis.get("general_info", {}).get("target_audience"),
                "analyzed_at": doc.get("analyzed_at").isoformat() if doc.get("analyzed_at") else None
            })
        
        # Get total count
        total = await videos.count_documents(query)
        
        return {
            "success": True,
            "query": q,
            "total": total,
            "skip": skip,
            "limit": limit,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

