# backend/app/services/analysis/orchestrator.py
"""
Phase 2 - Main Orchestrator: Complete Multimodal Processing

This is the main entry point for Phase 2 processing.
Orchestrates: STT → Scene Detection → OCR → Merge → Quality Assessment

Input: Phase 1 output (video_path, validation, source_metadata)
Output: Complete multimodal data ready for Phase 3 (analysis, classification)
"""

import os
import sys
import time
from typing import Dict, Optional
from datetime import datetime

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.analysis.stt import transcribe_with_timestamps
from app.services.analysis.vision import detect_scenes
from app.services.analysis.ocr import process_video_ocr_v2
from app.services.analysis.merger import merge_multimodal_data
from app.services.analysis.quality import assess_global_quality, get_content_richness_score


def process_phase2(video_path: str, phase1_data: Dict = None) -> Dict:
    """
    Complete Phase 2 processing: STT + Scene/OCR + Merge + Quality.
    
    Args:
        video_path: Path to video file
        phase1_data: Output from Phase 1 (validation, source_metadata, etc.)
    
    Returns:
    {
        # STT Data
        "transcript": str,
        "stt_segments": [...],
        "stt_quality": "good" | "low",
        
        # OCR Data
        "ocr_text": str,
        "ocr_by_scene": [...],
        "ocr_quality": "good" | "low",
        
        # Scene Data
        "scenes": [...],
        
        # Merged Data
        "multimodal_data": [...],
        "combined_text": str,
        
        # Quality
        "data_status": "valid" | "weak",
        "quality_assessment": {...},
        "content_richness": {...},
        
        # Metadata passthrough
        "source_metadata": {...},
        "validation": {...},
        
        # Processing info
        "phase2_processing_time_ms": int,
        "success": bool
    }
    """
    if phase1_data is None:
        phase1_data = {}
    
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"📦 [PHASE 2] Starting Multimodal Processing")
    print(f"{'='*60}")
    print(f"   Video: {os.path.basename(video_path)}")
    
    # Extract Phase 1 data
    validation = phase1_data.get("validation", {})
    source_metadata = phase1_data.get("source_metadata", {})
    has_audio = validation.get("metadata", {}).get("has_audio", True)
    
    # If validation says no audio, respect that
    if not has_audio:
        has_audio = source_metadata.get("has_audio", True)
    
    result = {
        "source_metadata": source_metadata,
        "validation": validation,
        "success": False
    }
    
    try:
        # ============================================================
        # STEP 1: Scene Detection
        # ============================================================
        print(f"\n📍 [PHASE 2] Step 1: Scene Detection")
        scenes = detect_scenes(video_path)
        result["scenes"] = scenes
        print(f"   ✅ Detected {len(scenes)} scenes")
        
        # ============================================================
        # STEP 2: Audio Branch - STT
        # ============================================================
        print(f"\n📍 [PHASE 2] Step 2: Speech-to-Text (STT)")
        stt_result = transcribe_with_timestamps(video_path, has_audio=has_audio)
        
        result["transcript"] = stt_result.get("transcript", "")
        result["stt_segments"] = stt_result.get("segments", [])
        result["stt_quality"] = stt_result.get("stt_quality", "low")
        result["stt_metrics"] = stt_result.get("quality_metrics", {})
        result["audio_duration"] = stt_result.get("audio_duration", 0)
        
        print(f"   ✅ STT Quality: {result['stt_quality']}")
        
        # ============================================================
        # STEP 3: Visual Branch - OCR
        # ============================================================
        print(f"\n📍 [PHASE 2] Step 3: OCR Processing")
        ocr_result = process_video_ocr_v2(
            video_path, 
            metadata=phase1_data, 
            scenes=scenes
        )
        
        result["ocr_text"] = ocr_result.get("ocr_text", "")
        result["ocr_by_scene"] = ocr_result.get("ocr_by_scene", [])
        result["ocr_quality"] = ocr_result.get("ocr_quality", "low")
        result["ocr_metrics"] = ocr_result.get("quality_metrics", {})
        
        print(f"   ✅ OCR Quality: {result['ocr_quality']}")
        
        # ============================================================
        # STEP 4: Multimodal Merge
        # ============================================================
        print(f"\n📍 [PHASE 2] Step 4: Multimodal Merge")
        merged = merge_multimodal_data(stt_result, ocr_result, scenes, source_metadata)
        
        result["multimodal_data"] = merged.get("multimodal_data", [])
        result["combined_text"] = merged.get("combined_text", "")
        result["combined_text_clean"] = merged.get("combined_text_clean", "")
        result["scenes_with_speech"] = merged.get("scenes_with_speech", 0)
        result["scenes_with_text"] = merged.get("scenes_with_text", 0)
        
        # ============================================================
        # STEP 5: Global Quality Assessment
        # ============================================================
        print(f"\n📍 [PHASE 2] Step 5: Quality Assessment")
        quality = assess_global_quality(stt_result, ocr_result)
        
        result["data_status"] = quality.get("data_status", "weak")
        result["quality_assessment"] = quality
        
        # Content richness score
        richness = get_content_richness_score(stt_result, ocr_result, merged)
        result["content_richness"] = richness
        
        print(f"   ✅ Data Status: {result['data_status']}")
        print(f"   ✅ Content Richness: {richness['score']}/100 ({richness['level']})")
        
        # ============================================================
        # FINALIZE
        # ============================================================
        result["success"] = True
        result["phase2_processing_time_ms"] = int((time.time() - start_time) * 1000)
        result["processed_at"] = datetime.now().isoformat()
        
        print(f"\n{'='*60}")
        print(f"✅ [PHASE 2] Complete in {result['phase2_processing_time_ms']}ms")
        print(f"{'='*60}")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   Scenes: {len(scenes)}")
        print(f"   STT: {result['stt_quality']} ({result['stt_metrics'].get('word_count', 0)} words)")
        print(f"   OCR: {result['ocr_quality']} ({result['ocr_metrics'].get('total_chars', 0)} chars)")
        print(f"   Status: {result['data_status']}")
        print(f"   Richness: {richness['level']} ({richness['score']}/100)")
        
        return result
        
    except Exception as e:
        import traceback
        print(f"\n❌ [PHASE 2] Error: {e}")
        traceback.print_exc()
        
        result["success"] = False
        result["error"] = str(e)
        result["phase2_processing_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result


def get_phase2_output_schema() -> Dict:
    """
    Returns the expected output schema for Phase 2.
    Useful for documentation and validation.
    """
    return {
        "transcript": "str - Full STT transcript",
        "stt_segments": "List[Dict] - Segments with start/end/text",
        "stt_quality": "str - 'good' or 'low'",
        "stt_metrics": "Dict - Word count, issues, etc.",
        
        "ocr_text": "str - Combined OCR text",
        "ocr_by_scene": "List[Dict] - OCR items with scene_id/timestamp",
        "ocr_quality": "str - 'good' or 'low'",
        "ocr_metrics": "Dict - Char count, issues, etc.",
        
        "scenes": "List[Dict] - Scene boundaries with start/end times",
        
        "multimodal_data": "List[Dict] - Merged STT+OCR per scene",
        "combined_text": "str - Full combined text with [SPOKEN]/[ON-SCREEN] tags",
        "combined_text_clean": "str - Clean combined text without tags",
        
        "data_status": "str - 'valid' or 'weak'",
        "quality_assessment": "Dict - Full quality assessment",
        "content_richness": "Dict - Score and level",
        
        "source_metadata": "Dict - Passthrough from Phase 1",
        "validation": "Dict - Passthrough from Phase 1",
        
        "success": "bool",
        "phase2_processing_time_ms": "int"
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("🧪 Phase 2 Processor Test")
    print("=" * 60)
    
    test_video = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    # Mock Phase 1 data
    mock_phase1 = {
        "validation": {
            "is_valid": True,
            "confidence": "high",
            "metadata": {
                "duration": 75,
                "has_audio": True
            }
        },
        "source_metadata": {
            "source_video_id": "7296055437135252738",
            "video_duration": 75,
            "video_type": "VIDEO"
        }
    }
    
    if os.path.exists(test_video):
        result = process_phase2(test_video, mock_phase1)
        
        print(f"\n📊 Full Result Keys: {list(result.keys())}")
        
        # Save result to file for inspection
        output_path = r"E:\Tiktok_content_AI\temp\phase2_test_output.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Clean non-serializable items
        serializable = {k: v for k, v in result.items() 
                       if not callable(v) and k != "processed_at"}
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n📁 Result saved to: {output_path}")
    else:
        print(f"❌ Test video not found: {test_video}")
