# main.py
"""
TikVault - Personal Knowledge System for TikTok Videos
Entry point for the FastAPI application

This is the simplified entry point that imports the app from the app package.
All routes are organized in app/routers/ directory.
"""
import uvicorn
from app import create_app

# Create application
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=["scraper_data", "temp", "*.db", "venv"]
    )
