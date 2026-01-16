# backend/app/services/analysis/ocr.py
"""
Phase 2 - Visual Branch: Enhanced OCR Processor

Features:
- Scene-based OCR (OCR per scene with timestamps)
- OCR quality assessment (good/low)
- Integration with scene_detector
- Noise filtering and deduplication
"""

import os
import sys
import time
import re
import tempfile
import shutil
from typing import List, Dict, Optional

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Config
from app.services.analysis.vision import get_scene_info, detect_scenes, extract_keyframes_per_scene


# ============================================================
# CONFIGURATION
# ============================================================

# Noise patterns to filter out
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
# TESSERACT SETUP
# ============================================================

def configure_tesseract() -> bool:
    """Configure Tesseract path for Windows"""
    if pytesseract is None:
        return False
    
    tesseract_path = getattr(Config, 'TESSERACT_PATH', None)
    if tesseract_path is None:
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return True
    return False


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


_ocr_ready = None

def init_ocr() -> bool:
    """Initialize OCR engine"""
    global _ocr_ready
    
    if _ocr_ready is None:
        if pytesseract is None or Image is None:
            _ocr_ready = False
        elif configure_tesseract():
            try:
                pytesseract.get_tesseract_version()
                _ocr_ready = True
            except:
                _ocr_ready = False
        else:
            _ocr_ready = False
    
    return _ocr_ready


# ============================================================
# OCR PROCESSING
# ============================================================

def run_ocr_on_frame(frame_path: str) -> Dict:
    """
    Run OCR on a single frame.
    
    Returns:
    {
        "raw_text": str,
        "lines": [...],
        "char_count": int,
        "success": bool
    }
    """
    if not init_ocr():
        return {"raw_text": "", "lines": [], "char_count": 0, "success": False}
    
    try:
        img = Image.open(frame_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        lang = get_tesseract_lang()
        custom_config = r'--oem 3 --psm 6'
        
        text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return {
            "raw_text": text.strip(),
            "lines": lines,
            "char_count": len(text.strip()),
            "success": True
        }
        
    except Exception as e:
        return {"raw_text": "", "lines": [], "char_count": 0, "success": False, "error": str(e)}


def is_noise_text(text: str) -> bool:
    """Check if text is noise (watermarks, UI elements)"""
    text_lower = text.lower().strip()
    
    if len(text) < 2:
        return True
    
    for pattern in NOISE_REGEX:
        if pattern.search(text_lower):
            return True
    
    return False


def clean_ocr_lines(lines: List[str]) -> List[str]:
    """Clean and filter OCR lines"""
    seen = set()
    clean = []
    
    for line in lines:
        line = line.strip()
        
        if len(line) < 2:
            continue
        
        if is_noise_text(line):
            continue
        
        # Deduplicate (case-insensitive)
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        
        clean.append(line)
    
    return clean


# ============================================================
# QUALITY ASSESSMENT
# ============================================================

def assess_ocr_quality(ocr_by_scene: List[Dict], total_frames: int) -> Dict:
    """
    Assess OCR quality based on various metrics.
    
    Returns:
    {
        "quality": "good" | "low",
        "metrics": {
            "total_chars": int,
            "total_lines": int,
            "readable_frames": int,
            "readable_ratio": float,
            "avg_chars_per_frame": float,
            "noise_ratio": float,
            "issues": [...]
        }
    }
    """
    issues = []
    
    # Aggregate stats
    total_chars = 0
    total_lines = 0
    readable_frames = 0
    noise_count = 0
    total_raw_lines = 0
    
    for item in ocr_by_scene:
        char_count = item.get("char_count", 0)
        lines = item.get("clean_lines", [])
        raw_lines = item.get("raw_lines", [])
        
        total_chars += char_count
        total_lines += len(lines)
        total_raw_lines += len(raw_lines)
        
        if char_count > 5 and lines:
            readable_frames += 1
        
        # Count filtered noise
        noise_count += len(raw_lines) - len(lines)
    
    # Calculate ratios
    readable_ratio = readable_frames / max(total_frames, 1)
    avg_chars = total_chars / max(total_frames, 1)
    noise_ratio = noise_count / max(total_raw_lines, 1)
    
    # Issue detection
    if total_chars < 5:
        issues.append("almost_no_text")
    elif total_chars < 20:
        issues.append("very_little_text")
    
    if readable_ratio < 0.1:
        issues.append("few_readable_frames")
    
    if noise_ratio > 0.6:
        issues.append("high_noise")
    
    if avg_chars < 2:
        issues.append("low_text_density")
    
    # Quality decision
    is_low = (
        total_chars < 5 or
        readable_ratio < 0.1 or
        len(issues) >= 3
    )
    
    quality = "low" if is_low else "good"
    
    return {
        "quality": quality,
        "metrics": {
            "total_chars": total_chars,
            "total_lines": total_lines,
            "readable_frames": readable_frames,
            "readable_ratio": round(readable_ratio, 2),
            "avg_chars_per_frame": round(avg_chars, 1),
            "noise_ratio": round(noise_ratio, 2),
            "issues": issues
        }
    }


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def process_video_ocr_v2(
    video_path: str, 
    metadata: dict = None,
    scenes: List[Dict] = None
) -> Dict:
    """
    Enhanced OCR processing with scene-based extraction and quality assessment.
    
    Args:
        video_path: Path to video file
        metadata: Video metadata (for slideshow detection)
        scenes: Pre-computed scenes (optional, will detect if not provided)
    
    Returns:
    {
        "ocr_text": "Combined text...",
        "ocr_by_scene": [
            {"scene_id": 0, "timestamp": 2.5, "text": "Bước 1: ...", "char_count": 15},
            ...
        ],
        "ocr_quality": "good" | "low",
        "quality_metrics": {...},
        "frames_processed": int,
        "success": True
    }
    """
    if metadata is None:
        metadata = {}
    
    start_time = time.time()
    
    # Check if OCR available
    if not init_ocr():
        return {
            "ocr_text": "",
            "ocr_by_scene": [],
            "ocr_quality": "low",
            "quality_metrics": {"issues": ["ocr_not_available"]},
            "frames_processed": 0,
            "success": False,
            "error": "Tesseract not available"
        }
    

    
    print(f"   🔍 [OCR] Processing video: {os.path.basename(video_path)}")
    
    # Create temp dir for frames
    temp_dir = tempfile.mkdtemp(prefix="ocr_v2_")
    
    try:
        # Step 1: Get scenes and keyframes
        if scenes is None:
            scene_info = get_scene_info(video_path, temp_dir)
            scenes = scene_info["scenes"]
            keyframes = scene_info["keyframes"]
        else:
            keyframes = extract_keyframes_per_scene(video_path, scenes, temp_dir)
        
        if not keyframes:
            return {
                "ocr_text": "",
                "ocr_by_scene": [],
                "ocr_quality": "low",
                "quality_metrics": {"issues": ["no_frames_extracted"]},
                "frames_processed": 0,
                "success": False
            }
        
        # Step 2: Run OCR on each keyframe
        print(f"   📝 [OCR] Running OCR on {len(keyframes)} keyframes...")
        
        ocr_by_scene = []
        all_clean_lines = []
        
        for kf in keyframes:
            ocr_result = run_ocr_on_frame(kf["frame_path"])
            
            if ocr_result["success"]:
                raw_lines = ocr_result["lines"]
                clean_lines = clean_ocr_lines(raw_lines)
                
                ocr_by_scene.append({
                    "scene_id": kf["scene_id"],
                    "timestamp": kf["timestamp"],
                    "frame_id": kf["frame_id"],
                    "text": "\n".join(clean_lines),
                    "clean_lines": clean_lines,
                    "raw_lines": raw_lines,
                    "char_count": len("\n".join(clean_lines))
                })
                
                all_clean_lines.extend(clean_lines)
        
        # Step 3: Deduplicate across all frames
        seen = set()
        deduped_lines = []
        for line in all_clean_lines:
            key = line.lower()
            if key not in seen:
                seen.add(key)
                deduped_lines.append(line)
        
        combined_text = "\n".join(deduped_lines)
        
        # Step 4: Assess quality
        quality_result = assess_ocr_quality(ocr_by_scene, len(keyframes))
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"   📊 [OCR] Quality: {quality_result['quality']} ({quality_result['metrics']['total_chars']} chars)")
        if quality_result["metrics"]["issues"]:
            print(f"   ⚠️ [OCR] Issues: {', '.join(quality_result['metrics']['issues'])}")
        
        if combined_text:
            preview = combined_text[:80].replace("\n", " ")
            print(f"   📝 [OCR] Preview: {preview}...")
        
        return {
            "ocr_text": combined_text,
            "ocr_by_scene": ocr_by_scene,
            "ocr_quality": quality_result["quality"],
            "quality_metrics": quality_result["metrics"],
            "frames_processed": len(keyframes),
            "scenes_count": len(scenes),
            "processing_time_ms": elapsed_ms,
            "success": True
        }
        
    except Exception as e:
        print(f"   ❌ [OCR] Error: {e}")
        return {
            "ocr_text": "",
            "ocr_by_scene": [],
            "ocr_quality": "low",
            "quality_metrics": {"issues": ["processing_error"]},
            "frames_processed": 0,
            "success": False,
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
    import json
    
    print("=" * 60)
    print("🧪 OCR Processor v2 Test")
    print("=" * 60)
    
    # Check Tesseract
    if init_ocr():
        print("✅ Tesseract ready")
    else:
        print("❌ Tesseract not available")
        exit(1)
    
    test_video = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    if os.path.exists(test_video):
        result = process_video_ocr_v2(test_video)
        
        print(f"\n📊 Results:")
        print(f"   OCR Quality: {result['ocr_quality']}")
        print(f"   Frames processed: {result['frames_processed']}")
        print(f"   Total chars: {result['quality_metrics'].get('total_chars', 0)}")
        
        if result['ocr_text']:
            print(f"\n📝 Extracted text:")
            print(result['ocr_text'][:500])
    else:
        print(f"❌ Test video not found: {test_video}")
