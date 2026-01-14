# app/routers/chat.py
"""
Chat API Routes
RAG-powered chat with video knowledge base
Supports: single video context, multi-video compare, general RAG
"""
from fastapi import APIRouter, Request, Body

router = APIRouter()


@router.post("/chat")
async def api_chat(request: Request, payload: dict = Body(...)):
    """Chat với RAG - multi-turn support với planning mode và compare mode"""
    from services.llm_chat import generate_rag_answer, detect_planning_intent, generate_travel_plan, generate_comparison
    
    query = payload.get("query", "").strip()
    history = payload.get("history", [])
    video_id = payload.get("video_id", None)  # Single video context
    compare_video_ids = payload.get("compare_video_ids", [])  # Multi-video compare
    
    if compare_video_ids:
        print(f"🔍 [DEBUG] Receive Compare Request: {compare_video_ids}")
    
    if not query:
        return {"success": False, "error": "Missing query"}
    
    db = request.app.state.db
    if db is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        # COMPARE MODE: Multiple videos selected
        if compare_video_ids:
            # Clean IDs
            compare_video_ids = [str(vid).strip() for vid in compare_video_ids if str(vid).strip()]
            
        if compare_video_ids and len(compare_video_ids) >= 2:
            print(f"🔄 [COMPARE] Comparing {len(compare_video_ids)} videos: {compare_video_ids}")
            
            # Fetch all videos for comparison
            videos = []
            for vid in compare_video_ids:
                video = db.videos.find_one({"video_id": vid})
                if video:
                    videos.append(video)
            
            if len(videos) < 2:
                return {"success": False, "error": "Không tìm thấy đủ video để so sánh"}
            
            # Generate comparison analysis
            answer = generate_comparison(query, videos, history)
            
            sources = [
                {"video_id": v.get("video_id"), "title": v.get("title", "Video")}
                for v in videos
            ]
            
            print(f"✅ [COMPARE] Generated comparison for {len(videos)} videos")
            return {"success": True, "answer": answer, "sources": sources}
        
        # SINGLE VIDEO CONTEXT
        if video_id and db.videos is not None:
            video = db.videos.find_one({"video_id": video_id})
            if video:
                search_results = [video]
            else:
                search_results = db.search_videos(query, limit=5)
        else:
            # GENERAL RAG SEARCH
            search_results = db.search_videos(query, limit=5)
        
        # Detect planning intent and use appropriate generator
        if detect_planning_intent(query):
            answer = generate_travel_plan(query, search_results, history)
        else:
            answer = generate_rag_answer(query, search_results, history)
        
        # Extract source info for UI
        sources = [
            {"video_id": r.get("video_id"), "title": r.get("title", "Video")}
            for r in search_results[:3]
        ]
        
        print(f"💬 [CHAT] Query: {query[:50]}... | Sources: {len(sources)} videos")
        
        return {"success": True, "answer": answer, "sources": sources}
    except Exception as e:
        print(f"❌ [CHAT] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

