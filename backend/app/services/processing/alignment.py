# services/content_aligner.py
"""
Phase 3 - Step 3.1 & 3.2: Time Alignment & Content Chunking

Features:
- Căn chỉnh STT + OCR theo timeline chung
- Gộp content theo time segments/scenes
- Tạo content_chunk[] với source tracking
"""

from typing import List, Dict, Optional


def align_content_to_timeline(
    multimodal_data: List[Dict],
    scenes: List[Dict] = None
) -> List[Dict]:
    """
    Căn chỉnh STT + OCR theo timeline chung.
    Sử dụng multimodal_data từ Phase 2 (đã được merge theo scene).
    
    Args:
        multimodal_data: Output từ multimodal_merger
        scenes: Scene boundaries (optional, để fallback)
    
    Returns:
    [
        {
            "chunk_id": 0,
            "scene_id": 0,
            "start_time": 0.0,
            "end_time": 5.0,
            "duration": 5.0,
            "stt_text": "...",
            "ocr_text": "...",
            "source": "both" | "stt" | "ocr" | "none",
            "has_stt": True,
            "has_ocr": True
        }
    ]
    """
    if not multimodal_data:
        return []
    
    aligned_chunks = []
    
    for i, item in enumerate(multimodal_data):
        stt_text = item.get("stt_text", "").strip()
        ocr_text = item.get("ocr_text", "").strip()
        
        # Determine source
        has_stt = bool(stt_text)
        has_ocr = bool(ocr_text)
        
        if has_stt and has_ocr:
            source = "both"
        elif has_stt:
            source = "stt"
        elif has_ocr:
            source = "ocr"
        else:
            source = "none"
        
        chunk = {
            "chunk_id": i,
            "scene_id": item.get("scene_id", i),
            "start_time": item.get("start_time", 0.0),
            "end_time": item.get("end_time", 0.0),
            "duration": item.get("duration", item.get("end_time", 0) - item.get("start_time", 0)),
            "stt_text": stt_text,
            "ocr_text": ocr_text,
            "stt_segments": item.get("stt_segments", []),
            "ocr_items": item.get("ocr_items", []),
            "source": source,
            "has_stt": has_stt,
            "has_ocr": has_ocr
        }
        
        aligned_chunks.append(chunk)
    
    return aligned_chunks


def create_content_windows(
    aligned_chunks: List[Dict],
    window_size: float = 10.0,
    overlap: float = 2.0
) -> List[Dict]:
    """
    Tạo các content windows với overlap để không mất context.
    Useful cho long videos.
    
    Args:
        aligned_chunks: Output từ align_content_to_timeline
        window_size: Kích thước window (giây)
        overlap: Thời gian overlap giữa windows
    
    Returns:
    [
        {
            "window_id": 0,
            "start_time": 0.0,
            "end_time": 10.0,
            "chunks": [chunk0, chunk1, ...],
            "combined_stt": "...",
            "combined_ocr": "..."
        }
    ]
    """
    if not aligned_chunks:
        return []
    
    # Get total duration
    min_time = min(c["start_time"] for c in aligned_chunks)
    max_time = max(c["end_time"] for c in aligned_chunks)
    
    # If video is short, return single window
    if max_time - min_time <= window_size:
        all_stt = " ".join(c["stt_text"] for c in aligned_chunks if c["stt_text"]).strip()
        all_ocr = "\n".join(c["ocr_text"] for c in aligned_chunks if c["ocr_text"]).strip()
        
        return [{
            "window_id": 0,
            "start_time": min_time,
            "end_time": max_time,
            "chunks": aligned_chunks,
            "chunk_ids": [c["chunk_id"] for c in aligned_chunks],
            "combined_stt": all_stt,
            "combined_ocr": all_ocr
        }]
    
    # Create overlapping windows
    windows = []
    window_id = 0
    current_start = min_time
    
    while current_start < max_time:
        window_end = min(current_start + window_size, max_time)
        
        # Find chunks in this window
        window_chunks = [
            c for c in aligned_chunks
            if (c["start_time"] < window_end and c["end_time"] > current_start)
        ]
        
        if window_chunks:
            combined_stt = " ".join(c["stt_text"] for c in window_chunks if c["stt_text"]).strip()
            combined_ocr = "\n".join(c["ocr_text"] for c in window_chunks if c["ocr_text"]).strip()
            
            windows.append({
                "window_id": window_id,
                "start_time": current_start,
                "end_time": window_end,
                "chunks": window_chunks,
                "chunk_ids": [c["chunk_id"] for c in window_chunks],
                "combined_stt": combined_stt,
                "combined_ocr": combined_ocr
            })
            window_id += 1
        
        # Move to next window with overlap
        current_start += window_size - overlap
    
    return windows


def get_timeline_stats(aligned_chunks: List[Dict]) -> Dict:
    """
    Thống kê về timeline alignment.
    """
    if not aligned_chunks:
        return {
            "total_chunks": 0,
            "chunks_with_stt": 0,
            "chunks_with_ocr": 0,
            "chunks_with_both": 0,
            "chunks_empty": 0,
            "total_duration": 0
        }
    
    stats = {
        "total_chunks": len(aligned_chunks),
        "chunks_with_stt": sum(1 for c in aligned_chunks if c["has_stt"]),
        "chunks_with_ocr": sum(1 for c in aligned_chunks if c["has_ocr"]),
        "chunks_with_both": sum(1 for c in aligned_chunks if c["source"] == "both"),
        "chunks_empty": sum(1 for c in aligned_chunks if c["source"] == "none"),
        "total_duration": sum(c["duration"] for c in aligned_chunks),
        "stt_coverage": 0.0,
        "ocr_coverage": 0.0
    }
    
    total_dur = stats["total_duration"]
    if total_dur > 0:
        stt_dur = sum(c["duration"] for c in aligned_chunks if c["has_stt"])
        ocr_dur = sum(c["duration"] for c in aligned_chunks if c["has_ocr"])
        stats["stt_coverage"] = round(stt_dur / total_dur, 2)
        stats["ocr_coverage"] = round(ocr_dur / total_dur, 2)
    
    return stats


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Content Aligner Test")
    print("=" * 60)
    
    # Mock multimodal data
    mock_data = [
        {
            "scene_id": 0,
            "start_time": 0.0,
            "end_time": 5.0,
            "duration": 5.0,
            "stt_text": "Xin chào các bạn.",
            "ocr_text": "Bước 1: Chuẩn bị",
            "stt_segments": [],
            "ocr_items": []
        },
        {
            "scene_id": 1,
            "start_time": 5.0,
            "end_time": 12.0,
            "duration": 7.0,
            "stt_text": "Hôm nay mình sẽ hướng dẫn.",
            "ocr_text": "",
            "stt_segments": [],
            "ocr_items": []
        },
        {
            "scene_id": 2,
            "start_time": 12.0,
            "end_time": 20.0,
            "duration": 8.0,
            "stt_text": "",
            "ocr_text": "Bước 2: Thực hiện",
            "stt_segments": [],
            "ocr_items": []
        }
    ]
    
    # Test alignment
    aligned = align_content_to_timeline(mock_data)
    print(f"\n📊 Aligned Chunks: {len(aligned)}")
    
    for chunk in aligned:
        print(f"   Chunk {chunk['chunk_id']}: source={chunk['source']}, "
              f"time={chunk['start_time']:.1f}-{chunk['end_time']:.1f}s")
    
    # Test stats
    stats = get_timeline_stats(aligned)
    print(f"\n📈 Stats:")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   With STT: {stats['chunks_with_stt']}")
    print(f"   With OCR: {stats['chunks_with_ocr']}")
    print(f"   With both: {stats['chunks_with_both']}")
    print(f"   STT coverage: {stats['stt_coverage']*100:.0f}%")
