# services/ocr_processor.py
"""
TikVault OCR Processor - Tesseract Edition (v4.0)

MỤC ĐÍCH:
- Trích xuất text từ video frames sử dụng Tesseract OCR
- Kết hợp với transcript để hỗ trợ phân loại
- LUÔN CHẠY - không có Decision Gate phức tạp

FLOW:
Video → FFmpeg extract frames → Tesseract OCR → Clean text → Return

OUTPUT: ocr_text để kết hợp với transcript trong analyzer
"""

import os
import time
import re
import subprocess
import tempfile
import shutil
from typing import List, Dict, Optional

import numpy as np

try:
    from PIL import Image
except ImportError:
    Image = None
    print("⚠️ [OCR] Pillow not installed. Run: pip install Pillow")

try:
    import pytesseract
except ImportError:
    pytesseract = None
    print("⚠️ [OCR] pytesseract not installed. Run: pip install pytesseract")

from config import Config


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

def configure_tesseract():
    """Configure Tesseract path for Windows"""
    if pytesseract is None:
        return False
    
    tesseract_path = getattr(Config, 'TESSERACT_PATH', None)
    if tesseract_path is None:
        # Default Windows path
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return True
    else:
        print(f"⚠️ [OCR] Tesseract not found at: {tesseract_path}")
        return False


# ============================================================
# NOISE PATTERNS - Lọc watermark, UI elements
# ============================================================

NOISE_PATTERNS = [
    r"@\w+",           # @username
    r"#\w+",           # #hashtag
    r"tiktok",
    r"douyin", 
    r"capcut",
    r"♬",
    r"original sound",
    r"âm thanh gốc",
    r"^\d+:\d+$",      # 0:15
    r"^\d+[km]$",      # 100k, 1m
    r"^\d{1,2}/\d{1,2}$",  # 1/5
]

NOISE_REGEX = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]


# ============================================================
# TESSERACT SINGLETON
# ============================================================

_tesseract_ready = None


def get_ocr_instance() -> Optional[bool]:
    """Check if Tesseract is ready"""
    global _tesseract_ready
    
    if not Config.OCR_ENABLED or pytesseract is None:
        return None
    
    if _tesseract_ready is None:
        print(f"   🔄 [OCR] Initializing Tesseract (lang={Config.OCR_LANG})...")
        try:
            if configure_tesseract():
                # Test Tesseract
                version = pytesseract.get_tesseract_version()
                print(f"   ✅ [OCR] Tesseract v{version} ready")
                _tesseract_ready = True
            else:
                _tesseract_ready = False
        except Exception as e:
            print(f"   ❌ [OCR] Tesseract init failed: {e}")
            _tesseract_ready = False
    
    return _tesseract_ready if _tesseract_ready else None


# ============================================================
# FFMPEG FRAME EXTRACTION
# ============================================================

def get_video_duration(video_path: str) -> float:
    """Get duration using ffprobe"""
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except:
        return 0


def extract_frames(video_path: str, output_dir: str) -> List[str]:
    """
    Extract frames using FFmpeg
    - 1 frame every 3-5 seconds
    - Resize to 1280px width
    - Skip first/last 10%
    """
    max_frames = Config.OCR_MAX_FRAMES
    duration = get_video_duration(video_path)
    
    if duration <= 0:
        return []
    
    # Calculate interval
    if duration < 30:
        interval = 3
    elif duration < 120:
        interval = 4
    else:
        interval = 5
    
    # Skip intro/outro
    start = duration * 0.1
    end = duration * 0.9
    usable = end - start
    
    num_frames = min(max_frames, int(usable / interval) + 1)
    if num_frames <= 0:
        num_frames = 1
        start = duration / 2
    
    print(f"   📸 [OCR] Extracting {num_frames} frames from {duration:.0f}s video")
    
    frame_paths = []
    for i in range(num_frames):
        ts = start + (i * usable / max(num_frames, 1))
        out_path = os.path.join(output_dir, f"f{i:03d}.jpg")
        
        cmd = f'ffmpeg -ss {ts:.2f} -i "{video_path}" -vframes 1 -vf "scale=1280:-1" -q:v 2 "{out_path}" -y -loglevel error'
        
        try:
            subprocess.run(cmd, shell=True, timeout=15)
            if os.path.exists(out_path):
                frame_paths.append(out_path)
        except:
            pass
    
    return frame_paths


def load_frames(paths: List[str]) -> List[Image.Image]:
    """Load images as PIL Image objects"""
    frames = []
    
    if Image is None:
        return frames
    
    for p in paths:
        try:
            img = Image.open(p)
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            frames.append(img)
        except Exception as e:
            print(f"   ⚠️ [OCR] Failed to load {p}: {e}")
    
    return frames


# ============================================================
# OCR PROCESSING
# ============================================================

def get_tesseract_lang() -> str:
    """Map config language to Tesseract language code"""
    lang_map = {
        'vi': 'vie',
        'vie': 'vie',
        'en': 'eng',
        'eng': 'eng',
        'vi+en': 'vie+eng',
    }
    return lang_map.get(Config.OCR_LANG, 'vie+eng')


def run_ocr(frames: List[Image.Image]) -> List[str]:
    """Run Tesseract OCR on frames, return list of texts"""
    if not get_ocr_instance() or pytesseract is None:
        return []
    
    all_texts = []
    lang = get_tesseract_lang()
    
    # Tesseract config for better results
    custom_config = r'--oem 3 --psm 6'
    
    for i, frame in enumerate(frames):
        try:
            # Run Tesseract
            text = pytesseract.image_to_string(
                frame, 
                lang=lang,
                config=custom_config
            )
            
            # Split into lines and filter
            lines = text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) >= 2:
                    all_texts.append(line)
                    
        except Exception as e:
            print(f"   ⚠️ [OCR] Frame {i} error: {e}")
    
    return all_texts


def clean_texts(texts: List[str]) -> str:
    """
    Clean and deduplicate OCR texts
    - Remove noise (watermarks, usernames, hashtags)
    - Remove duplicates
    - Join into single string
    """
    seen = set()
    clean = []
    
    for text in texts:
        text = text.strip()
        
        # Skip short
        if len(text) < 2:
            continue
        
        # Skip noise
        text_lower = text.lower()
        is_noise = any(p.search(text_lower) for p in NOISE_REGEX)
        if is_noise:
            continue
        
        # Dedup
        key = text_lower
        if key in seen:
            continue
        seen.add(key)
        
        clean.append(text)
    
    return "\n".join(clean)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def process_video_ocr(video_path: str, metadata: dict = None) -> Dict:
    """
    Main OCR function - Tesseract Edition
    
    Args:
        video_path: Path to video file
        metadata: Video metadata (optional, for slideshow detection)
    
    Returns:
        {
            "ocr_text": "Extracted text...",
            "text_count": 15,
            "processing_time_ms": 3500,
            "success": True
        }
    """
    if metadata is None:
        metadata = {}
    
    start = time.time()
    
    # Check if OCR enabled
    if not Config.OCR_ENABLED:
        return {"ocr_text": "", "text_count": 0, "skipped": True, "reason": "OCR disabled"}
    
    if pytesseract is None or Image is None:
        return {"ocr_text": "", "text_count": 0, "skipped": True, "reason": "pytesseract or Pillow not installed"}
    
    if not get_ocr_instance():
        return {"ocr_text": "", "text_count": 0, "skipped": True, "reason": "Tesseract not available"}
    
    # Check slideshow (use images directly from absolute paths)
    # slideshow_images_abs contains absolute file paths for OCR
    slideshow_images = metadata.get("slideshow_images_abs", [])
    if not slideshow_images:
        # Fallback to slideshow_images if abs not available
        slideshow_images = metadata.get("slideshow_images", [])
    if slideshow_images:
        print(f"   📸 [OCR] Processing {len(slideshow_images)} slideshow images...")
        frames = load_frames(slideshow_images[:Config.OCR_MAX_FRAMES])
        if frames:
            texts = run_ocr(frames)
            ocr_text = clean_texts(texts)
            return {
                "ocr_text": ocr_text,
                "text_count": len(ocr_text.split("\n")) if ocr_text else 0,
                "processing_time_ms": int((time.time() - start) * 1000),
                "source": "slideshow",
                "success": True
            }
    
    # Check video exists
    if not os.path.exists(video_path):
        return {"ocr_text": "", "text_count": 0, "error": "Video not found"}
    
    print(f"   🔍 [OCR] Processing video: {os.path.basename(video_path)}")
    
    # Create temp dir for frames
    temp_dir = tempfile.mkdtemp(prefix="ocr_")
    
    try:
        # Extract frames with FFmpeg
        frame_paths = extract_frames(video_path, temp_dir)
        
        if not frame_paths:
            return {
                "ocr_text": "",
                "text_count": 0,
                "processing_time_ms": int((time.time() - start) * 1000),
                "error": "No frames extracted"
            }
        
        # Load frames
        frames = load_frames(frame_paths)
        
        if not frames:
            return {
                "ocr_text": "",
                "text_count": 0,
                "processing_time_ms": int((time.time() - start) * 1000),
                "error": "Failed to load frames"
            }
        
        # Run OCR
        texts = run_ocr(frames)
        
        # Clean and join
        ocr_text = clean_texts(texts)
        
        elapsed = int((time.time() - start) * 1000)
        text_count = len(ocr_text.split("\n")) if ocr_text else 0
        
        print(f"   ✅ [OCR] Done: {text_count} text items in {elapsed}ms")
        
        if ocr_text:
            preview = ocr_text[:80].replace("\n", " ")
            print(f"   📝 [OCR] Preview: {preview}...")
        
        return {
            "ocr_text": ocr_text,
            "text_count": text_count,
            "frames_processed": len(frames),
            "processing_time_ms": elapsed,
            "success": True
        }
        
    except Exception as e:
        print(f"   ❌ [OCR] Error: {e}")
        return {
            "ocr_text": "",
            "text_count": 0,
            "processing_time_ms": int((time.time() - start) * 1000),
            "error": str(e)
        }
    
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=== OCR Processor v4.0 (Tesseract) Test ===")
    
    # Check FFmpeg
    try:
        r = subprocess.run("ffmpeg -version", shell=True, capture_output=True, timeout=5)
        print("✅ FFmpeg:", "available" if r.returncode == 0 else "not found")
    except:
        print("❌ FFmpeg check failed")
    
    # Check Tesseract
    ocr = get_ocr_instance()
    print("✅ Tesseract:" if ocr else "❌ Tesseract:", "ready" if ocr else "not available")
    
    # Show language info
    if ocr:
        print(f"   Language: {get_tesseract_lang()}")
