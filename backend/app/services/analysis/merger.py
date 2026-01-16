# services/multimodal_merger.py
"""
Phase 2 - Multimodal Merge: Timeline Alignment

Features:
- Align STT and OCR data on unified timeline
- Merge by scene
- Combine text sources
"""

from typing import List, Dict, Optional


def align_stt_to_scenes(stt_segments: List[Dict], scenes: List[Dict]) -> Dict[int, List[Dict]]:
    """
    Map STT segments to scenes based on timestamp overlap.
    
    Returns: {scene_id: [segment, segment, ...]}
    """
    scene_stt = {scene["scene_id"]: [] for scene in scenes}
    
    for segment in stt_segments:
        seg_start = segment.get("start", 0)
        seg_end = segment.get("end", seg_start)
        seg_mid = (seg_start + seg_end) / 2
        
        # Find which scene this segment belongs to
        for scene in scenes:
            if scene["start_time"] <= seg_mid < scene["end_time"]:
                scene_stt[scene["scene_id"]].append(segment)
                break
    
    return scene_stt


def merge_multimodal_data(
    stt_result: Dict,
    ocr_result: Dict,
    scenes: List[Dict],
    metadata: Dict = None
) -> Dict:
    """
    Merge STT and OCR data aligned by timeline/scene.
    
    Args:
        stt_result: Output from stt_processor.transcribe_with_timestamps()
        ocr_result: Output from ocr_processor_v2.process_video_ocr_v2()
        scenes: List of scenes from scene_detector
        metadata: Additional video metadata
    
    Returns:
    {
        "multimodal_data": [
            {
                "scene_id": 0,
                "start_time": 0.0,
                "end_time": 5.2,
                "stt_text": "Xin chào các bạn...",
                "stt_segments": [...],
                "ocr_text": "Bước 1: Chuẩn bị",
                "ocr_items": [...],
                "combined_text": "..."
            },
            ...
        ],
        "combined_text": "Full merged text...",
        "timeline_aligned": True,
        "scene_count": int
    }
    """
    if metadata is None:
        metadata = {}
    
    print("   🔗 [MERGE] Aligning multimodal data...")
    
    # Get STT segments and map to scenes
    stt_segments = stt_result.get("segments", [])
    scene_stt = align_stt_to_scenes(stt_segments, scenes)
    
    # Get OCR by scene
    ocr_by_scene_list = ocr_result.get("ocr_by_scene", [])
    
    # Group OCR items by scene_id
    scene_ocr = {}
    for item in ocr_by_scene_list:
        sid = item.get("scene_id", 0)
        if sid not in scene_ocr:
            scene_ocr[sid] = []
        scene_ocr[sid].append(item)
    
    # Build merged data
    multimodal_data = []
    all_combined_texts = []
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        
        # Get STT for this scene
        stt_segs = scene_stt.get(scene_id, [])
        stt_text = " ".join(seg.get("text", "") for seg in stt_segs).strip()
        
        # Get OCR for this scene
        ocr_items = scene_ocr.get(scene_id, [])
        ocr_texts = [item.get("text", "") for item in ocr_items if item.get("text")]
        ocr_text = "\n".join(ocr_texts).strip()
        
        # Combine text (prioritize STT for spoken content, OCR for on-screen)
        combined_parts = []
        if stt_text:
            combined_parts.append(f"[SPOKEN] {stt_text}")
        if ocr_text:
            combined_parts.append(f"[ON-SCREEN] {ocr_text}")
        
        combined_text = "\n".join(combined_parts)
        
        multimodal_data.append({
            "scene_id": scene_id,
            "start_time": scene["start_time"],
            "end_time": scene["end_time"],
            "duration": scene.get("duration", scene["end_time"] - scene["start_time"]),
            "stt_text": stt_text,
            "stt_segments": stt_segs,
            "ocr_text": ocr_text,
            "ocr_items": ocr_items,
            "combined_text": combined_text,
            "has_speech": bool(stt_text),
            "has_text": bool(ocr_text)
        })
        
        if combined_text:
            all_combined_texts.append(combined_text)
    
    # Build full combined text
    full_combined = "\n\n".join(all_combined_texts)
    
    # Also create a clean combined version (without tags)
    clean_stt = stt_result.get("transcript", "")
    clean_ocr = ocr_result.get("ocr_text", "")
    
    clean_combined_parts = []
    if clean_stt:
        clean_combined_parts.append(clean_stt)
    if clean_ocr:
        clean_combined_parts.append(clean_ocr)
    
    clean_combined = "\n\n".join(clean_combined_parts)
    
    print(f"   ✅ [MERGE] Aligned {len(multimodal_data)} scenes")
    
    return {
        "multimodal_data": multimodal_data,
        "combined_text": full_combined,
        "combined_text_clean": clean_combined,
        "timeline_aligned": True,
        "scene_count": len(scenes),
        "scenes_with_speech": sum(1 for m in multimodal_data if m["has_speech"]),
        "scenes_with_text": sum(1 for m in multimodal_data if m["has_text"])
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    # Simple test with mock data
    print("=" * 60)
    print("🧪 Multimodal Merger Test")
    print("=" * 60)
    
    mock_scenes = [
        {"scene_id": 0, "start_time": 0.0, "end_time": 5.0, "duration": 5.0},
        {"scene_id": 1, "start_time": 5.0, "end_time": 12.0, "duration": 7.0},
    ]
    
    mock_stt = {
        "transcript": "Xin chào các bạn. Hôm nay mình sẽ hướng dẫn.",
        "segments": [
            {"start": 0.5, "end": 2.0, "text": "Xin chào các bạn."},
            {"start": 5.5, "end": 8.0, "text": "Hôm nay mình sẽ hướng dẫn."},
        ]
    }
    
    mock_ocr = {
        "ocr_text": "Bước 1: Chuẩn bị\nBước 2: Thực hiện",
        "ocr_by_scene": [
            {"scene_id": 0, "timestamp": 2.5, "text": "Bước 1: Chuẩn bị"},
            {"scene_id": 1, "timestamp": 8.0, "text": "Bước 2: Thực hiện"},
        ]
    }
    
    result = merge_multimodal_data(mock_stt, mock_ocr, mock_scenes)
    
    print(f"\n📊 Result:")
    print(f"   Scenes aligned: {result['scene_count']}")
    print(f"   With speech: {result['scenes_with_speech']}")
    print(f"   With text: {result['scenes_with_text']}")
    
    print(f"\n📝 Combined text preview:")
    print(result['combined_text'][:300])
