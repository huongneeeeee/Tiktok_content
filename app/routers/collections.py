# app/routers/collections.py
"""
Collections & User Data API Routes
Handles collections, notes, tags, and favorites
"""
from datetime import datetime
from fastapi import APIRouter, Request, Body
from bson import ObjectId

router = APIRouter()


# ------------------------
# Collections CRUD
# ------------------------
@router.get("/collections")
async def get_collections(request: Request):
    """Get all user collections"""
    db = request.app.state.db
    if db is None or db.user_collections is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        collections = list(db.user_collections.find().sort("updated_at", -1))
        for c in collections:
            c["_id"] = str(c["_id"])
            c["video_count"] = len(c.get("video_ids", []))
        return {"success": True, "collections": collections}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/collections")
async def create_collection(request: Request, payload: dict = Body(...)):
    """Create a new collection"""
    db = request.app.state.db
    if db is None or db.user_collections is None:
        return {"success": False, "error": "Database not available"}
    
    name = payload.get("name", "").strip()
    if not name:
        return {"success": False, "error": "Collection name is required"}
    
    try:
        collection = {
            "name": name,
            "description": payload.get("description", ""),
            "icon": payload.get("icon", "📁"),
            "color": payload.get("color", "#3b82f6"),
            "video_ids": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = db.user_collections.insert_one(collection)
        collection["_id"] = str(result.inserted_id)
        return {"success": True, "collection": collection}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/collections/{collection_id}")
async def update_collection(request: Request, collection_id: str, payload: dict = Body(...)):
    """Update a collection"""
    db = request.app.state.db
    if db is None or db.user_collections is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        update_data = {"updated_at": datetime.utcnow()}
        if "name" in payload:
            update_data["name"] = payload["name"]
        if "description" in payload:
            update_data["description"] = payload["description"]
        if "icon" in payload:
            update_data["icon"] = payload["icon"]
        if "color" in payload:
            update_data["color"] = payload["color"]
        
        result = db.user_collections.update_one(
            {"_id": ObjectId(collection_id)},
            {"$set": update_data}
        )
        return {"success": True, "modified": result.modified_count > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/collections/{collection_id}")
async def delete_collection(request: Request, collection_id: str):
    """Delete a collection"""
    db = request.app.state.db
    if db is None or db.user_collections is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        result = db.user_collections.delete_one({"_id": ObjectId(collection_id)})
        return {"success": True, "deleted": result.deleted_count > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/collections/{collection_id}/videos")
async def add_video_to_collection(request: Request, collection_id: str, payload: dict = Body(...)):
    """Add or remove video from collection"""
    db = request.app.state.db
    if db is None or db.user_collections is None:
        return {"success": False, "error": "Database not available"}
    
    video_id = payload.get("video_id")
    action = payload.get("action", "add")
    
    if not video_id:
        return {"success": False, "error": "video_id is required"}
    
    try:
        if action == "add":
            result = db.user_collections.update_one(
                {"_id": ObjectId(collection_id)},
                {
                    "$addToSet": {"video_ids": video_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        else:
            result = db.user_collections.update_one(
                {"_id": ObjectId(collection_id)},
                {
                    "$pull": {"video_ids": video_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        return {"success": True, "modified": result.modified_count > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ------------------------
# User Notes & Tags
# ------------------------
@router.put("/video/{video_id}/notes")
async def update_video_notes(request: Request, video_id: str, payload: dict = Body(...)):
    """Update user notes for a video"""
    db = request.app.state.db
    if db is None or db.videos is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        notes = payload.get("notes", "")
        result = db.videos.update_one(
            {"video_id": video_id},
            {"$set": {
                "user_notes": notes,
                "updated_by_user_at": datetime.utcnow()
            }}
        )
        return {"success": True, "modified": result.modified_count > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/video/{video_id}/tags")
async def update_video_tags(request: Request, video_id: str, payload: dict = Body(...)):
    """Update user tags for a video"""
    db = request.app.state.db
    if db is None or db.videos is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        tags = payload.get("tags", [])
        result = db.videos.update_one(
            {"video_id": video_id},
            {"$set": {
                "user_tags": tags,
                "updated_by_user_at": datetime.utcnow()
            }}
        )
        return {"success": True, "modified": result.modified_count > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/video/{video_id}/favorite")
async def toggle_favorite(request: Request, video_id: str, payload: dict = Body(...)):
    """Toggle favorite status for a video"""
    db = request.app.state.db
    if db is None or db.videos is None:
        return {"success": False, "error": "Database not available"}
    
    try:
        is_favorite = payload.get("is_favorite", False)
        result = db.videos.update_one(
            {"video_id": video_id},
            {"$set": {
                "is_favorite": is_favorite,
                "updated_by_user_at": datetime.utcnow()
            }}
        )
        return {"success": True, "is_favorite": is_favorite}
    except Exception as e:
        return {"success": False, "error": str(e)}
