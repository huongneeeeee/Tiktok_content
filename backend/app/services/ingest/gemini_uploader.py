# backend/app/services/ingest/gemini_uploader.py
"""
Gemini File API Upload Module

Upload video files lên Gemini File API và quản lý trạng thái processing.
Đảm bảo file ở trạng thái ACTIVE trước khi cho phép phân tích.

Features:
- Upload video với retry logic
- Poll trạng thái PROCESSING → ACTIVE
- Validate file trước khi upload
- Xử lý lỗi đầy đủ
"""

import os
import sys
import time
import mimetypes
from typing import Dict, Optional
from datetime import datetime

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Config

# Import Google GenAI SDK
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ [GEMINI_UPLOADER] google-genai SDK not installed. Run: pip install google-genai")


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class GeminiUploadError(Exception):
    """Base exception for Gemini upload errors."""
    pass


class FileValidationError(GeminiUploadError):
    """File validation failed (size, format, etc.)."""
    pass


class UploadFailedError(GeminiUploadError):
    """Upload to Gemini API failed after retries."""
    pass


class ProcessingTimeoutError(GeminiUploadError):
    """File stuck in PROCESSING state."""
    pass


class AuthenticationError(GeminiUploadError):
    """Invalid or missing API key."""
    pass


# ============================================================
# CONFIGURATION
# ============================================================

# File size limits
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB limit

# Processing timeout
PROCESSING_TIMEOUT_SECONDS = 300  # 5 minutes

# Upload retry
UPLOAD_RETRY_COUNT = 3
UPLOAD_RETRY_DELAY_SECONDS = 2

# Polling interval for processing state
POLLING_INTERVAL_SECONDS = 5

# Supported video MIME types
SUPPORTED_VIDEO_MIMES = {
    "video/mp4",
    "video/mpeg",
    "video/mov",
    "video/avi",
    "video/x-flv",
    "video/mpg",
    "video/webm",
    "video/wmv",
    "video/3gpp",
    "video/quicktime",
}


# ============================================================
# GEMINI FILE UPLOADER
# ============================================================

class GeminiFileUploader:
    """
    Upload và quản lý file video trên Gemini File API.
    
    Usage:
        uploader = GeminiFileUploader()
        result = uploader.upload_video("path/to/video.mp4")
        
        if result["success"]:
            file_uri = result["file_uri"]  # Use for Gemini analysis
    """
    
    def __init__(self, api_key: str = None):
        """
        Khởi tạo Gemini File Uploader.
        
        Args:
            api_key: Optional API key. Nếu không cung cấp, lấy từ Config.
        
        Raises:
            AuthenticationError: Nếu không có API key
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai SDK not installed. Run: pip install google-genai")
        
        self.api_key = api_key or Config.GEMINI_API_KEY
        
        if not self.api_key:
            raise AuthenticationError("Missing GEMINI_API_KEY. Set it in .env file.")
        
        # Initialize GenAI client
        self.client = genai.Client(api_key=self.api_key)
        
        print(f"✅ [GEMINI_UPLOADER] Initialized with API key")
    
    def upload_video(self, video_path: str, wait_for_ready: bool = True) -> Dict:
        """
        Upload video lên Gemini File API.
        
        Args:
            video_path: Đường dẫn file video local
            wait_for_ready: True = chờ file ACTIVE trước khi return
        
        Returns:
            {
                "success": True/False,
                "file_uri": "files/abc123...",  # URI để sử dụng với Gemini
                "file_name": "files/abc123...", # Tên file trên Gemini
                "display_name": "original_filename.mp4",
                "mime_type": "video/mp4",
                "state": "ACTIVE",
                "size_bytes": 12345678,
                "upload_time_ms": 1234,
                "error": "..." (nếu thất bại)
            }
        
        Raises:
            FileValidationError: File không hợp lệ
            UploadFailedError: Upload thất bại sau khi retry
            ProcessingTimeoutError: File stuck ở PROCESSING
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"📤 [GEMINI_UPLOADER] Starting upload")
        print(f"{'='*60}")
        print(f"   File: {os.path.basename(video_path)}")
        
        try:
            # Step 1: Validate file
            self._validate_video(video_path)
            
            # Step 2: Detect MIME type
            mime_type = self._get_mime_type(video_path)
            print(f"   MIME: {mime_type}")
            
            # Step 3: Upload with retry
            uploaded_file = self._upload_with_retry(video_path, mime_type)
            
            print(f"   ✅ Upload successful: {uploaded_file.name}")
            print(f"   State: {uploaded_file.state}")
            
            # Step 4: Wait for ACTIVE state if requested
            if wait_for_ready:
                uploaded_file = self._wait_for_active(uploaded_file.name)
            
            # Build result
            upload_time_ms = int((time.time() - start_time) * 1000)
            
            result = {
                "success": True,
                "file_uri": uploaded_file.uri,
                "file_name": uploaded_file.name,
                "display_name": getattr(uploaded_file, 'display_name', os.path.basename(video_path)),
                "mime_type": uploaded_file.mime_type,
                "state": str(uploaded_file.state),
                "size_bytes": getattr(uploaded_file, 'size_bytes', os.path.getsize(video_path)),
                "upload_time_ms": upload_time_ms,
                "uploaded_at": datetime.now().isoformat()
            }
            
            print(f"\n✅ [GEMINI_UPLOADER] Complete in {upload_time_ms}ms")
            print(f"   URI: {result['file_uri']}")
            
            return result
            
        except (FileValidationError, UploadFailedError, ProcessingTimeoutError) as e:
            # Known errors - re-raise
            print(f"\n❌ [GEMINI_UPLOADER] Error: {e}")
            raise
            
        except Exception as e:
            # Unexpected errors
            print(f"\n❌ [GEMINI_UPLOADER] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "upload_time_ms": int((time.time() - start_time) * 1000)
            }
    
    def _validate_video(self, video_path: str) -> None:
        """
        Validate file trước khi upload.
        
        Raises:
            FileValidationError: Nếu file không hợp lệ
        """
        print(f"   🔍 Validating file...")
        
        # Check file exists
        if not os.path.exists(video_path):
            raise FileValidationError(f"File not found: {video_path}")
        
        # Check is file (not directory)
        if not os.path.isfile(video_path):
            raise FileValidationError(f"Path is not a file: {video_path}")
        
        # Check file size
        file_size = os.path.getsize(video_path)
        
        if file_size == 0:
            raise FileValidationError("File is empty (0 bytes)")
        
        if file_size > MAX_FILE_SIZE_BYTES:
            size_gb = file_size / (1024**3)
            raise FileValidationError(
                f"File too large: {size_gb:.2f}GB (max: 2GB)"
            )
        
        # Check MIME type
        mime_type = self._get_mime_type(video_path)
        
        if mime_type not in SUPPORTED_VIDEO_MIMES:
            raise FileValidationError(
                f"Unsupported video format: {mime_type}. "
                f"Supported: {', '.join(SUPPORTED_VIDEO_MIMES)}"
            )
        
        print(f"   ✅ Validation passed ({file_size / (1024*1024):.1f}MB)")
    
    def _get_mime_type(self, video_path: str) -> str:
        """Detect MIME type từ file extension."""
        mime_type, _ = mimetypes.guess_type(video_path)
        
        # Default fallback for common video extensions
        if not mime_type:
            ext = os.path.splitext(video_path)[1].lower()
            mime_map = {
                ".mp4": "video/mp4",
                ".mov": "video/quicktime",
                ".avi": "video/avi",
                ".webm": "video/webm",
                ".mkv": "video/x-matroska",
                ".flv": "video/x-flv",
                ".wmv": "video/x-ms-wmv",
                ".3gp": "video/3gpp",
            }
            mime_type = mime_map.get(ext, "video/mp4")
        
        return mime_type
    
    def _upload_with_retry(self, video_path: str, mime_type: str):
        """
        Upload file với retry logic.
        
        Returns:
            File object từ Gemini API
        
        Raises:
            UploadFailedError: Sau khi hết retry
        """
        last_error = None
        
        for attempt in range(1, UPLOAD_RETRY_COUNT + 1):
            try:
                print(f"   📤 Upload attempt {attempt}/{UPLOAD_RETRY_COUNT}...")
                
                # Upload using GenAI SDK
                uploaded_file = self.client.files.upload(
                    file=video_path,
                    config={
                        "mime_type": mime_type,
                        "display_name": os.path.basename(video_path)
                    }
                )
                
                return uploaded_file
                
            except Exception as e:
                last_error = e
                print(f"   ⚠️ Attempt {attempt} failed: {e}")
                
                if attempt < UPLOAD_RETRY_COUNT:
                    print(f"   ⏳ Retrying in {UPLOAD_RETRY_DELAY_SECONDS}s...")
                    time.sleep(UPLOAD_RETRY_DELAY_SECONDS)
        
        raise UploadFailedError(
            f"Upload failed after {UPLOAD_RETRY_COUNT} attempts. Last error: {last_error}"
        )
    
    def _wait_for_active(self, file_name: str):
        """
        Poll trạng thái file đến khi ACTIVE.
        
        Args:
            file_name: Tên file trên Gemini (files/...)
        
        Returns:
            File object với state = ACTIVE
        
        Raises:
            ProcessingTimeoutError: Nếu timeout
        """
        print(f"   ⏳ Waiting for file to be ready...")
        
        start_time = time.time()
        
        while True:
            # Get current file state
            file_info = self.client.files.get(name=file_name)
            state = str(file_info.state)
            
            # Check if ACTIVE (ready)
            if "ACTIVE" in state.upper():
                print(f"   ✅ File is ACTIVE and ready")
                return file_info
            
            # Check for FAILED state
            if "FAILED" in state.upper():
                raise UploadFailedError(f"File processing failed: {state}")
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > PROCESSING_TIMEOUT_SECONDS:
                raise ProcessingTimeoutError(
                    f"File stuck in {state} state for {elapsed:.0f}s. "
                    f"Timeout: {PROCESSING_TIMEOUT_SECONDS}s"
                )
            
            # Still processing - wait and poll again
            print(f"   ⏳ State: {state} ({elapsed:.0f}s elapsed)...")
            time.sleep(POLLING_INTERVAL_SECONDS)
    
    def get_file_info(self, file_name: str) -> Dict:
        """
        Lấy thông tin file đã upload.
        
        Args:
            file_name: Tên file trên Gemini (files/...)
        
        Returns:
            Dict với thông tin file
        """
        try:
            file_info = self.client.files.get(name=file_name)
            
            return {
                "success": True,
                "file_uri": file_info.uri,
                "file_name": file_info.name,
                "display_name": getattr(file_info, 'display_name', None),
                "mime_type": file_info.mime_type,
                "state": str(file_info.state),
                "size_bytes": getattr(file_info, 'size_bytes', None),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_file_ready(self, file_name: str) -> bool:
        """
        Kiểm tra file đã ACTIVE chưa.
        
        Args:
            file_name: Tên file trên Gemini
        
        Returns:
            True nếu file ACTIVE, False nếu còn PROCESSING hoặc lỗi
        """
        try:
            file_info = self.client.files.get(name=file_name)
            return "ACTIVE" in str(file_info.state).upper()
        except:
            return False
    
    def delete_file(self, file_name: str) -> bool:
        """
        Xóa file khỏi Gemini (cleanup sau khi xử lý xong).
        
        Args:
            file_name: Tên file trên Gemini
        
        Returns:
            True nếu xóa thành công
        """
        try:
            self.client.files.delete(name=file_name)
            print(f"   🗑️ Deleted file: {file_name}")
            return True
        except Exception as e:
            print(f"   ⚠️ Failed to delete file: {e}")
            return False
    
    def list_files(self) -> list:
        """
        Liệt kê tất cả files đã upload.
        
        Returns:
            List of file info dicts
        """
        try:
            files = list(self.client.files.list())
            return [
                {
                    "file_name": f.name,
                    "display_name": getattr(f, 'display_name', None),
                    "state": str(f.state),
                    "mime_type": f.mime_type,
                }
                for f in files
            ]
        except Exception as e:
            print(f"   ⚠️ Failed to list files: {e}")
            return []


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def upload_video_to_gemini(video_path: str, api_key: str = None) -> Dict:
    """
    Convenience function để upload video.
    
    Args:
        video_path: Đường dẫn file video
        api_key: Optional API key
    
    Returns:
        Upload result dict
    """
    uploader = GeminiFileUploader(api_key=api_key)
    return uploader.upload_video(video_path)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Gemini File Uploader Test")
    print("=" * 60)
    
    # Test video path
    test_video = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    # Alternative: find any MP4 in scraper_data
    if not os.path.exists(test_video):
        scraper_dir = r"E:\Tiktok_content_AI\scraper_data\content_files"
        if os.path.exists(scraper_dir):
            for f in os.listdir(scraper_dir):
                if f.endswith(".mp4"):
                    test_video = os.path.join(scraper_dir, f)
                    break
    
    if os.path.exists(test_video):
        print(f"\n📹 Testing with: {os.path.basename(test_video)}")
        print(f"   Size: {os.path.getsize(test_video) / (1024*1024):.1f}MB")
        
        try:
            uploader = GeminiFileUploader()
            result = uploader.upload_video(test_video)
            
            print(f"\n📊 Result:")
            for key, value in result.items():
                print(f"   {key}: {value}")
            
            # Optional: delete file after test
            if result.get("success") and result.get("file_name"):
                print(f"\n🗑️ Cleaning up...")
                uploader.delete_file(result["file_name"])
                
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ No test video found")
        print(f"   Expected: {test_video}")
