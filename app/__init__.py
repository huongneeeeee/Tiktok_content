# app/__init__.py
"""
TikVault Application Factory
Creates and configures the FastAPI application
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Templates
templates = Jinja2Templates(directory="templates")


def create_app() -> FastAPI:
    """
    Application factory pattern.
    Creates FastAPI app with all routers and middleware configured.
    """
    from services.database import TikVaultDB
    from services.tiktok_tool import init_scraper, close_scraper
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup and shutdown events"""
        print("🚀 TikVault starting...")
        
        # Create temp directory
        os.makedirs("temp", exist_ok=True)
        
        # Initialize database
        try:
            app.state.db = TikVaultDB()
            print("✅ Database connected")
        except Exception as e:
            print(f"❌ Database error: {e}")
            app.state.db = None
        
        # Initialize scraper
        init_scraper()
        
        yield
        
        # Cleanup
        close_scraper()
        print("👋 TikVault shutting down")
    
    # Create app
    app = FastAPI(
        title="TikVault API",
        description="Personal Knowledge System for TikTok Videos",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/temp", StaticFiles(directory="temp"), name="temp")
    app.mount("/scraper_images", StaticFiles(directory="scraper_data/content_files"), name="scraper_images")
    
    # Include routers
    from app.routers import pages, videos, chat, collections, system
    
    app.include_router(pages.router)
    app.include_router(videos.router, prefix="/api", tags=["Videos"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(collections.router, prefix="/api", tags=["Collections"])
    app.include_router(system.router, prefix="/api", tags=["System"])
    
    return app
