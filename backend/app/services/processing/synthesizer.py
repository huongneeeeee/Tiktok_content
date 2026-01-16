# backend/app/services/processing/synthesizer.py
"""
Phase 3 - Main Orchestrator: Content Understanding & Normalization

Chuyển Raw Multimodal Data (Phase 2) → Nội dung đã hiểu, sẵn sàng cho AI reasoning.

Pipeline:
1. Time Alignment - Căn chỉnh STT/OCR theo timeline
2. Content Chunking - Gộp content theo scenes
3. STT/OCR Comparison - So sánh và chọn nguồn tin cậy
4. Content Cleaning - Loại bỏ noise, fillers
5. Language Normalization - Chuẩn hóa ngôn ngữ
6. Reasoning Check - Đánh giá reasoning_ready
"""

import os
import sys
import time
from typing import Dict, List, Optional
from datetime import datetime

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.processing.alignment import align_content_to_timeline, get_timeline_stats
from app.services.processing.comparison import process_chunk_comparison
from app.services.processing.cleaning import process_chunk_content
from app.services.processing.reasoning import check_reasoning_ready


def process_phase3(phase2_output: Dict) -> Dict:
    """
    Complete Phase 3 processing: Content Understanding & Normalization.
    
    Args:
        phase2_output: Output từ Phase 2 (process_phase2)
    
    Returns:
    {
        # Content Chunks (aligned, compared, cleaned, normalized)
        "content_chunks": [
            {
                "chunk_id": 0,
                "scene_id": 0,
                "timestamp": {"start": 0.0, "end": 5.0},
                "final_text": "Cleaned & normalized text...",
                "source": "stt" | "ocr" | "merged",
                "source_weight": {"stt": 0.7, "ocr": 0.3},
                "content_confidence": "high" | "medium" | "low",
                "comparison": {...},
                "priority": {...}
            }
        ],
        
        # Normalized full text
        "normalized_text": str,
        
        # Reasoning status
        "reasoning_ready": True | False,
        "reasoning_status": {...},
        
        # Statistics
        "timeline_stats": {...},
        
        # Passthrough from Phase 2
        "data_status": "valid" | "weak",
        "stt_quality": str,
        "ocr_quality": str,
        "scenes": [...],
        "source_metadata": {...},
        
        "phase3_processing_time_ms": int,
        "success": bool
    }
    """
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"🧠 [PHASE 3] Starting Content Understanding & Normalization")
    print(f"{'='*60}")
    
    # Extract Phase 2 data
    multimodal_data = phase2_output.get("multimodal_data", [])
    scenes = phase2_output.get("scenes", [])
    stt_quality = phase2_output.get("stt_quality", "low")
    ocr_quality = phase2_output.get("ocr_quality", "low")
    data_status = phase2_output.get("data_status", "weak")
    
    result = {
        # Passthrough
        "data_status": data_status,
        "stt_quality": stt_quality,
        "ocr_quality": ocr_quality,
        "scenes": scenes,
        "source_metadata": phase2_output.get("source_metadata", {}),
        "transcript": phase2_output.get("transcript", ""),
        "ocr_text": phase2_output.get("ocr_text", ""),
        "success": False
    }
    
    try:
        # ============================================================
        # STEP 1: Time Alignment
        # ============================================================
        print(f"\n📍 [PHASE 3] Step 1: Time Alignment")
        
        aligned_chunks = align_content_to_timeline(multimodal_data, scenes)
        timeline_stats = get_timeline_stats(aligned_chunks)
        
        print(f"   ✅ Aligned {len(aligned_chunks)} chunks")
        print(f"   ✅ STT coverage: {timeline_stats['stt_coverage']*100:.0f}%")
        print(f"   ✅ OCR coverage: {timeline_stats['ocr_coverage']*100:.0f}%")
        
        result["timeline_stats"] = timeline_stats
        
        # ============================================================
        # STEP 2: STT/OCR Comparison per Chunk
        # ============================================================
        print(f"\n📍 [PHASE 3] Step 2: STT/OCR Comparison")
        
        compared_chunks = []
        for chunk in aligned_chunks:
            compared = process_chunk_comparison(chunk, stt_quality, ocr_quality)
            compared_chunks.append(compared)
        
        # Stats
        relations = {}
        for c in compared_chunks:
            rel = c.get("comparison", {}).get("relation", "independent")
            relations[rel] = relations.get(rel, 0) + 1
        
        print(f"   ✅ Comparison results: {relations}")
        
        # ============================================================
        # STEP 3: Content Cleaning & Normalization
        # ============================================================
        print(f"\n📍 [PHASE 3] Step 3: Content Cleaning & Normalization")
        
        cleaned_chunks = []
        total_removed = 0
        
        for chunk in compared_chunks:
            cleaned = process_chunk_content(chunk)
            cleaned_chunks.append(cleaned)
            total_removed += cleaned.get("processing_stats", {}).get("removed_words", 0)
        
        print(f"   ✅ Cleaned {len(cleaned_chunks)} chunks")
        print(f"   ✅ Removed ~{total_removed} noise words")
        
        # ============================================================
        # STEP 4: Build Final Content Chunks
        # ============================================================
        print(f"\n📍 [PHASE 3] Step 4: Building Content Chunks")
        
        content_chunks = []
        all_final_texts = []
        
        for chunk in cleaned_chunks:
            final_text = chunk.get("final_text", "").strip()
            
            content_chunk = {
                "chunk_id": chunk.get("chunk_id", 0),
                "scene_id": chunk.get("scene_id", 0),
                "timestamp": {
                    "start": chunk.get("start_time", 0.0),
                    "end": chunk.get("end_time", 0.0)
                },
                "duration": chunk.get("duration", 0.0),
                
                # Content
                "final_text": final_text,
                "source": chunk.get("priority", {}).get("primary_source", "none"),
                "source_weight": chunk.get("priority", {}).get("weight", {}),
                "content_confidence": chunk.get("content_confidence", "low"),
                
                # Detailed data (for debugging)
                "comparison": chunk.get("comparison", {}),
                "priority": chunk.get("priority", {}),
                "processing_stats": chunk.get("processing_stats", {})
            }
            
            content_chunks.append(content_chunk)
            
            if final_text:
                all_final_texts.append(final_text)
        
        # Build normalized full text
        normalized_text = "\n\n".join(all_final_texts)
        
        result["content_chunks"] = content_chunks
        result["normalized_text"] = normalized_text
        
        print(f"   ✅ Built {len(content_chunks)} content chunks")
        print(f"   ✅ Normalized text: {len(normalized_text)} chars")
        
        # ============================================================
        # STEP 5: Reasoning Readiness Check
        # ============================================================
        print(f"\n📍 [PHASE 3] Step 5: Reasoning Readiness Check")
        
        quality_data = {
            "data_status": data_status,
            "stt_quality": stt_quality,
            "ocr_quality": ocr_quality
        }
        
        reasoning_status = check_reasoning_ready(content_chunks, quality_data)
        
        result["reasoning_ready"] = reasoning_status["reasoning_ready"]
        result["reasoning_status"] = reasoning_status
        
        # ============================================================
        # FINALIZE
        # ============================================================
        result["success"] = True
        result["phase3_processing_time_ms"] = int((time.time() - start_time) * 1000)
        result["processed_at"] = datetime.now().isoformat()
        
        print(f"\n{'='*60}")
        print(f"✅ [PHASE 3] Complete in {result['phase3_processing_time_ms']}ms")
        print(f"{'='*60}")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   Content chunks: {len(content_chunks)}")
        print(f"   Normalized text: {len(normalized_text.split())} words")
        print(f"   Reasoning ready: {result['reasoning_ready']}")
        print(f"   Content quality: {reasoning_status['content_quality']}")
        
        if not result["reasoning_ready"]:
            print(f"\n⚠️ Not ready for reasoning:")
            print(f"   Reason: {reasoning_status['reason']}")
            for action in reasoning_status.get("recommended_actions", [])[:3]:
                print(f"   → {action}")
        
        return result
        
    except Exception as e:
        import traceback
        print(f"\n❌ [PHASE 3] Error: {e}")
        traceback.print_exc()
        
        result["success"] = False
        result["error"] = str(e)
        result["phase3_processing_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result


def get_phase3_output_schema() -> Dict:
    """
    Returns the expected output schema for Phase 3.
    """
    return {
        "content_chunks": "List[Dict] - Processed chunks with final_text, confidence, etc.",
        "normalized_text": "str - Full normalized text",
        "reasoning_ready": "bool - True if AI can reason from this content",
        "reasoning_status": "Dict - Full reasoning assessment",
        
        "timeline_stats": "Dict - Coverage and alignment stats",
        
        "data_status": "str - Passthrough from Phase 2",
        "stt_quality": "str - Passthrough",
        "ocr_quality": "str - Passthrough",
        "scenes": "List - Passthrough",
        "source_metadata": "Dict - Passthrough",
        
        "success": "bool",
        "phase3_processing_time_ms": "int"
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("🧪 Phase 3 Processor Test")
    print("=" * 60)
    
    # Mock Phase 2 output
    mock_phase2 = {
        "multimodal_data": [
            {
                "scene_id": 0,
                "start_time": 0.0,
                "end_time": 5.0,
                "duration": 5.0,
                "stt_text": "Xin chào các bạn, ừm, hôm nay mình sẽ hướng dẫn.",
                "ocr_text": "Hướng dẫn nấu ăn",
                "stt_segments": [],
                "ocr_items": []
            },
            {
                "scene_id": 1,
                "start_time": 5.0,
                "end_time": 12.0,
                "duration": 7.0,
                "stt_text": "Bước 1 là chuẩn bị nguyên liệu cần thiết.",
                "ocr_text": "Bước 1: Chuẩn bị",
                "stt_segments": [],
                "ocr_items": []
            },
            {
                "scene_id": 2,
                "start_time": 12.0,
                "end_time": 20.0,
                "duration": 8.0,
                "stt_text": "Like và subscribe nhé!",
                "ocr_text": "@user123 #cooking",
                "stt_segments": [],
                "ocr_items": []
            }
        ],
        "scenes": [
            {"scene_id": 0, "start_time": 0.0, "end_time": 5.0, "duration": 5.0},
            {"scene_id": 1, "start_time": 5.0, "end_time": 12.0, "duration": 7.0},
            {"scene_id": 2, "start_time": 12.0, "end_time": 20.0, "duration": 8.0},
        ],
        "stt_quality": "good",
        "ocr_quality": "medium",
        "data_status": "valid",
        "source_metadata": {"video_duration": 20}
    }
    
    result = process_phase3(mock_phase2)
    
    print(f"\n📊 Full Result:")
    print(f"   Success: {result['success']}")
    print(f"   Reasoning ready: {result['reasoning_ready']}")
    print(f"   Content chunks: {len(result.get('content_chunks', []))}")
    
    if result.get("normalized_text"):
        print(f"\n📝 Normalized Text:")
        print(result["normalized_text"][:500])
