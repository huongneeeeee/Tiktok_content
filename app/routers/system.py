# app/routers/system.py
"""
System API Routes
Administrative functions like database reset
"""
import os
import shutil
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/system/reset")
async def reset_system(request: Request):
    """Reset entire system - DANGEROUS!"""
    try:
        request.app.state.db.reset_database()
    except Exception:
        pass

    shutil.rmtree("temp", ignore_errors=True)
    os.makedirs("temp", exist_ok=True)

    return {"success": True, "message": "System reset complete"}
