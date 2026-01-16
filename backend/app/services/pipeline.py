# backend/app/services/pipeline.py
import time
import traceback
from datetime import datetime
import os
import sys

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# New structure imports (Ingest -> Analysis -> Processing)
from app.services.ingest.downloader import download_tiktok_full_data
from app.services.ingest.validator import validate_video, should_normalize
from app.services.ingest.normalizer import normalize_video
from app.services.analysis.orchestrator import process_phase2 as process_analysis
from app.services.processing.synthesizer import process_phase3 as process_core


def process_tiktok(url: str):
    """
    Orchestrates the Professional Content Pipeline:
    1. Ingest (Download, Validate, Normalize)
    2. Analysis (Multimodal Processing)
    3. Core (Content Synthesis & Reasoning)
    """
    print(f"\n🎬 [PIPELINE] Started processing: {url}")
    
    # ==================================================================================
    # STEP 1: INGEST LAYER
    # ==================================================================================
    print(f"\n{'='*40}\n📍 STEP 1: INGEST & NORMALIZATION\n{'='*40}")
    
    try:
        dl = download_tiktok_full_data(url)
    except Exception as e:
        print(f"❌ [INGEST] Download error: {e}")
        traceback.print_exc()
        return None, f"Download error: {str(e)}"
    
    if not dl:
        print("❌ [INGEST] Download returned None")
        return None, "Download failed"

    # Base Video Info
    video_info = dl["metadata"]
    video_info["video_id"] = video_info.get("id")
    video_info["filename"] = dl["filename"]
    video_info["type"] = "video"
    video_info["processed_at"] = datetime.now()
    


    local_path = dl["local_path"]

    # Validation
    print("   🔍 [INGEST] Validating video...")
    validation = validate_video(local_path)
    video_info["validation"] = validation
    
    # Update metadata from validation if available
    if validation.get("metadata") and "source_metadata" in video_info:
        ffprobe_meta = validation["metadata"]
        video_info["source_metadata"]["video_duration"] = ffprobe_meta.get("duration", 0)
        video_info["source_metadata"]["has_audio"] = ffprobe_meta.get("has_audio", True)
        if ffprobe_meta.get("width") and ffprobe_meta.get("height"):
            video_info["source_metadata"]["video_resolution"] = {
                "width": ffprobe_meta["width"],
                "height": ffprobe_meta["height"]
            }
    
    # Normalization
    if should_normalize(validation):
        print("   🔄 [INGEST] Normalizing video...")
        normalized_path = normalize_video(local_path)
        if normalized_path:
            local_path = normalized_path
            video_info["normalized"] = True
            print("   ✅ [INGEST] Normalized successfully")

    # ==================================================================================
    # STEP 2: ANALYSIS LAYER
    # ==================================================================================
    print(f"\n{'='*40}\n📍 STEP 2: MULTIMODAL ANALYSIS\n{'='*40}")
    
    # Validate strictly before Analysis
    if not os.path.exists(local_path):
         return None, "Video file not found after Ingest"

    # Call Analysis Orchestrator
    analysis_output = process_analysis(local_path, video_info)
    video_info["analysis_data"] = analysis_output
    
    if not analysis_output["success"]:
        print(f"❌ [ANALYSIS] Failed: {analysis_output.get('error')}")

    # ==================================================================================
    # STEP 3: CORE LAYER (CONTENT)
    # ==================================================================================
    print(f"\n{'='*40}\n📍 STEP 3: CONTENT SYNTHESIS\n{'='*40}")
    
    # Call Core Synthesizer
    core_output = process_core(analysis_output)
    video_info["core_data"] = core_output
    
    # Flatten key fields
    video_info["final_transcript"] = core_output.get("normalized_text", "")
    video_info["reasoning_ready"] = core_output.get("reasoning_ready", False)
    video_info["content_quality"] = core_output.get("reasoning_status", {}).get("content_quality", "low")

    # Return pure data
    return video_info, "OK"
