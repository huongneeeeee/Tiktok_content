# app/dependencies.py
"""
Shared dependencies for TikVault routers
"""
from fastapi import Request, HTTPException
from fastapi.templating import Jinja2Templates

# Shared templates instance
templates = Jinja2Templates(directory="templates")


def get_db(request: Request):
    """Get database instance from app state"""
    db = request.app.state.db
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db


def get_db_optional(request: Request):
    """Get database instance, returns None if not available"""
    return request.app.state.db
