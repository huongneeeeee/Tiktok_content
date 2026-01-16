"""
Video Ingestion Service

Handles video file uploads and URL downloads.
Uses TT_Content_Scraper for TikTok video downloads.
"""

import os
import re
import uuid
import asyncio
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import sys

from app.core.config import Config

# Add project root to path for TT_Content_Scraper import
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from TT_Content_Scraper.src.scraper_functions.base_scraper import BaseScraper


# Allowed video formats
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MAX_FILE_SIZE_MB = 500  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class VideoIngestionError(Exception):
    """Custom exception for video ingestion errors."""
    pass


def generate_video_id() -> str:
    """Generate unique video ID."""
    return f"vid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def validate_file_extension(filename: str) -> Tuple[bool, str]:
    """Validate file extension."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    return True, ""


def validate_file_size(size_bytes: int) -> Tuple[bool, str]:
    """Validate file size."""
    if size_bytes > MAX_FILE_SIZE_BYTES:
        size_mb = size_bytes / (1024 * 1024)
        return False, f"File too large ({size_mb:.1f}MB). Maximum: {MAX_FILE_SIZE_MB}MB"
    return True, ""


def get_upload_path(video_id: str, extension: str) -> str:
    """Get the full path for uploaded video."""
    filename = f"{video_id}{extension}"
    return os.path.join(Config.UPLOAD_DIR, filename)


async def save_uploaded_file(file_content: bytes, filename: str) -> dict:
    """
    Save uploaded video file.
    
    Args:
        file_content: File bytes
        filename: Original filename
    
    Returns:
        dict with video_id, path, and file info
    """
    # Validate extension
    valid, error = validate_file_extension(filename)
    if not valid:
        raise VideoIngestionError(error)
    
    # Validate size
    valid, error = validate_file_size(len(file_content))
    if not valid:
        raise VideoIngestionError(error)
    
    # Generate ID and path
    video_id = generate_video_id()
    extension = Path(filename).suffix.lower()
    file_path = get_upload_path(video_id, extension)
    
    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    return {
        "video_id": video_id,
        "filename": filename,
        "path": file_path,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "extension": extension,
        "source": "upload",
        "created_at": datetime.utcnow().isoformat()
    }


def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract TikTok video ID from various URL formats.
    
    Supports:
    - https://www.tiktok.com/@user/video/1234567890
    - https://vm.tiktok.com/abc123/
    - https://vt.tiktok.com/abc123/
    """
    # Standard TikTok URL: /video/1234567890
    match = re.search(r'/video/(\d+)', url)
    if match:
        return match.group(1)
    
    # Short URL format - need to resolve it
    if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
        try:
            import requests
            response = requests.head(url, allow_redirects=True, timeout=10)
            match = re.search(r'/video/(\d+)', response.url)
            if match:
                return match.group(1)
        except:
            pass
    
    return None


def is_valid_url(url: str) -> Tuple[bool, str]:
    """Check if URL is a valid TikTok video URL."""
    url_lower = url.lower()
    
    # Check for TikTok
    tiktok_domains = ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]
    
    for domain in tiktok_domains:
        if domain in url_lower:
            return True, "tiktok"
    
    return False, "unsupported"


async def download_video_from_url(url: str) -> dict:
    """
    Download video from TikTok URL using TT_Content_Scraper.
    
    Args:
        url: TikTok video URL
    
    Returns:
        dict with video_id, path, metadata, and video info
    """
    # Validate URL
    valid, platform = is_valid_url(url)
    if not valid:
        raise VideoIngestionError("Unsupported URL. Only TikTok URLs are supported.")
    
    # Extract TikTok video ID from URL
    tiktok_id = extract_video_id_from_url(url)
    if not tiktok_id:
        raise VideoIngestionError("Could not extract video ID from URL. Please check the URL format.")
    
    # Generate our internal video ID
    video_id = generate_video_id()
    
    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    
    try:
        # Use TT_Content_Scraper to download
        scraper = BaseScraper()
        
        # Run scraper in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Get metadata and binary links
        metadata, links = await loop.run_in_executor(
            None,
            lambda: scraper.scrape_metadata(tiktok_id)
        )
        
        # Check if it's a video (not a slideshow)
        if not links.get("mp4"):
            raise VideoIngestionError("This appears to be a slideshow/photo post, not a video.")
        
        # Download video binary
        binaries = await loop.run_in_executor(
            None,
            lambda: scraper.scrape_binaries(links)
        )
        
        if not binaries.get("mp4"):
            raise VideoIngestionError("Failed to download video. The video may be private or unavailable.")
        
        # Save video to file
        file_path = os.path.join(Config.UPLOAD_DIR, f"{video_id}.mp4")
        with open(file_path, 'wb') as f:
            f.write(binaries["mp4"])
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        # Extract useful metadata
        video_meta = metadata.get("video_metadata", {})
        file_meta = metadata.get("file_metadata", {})
        author_meta = metadata.get("author_metadata", {})
        
        return {
            "video_id": video_id,
            "tiktok_id": tiktok_id,
            "filename": f"{video_id}.mp4",
            "path": file_path,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "extension": ".mp4",
            "source": "url",
            "platform": platform,
            "original_url": url,
            # Rich metadata from TikTok
            "title": video_meta.get("description", ""),
            "duration": file_meta.get("duration", 0),
            "uploader": author_meta.get("username", ""),
            "uploader_name": author_meta.get("name", ""),
            "hashtags": video_meta.get("hashtags", []),
            "view_count": video_meta.get("playcount", 0),
            "like_count": video_meta.get("diggcount", 0),
            "comment_count": video_meta.get("commentcount", 0),
            "share_count": video_meta.get("sharecount", 0),
            "created_at": datetime.utcnow().isoformat(),
            "tiktok_metadata": metadata  # Full metadata for later use
        }
        
    except VideoIngestionError:
        raise
    except KeyError as e:
        raise VideoIngestionError(f"Video not found or unavailable: {str(e)}")
    except ConnectionError as e:
        raise VideoIngestionError(f"Network error downloading video: {str(e)}")
    except Exception as e:
        raise VideoIngestionError(f"Error downloading video: {str(e)}")


def cleanup_video(path: str) -> bool:
    """Delete a video file."""
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    except Exception:
        return False


def get_video_info(path: str) -> Optional[dict]:
    """Get basic info about a video file."""
    if not os.path.exists(path):
        return None
    
    stat = os.stat(path)
    return {
        "path": path,
        "filename": os.path.basename(path),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "extension": Path(path).suffix.lower(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
    }
