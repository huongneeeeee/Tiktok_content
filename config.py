import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Services
    STT_API_URL = os.getenv("STT_API_URL", "http://localhost:8019/stt/simple")
    
    # OCR Configuration (Tesseract)
    OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
    OCR_LANG = os.getenv("OCR_LANG", "vie")  # vie for Vietnamese, eng for English
    OCR_MAX_FRAMES = int(os.getenv("OCR_MAX_FRAMES", "10"))
    TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMP_DIR = os.path.join(BASE_DIR, "temp")
    SCRAPER_DIR = os.path.join(BASE_DIR, "scraper_data")
    MODEL_DIR = os.path.join(BASE_DIR, "local_models")

    @staticmethod
    def ensure_dirs():
        if not os.path.exists(Config.TEMP_DIR): os.makedirs(Config.TEMP_DIR)
        if not os.path.exists(Config.SCRAPER_DIR): os.makedirs(Config.SCRAPER_DIR)

# Tự động tạo thư mục khi import config
Config.ensure_dirs()