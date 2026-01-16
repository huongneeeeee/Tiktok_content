import os
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse

# Add backend to path for proper imports
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load .env from project root (parent of backend)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _extract_db_name_from_uri(uri: str, default: str = "video_analysis_ai") -> str:
    """Extract database name from MongoDB URI path."""
    try:
        parsed = urlparse(uri)
        if parsed.path and parsed.path != "/":
            return parsed.path.lstrip("/").split("?")[0]
    except:
        pass
    return default


class Config:
    # ============================================================
    # API Keys
    # ============================================================
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # ============================================================
    # MongoDB Configuration
    # ============================================================
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/video_analysis_ai")
    DB_URL = MONGO_URI  # Alias for compatibility
    DB_NAME = os.getenv("DB_NAME") or _extract_db_name_from_uri(MONGO_URI)
    
    # ============================================================
    # Qdrant Vector Database
    # ============================================================
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "video_analysis_vectors")
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))  # sentence-transformers default
    
    # ============================================================
    # Paths
    # ============================================================
    BASE_DIR = PROJECT_ROOT
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
    TEMP_DIR = os.path.join(BASE_DIR, "temp")
    SCRAPER_DIR = os.path.join(BASE_DIR, "scraper_data")
    MODEL_DIR = os.path.join(BASE_DIR, "local_models")
    
    # ============================================================
    # Services
    # ============================================================
    STT_API_URL = os.getenv("STT_API_URL", "http://localhost:8019/stt/simple")
    
    # ============================================================
    # OCR Configuration (Tesseract)
    # ============================================================
    OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
    OCR_LANG = os.getenv("OCR_LANG", "vie")
    OCR_MAX_FRAMES = int(os.getenv("OCR_MAX_FRAMES", "10"))
    TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    @staticmethod
    def ensure_dirs():
        """Ensure required directories exist."""
        for dir_path in [Config.TEMP_DIR, Config.SCRAPER_DIR, Config.UPLOAD_DIR]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)


# Auto-create directories on import
Config.ensure_dirs()
