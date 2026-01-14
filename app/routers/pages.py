# app/routers/pages.py
"""
Frontend Page Routes
Serves HTML pages for the TikVault web interface
"""
import re
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import templates

router = APIRouter(tags=["Pages"])


# ------------------------
# Dashboard
# ------------------------
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, sort: str = "newest"):
    """Dashboard - Trang chủ với video grid"""
    videos = []
    
    try:
        db = request.app.state.db
        if db is not None and db.videos is not None:
            # Get videos sorted
            sort_field = "processed_at"
            sort_dir = -1  # Descending
            
            if sort == "oldest":
                sort_dir = 1
            elif sort == "views":
                sort_field = "stats.views"
            elif sort == "likes":
                sort_field = "stats.likes"
            
            cursor = db.videos.find().sort(sort_field, sort_dir).limit(50)
            for doc in cursor:
                doc["_id"] = str(doc.get("_id", ""))
                videos.append(doc)
    except Exception as e:
        print(f"Error fetching videos: {e}")
        import traceback
        traceback.print_exc()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "videos": videos,
        "sort": sort,
        "storage_used": 15,
        "storage_total": 20,
        "user_initial": "U"
    })


# ------------------------
# Library
# ------------------------
def _clean_category_key(key):
    """Strip Roman numeral prefix (I., II., etc.)"""
    if not key:
        return key
    return re.sub(r'^[IVX]+\.\s*', '', key)


@router.get("/library", response_class=HTMLResponse)
async def library(request: Request, category: str = None, sub: str = None, sort: str = "newest"):
    """Library - Hiển thị tất cả video theo category"""
    videos = []
    categories = []
    subcategories = []
    category_counts = {}
    
    clean_category = _clean_category_key(category) if category else None
    
    db = request.app.state.db
    if db is not None:
        try:
            # Get categories from database
            if db.categories is not None:
                raw_categories = list(db.categories.find({"is_active": True}).sort("order", 1))
                
                # Count videos per category
                for cat in raw_categories:
                    cat_key = _clean_category_key(cat["key"])
                    count = db.videos.count_documents({"ai_analysis.classification.level_1": cat_key}) if db.videos is not None else 0
                    cat["video_count"] = count
                    cat["clean_key"] = cat_key
                    category_counts[cat_key] = count
                categories = raw_categories
                
                # Get subcategories for current category with counts
                if clean_category:
                    cat_doc = db.categories.find_one({
                        "$or": [
                            {"key": clean_category},
                            {"key": {"$regex": f".*{clean_category}$"}}
                        ]
                    })
                    if cat_doc and cat_doc.get("subcategories"):
                        subs_with_counts = []
                        for sub_item in cat_doc["subcategories"]:
                            sub_key = sub_item.get("key", "")
                            sub_count = db.videos.count_documents({
                                "ai_analysis.classification.level_1": clean_category,
                                "ai_analysis.classification.level_2": sub_key
                            }) if db.videos is not None else 0
                            sub_item["video_count"] = sub_count
                            subs_with_counts.append(sub_item)
                        subcategories = subs_with_counts
            
            # Fallback: use defaults from analyzer
            if not categories:
                from services.analyzer import CATEGORY_TREE
                categories = [
                    {"key": k, "clean_key": k, "name": k.replace("_", " "), "order": i, "video_count": 0}
                    for i, k in enumerate(CATEGORY_TREE.keys())
                ]
            
            # Build query
            query = {}
            if clean_category:
                query["ai_analysis.classification.level_1"] = clean_category
            if sub:
                query["ai_analysis.classification.level_2"] = sub
            
            # Determine sort order
            sort_field = "processed_at"
            sort_dir = -1
            if sort == "oldest":
                sort_dir = 1
            elif sort == "views":
                sort_field = "stats.views"
            elif sort == "likes":
                sort_field = "stats.likes"
            
            # Get videos
            if db.videos is not None:
                videos = list(db.videos.find(query).sort(sort_field, sort_dir).limit(100))
                print(f"📚 [LIBRARY] Query: {query}")
                print(f"📚 [LIBRARY] Found {len(videos)} videos (category={category}, sub={sub}, sort={sort})")
        except Exception as e:
            print(f"Error fetching library: {e}")
            import traceback
            traceback.print_exc()
    
    return templates.TemplateResponse("library.html", {
        "request": request,
        "videos": videos,
        "categories": categories,
        "subcategories": subcategories,
        "current_category": category,
        "current_subcategory": sub,
        "current_sort": sort,
        "total_videos": sum(c.get("video_count", 0) for c in categories)
    })


# ------------------------
# Search
# ------------------------
@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    """Search - Tìm kiếm video với Hybrid Search"""
    results = []
    ai_answer = None
    
    if q and request.app.state.db:
        try:
            results = request.app.state.db.search_videos(q, limit=3)
            
            if results:
                from services.llm_chat import generate_rag_answer
                ai_answer = generate_rag_answer(q, results)
        except Exception as e:
            print(f"Search error: {e}")
            import traceback
            traceback.print_exc()
    
    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "results": results,
        "ai_answer": ai_answer
    })


# ------------------------
# Video Detail
# ------------------------
def _serialize_mongo_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    from datetime import datetime
    from bson import ObjectId
    
    if doc is None:
        return None
    
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _serialize_mongo_doc(value)
        elif isinstance(value, list):
            result[key] = [
                _serialize_mongo_doc(item) if isinstance(item, dict) else 
                str(item) if isinstance(item, ObjectId) else
                item.isoformat() if isinstance(item, datetime) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


@router.get("/video/{video_id}")
async def video_detail(request: Request, video_id: str):
    """Video Detail - Chi tiết video (HTML or JSON based on Accept header)"""
    video = None
    
    if request.app.state.db is not None and request.app.state.db.videos is not None:
        try:
            video = request.app.state.db.videos.find_one({"video_id": video_id})
        except Exception as e:
            print(f"Error fetching video: {e}")
    
    if not video:
        # Check if client wants JSON
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Video not found"}, status_code=404)
        return RedirectResponse(url="/", status_code=303)
    
    # Check if client wants JSON (for API calls from frontend)
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header:
        from fastapi.responses import JSONResponse
        # Serialize MongoDB document (handles ObjectId, datetime, etc.)
        serialized_video = _serialize_mongo_doc(video)
        return JSONResponse(serialized_video)
    
    # Default: return HTML
    return templates.TemplateResponse("video_detail.html", {
        "request": request,
        "video": video
    })


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat page - RAG-powered knowledge assistant"""
    return templates.TemplateResponse("chat.html", {"request": request})

