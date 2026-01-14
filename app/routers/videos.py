# app/routers/videos.py
"""
Video API Routes
Handles video processing, management, and export
"""
import os
import glob
from fastapi import APIRouter, Request, UploadFile, File, Body
from fastapi.responses import PlainTextResponse

from services.pipeline import process_tiktok, process_text

router = APIRouter()


# ------------------------
# TikTok Processing
# ------------------------
@router.post("/tiktok/process")
async def api_process_tiktok(request: Request, payload: dict = Body(...)):
    """Process a TikTok URL and extract content"""
    url = payload.get("url")
    if not url:
        return {"success": False, "error": "Missing url"}

    data, msg = process_tiktok(url, request.app.state.db)

    if not data:
        return {"success": False, "error": msg}

    return {"success": True, "data": data}


# ------------------------
# Text Upload
# ------------------------
@router.post("/text/upload")
async def api_upload_text(request: Request, file: UploadFile = File(...)):
    """Upload and process text file"""
    if not file.filename.endswith(".txt"):
        return {"success": False, "error": "Only .txt supported"}

    content = (await file.read()).decode("utf-8", errors="ignore")
    data, msg = process_text(content, file.filename, request.app.state.db)

    if not data:
        return {"success": False, "error": msg}

    return {"success": True, "data": data}


# ------------------------
# Search
# ------------------------
@router.post("/search")
async def api_search(request: Request, payload: dict = Body(...)):
    """Search videos using hybrid search"""
    query = payload.get("query")
    if not query:
        return {"success": False, "error": "Missing query"}

    results = request.app.state.db.search_videos(query, limit=10)
    return {"success": True, "results": results}


# ------------------------
# Delete Video
# ------------------------
@router.delete("/video/{video_id}")
async def delete_video(request: Request, video_id: str):
    """Delete a video from database"""
    db = request.app.state.db
    if db is None or db.videos is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        result = db.videos.delete_one({"video_id": video_id})
        
        if result.deleted_count == 0:
            return {"success": False, "error": "Video not found"}
        
        # Cleanup local files
        temp_files = glob.glob(f"temp/{video_id}*")
        for f in temp_files:
            try:
                os.remove(f)
            except:
                pass
        
        return {"success": True, "message": "Video deleted"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ------------------------
# Re-analyze Video
# ------------------------
@router.post("/video/{video_id}/reanalyze")
async def reanalyze_video(request: Request, video_id: str):
    """Re-analyze a video with updated Knowledge Card prompt"""
    from services.analyzer import analyze_video_content
    
    db = request.app.state.db
    if db is None or db.videos is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        video = db.videos.find_one({"video_id": video_id})
        if not video:
            return {"success": False, "error": "Video not found"}
        
        transcript = video.get("transcript", "")
        metadata = {
            "title": video.get("title", ""),
            "author": video.get("author", {}),
            "hashtags": video.get("hashtags", []),
            "duration": video.get("duration", 0)
        }
        
        print(f"🔄 Re-analyzing video: {video_id}")
        
        ai_result = analyze_video_content(transcript, metadata)
        
        db.videos.update_one(
            {"video_id": video_id},
            {"$set": {"ai_analysis": ai_result}}
        )
        
        video["ai_analysis"] = ai_result
        db._save_video_embeddings(video_id, video)
        
        print(f"✅ Re-analysis complete: {ai_result.get('classification', {}).get('category_path', 'N/A')}")
        
        return {
            "success": True, 
            "message": "Re-analysis complete",
            "knowledge_card": ai_result.get("knowledge_card", {})
        }
    except Exception as e:
        print(f"❌ Re-analyze error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ------------------------
# Export Knowledge
# ------------------------
@router.get("/video/{video_id}/export")
async def export_knowledge(request: Request, video_id: str, format: str = "markdown"):
    """Export Knowledge Card as Markdown"""
    db = request.app.state.db
    if db is None or db.videos is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        video = db.videos.find_one({"video_id": video_id})
        if not video:
            return {"success": False, "error": "Video not found"}
        
        ai_analysis = video.get("ai_analysis", {})
        kc = ai_analysis.get("knowledge_card", {})
        
        # Build Markdown
        md = f"# {kc.get('title', video.get('title', 'Untitled'))}\n\n"
        md += f"**Category:** {kc.get('category_path', 'N/A')}\n"
        md += f"**Scores:** Knowledge {kc.get('knowledge_density', 0)}/10 | Actionability {kc.get('actionability', 0)}/10\n\n"
        
        md += f"## Summary\n{kc.get('summary', ai_analysis.get('summary', 'N/A'))}\n\n"
        
        takeaways = kc.get("key_takeaways", [])
        if takeaways:
            md += "## Key Takeaways\n"
            for t in takeaways:
                md += f"- {t}\n"
            md += "\n"
        
        ingredients = kc.get("entities", {}).get("ingredients", [])
        if ingredients:
            md += "## Ingredients\n"
            for ing in ingredients:
                md += f"- {ing}\n"
            md += "\n"
        
        action_items = kc.get("action_items", [])
        if action_items:
            md += "## Steps\n"
            for i, step in enumerate(action_items, 1):
                md += f"{i}. {step}\n"
            md += "\n"
        
        products = kc.get("entities", {}).get("products", [])
        if products:
            md += "## Products Mentioned\n"
            for p in products:
                md += f"- {p}\n"
            md += "\n"
        
        locations = kc.get("entities", {}).get("locations", [])
        if locations:
            md += "## Locations\n"
            for loc in locations:
                md += f"- {loc}\n"
            md += "\n"
        
        tags = kc.get("tags", [])
        if tags:
            md += f"---\n**Tags:** {', '.join(tags)}\n"
        
        md += f"\n---\n*Source: TikVault - Video ID: {video_id}*\n"
        
        return PlainTextResponse(content=md, media_type="text/markdown")
        
    except Exception as e:
        return {"success": False, "error": str(e)}
