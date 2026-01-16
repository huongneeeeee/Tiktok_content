# services/reasoning_checker.py
"""
Phase 3 - Step 3.7: Reasoning Readiness Check

Features:
- Kiểm tra nội dung có đủ rõ để AI suy luận không
- Gán flag reasoning_ready = True/False
- Đánh giá content_quality tổng thể
- Đề xuất hành động nếu chưa sẵn sàng
"""

from typing import Dict, List, Optional


# ============================================================
# REASONING CRITERIA
# ============================================================

# Minimum thresholds
MIN_WORD_COUNT = 5          # Tối thiểu 5 từ có nghĩa
MIN_CHUNK_WITH_CONTENT = 1  # Ít nhất 1 chunk có nội dung
MIN_CONTENT_DENSITY = 0.3   # 30% chunks phải có content


def assess_content_completeness(content_chunks: List[Dict]) -> Dict:
    """
    Đánh giá độ đầy đủ của nội dung.
    
    Returns:
    {
        "is_complete": bool,
        "word_count": int,
        "chunks_with_content": int,
        "content_density": float,
        "issues": [...]
    }
    """
    if not content_chunks:
        return {
            "is_complete": False,
            "word_count": 0,
            "chunks_with_content": 0,
            "content_density": 0.0,
            "issues": ["no_chunks"]
        }
    
    issues = []
    
    # Count words across all chunks
    total_words = 0
    chunks_with_content = 0
    
    for chunk in content_chunks:
        final_text = chunk.get("final_text", "") or chunk.get("cleaned_text", "")
        if final_text:
            words = len(final_text.split())
            total_words += words
            if words >= 3:  # At least 3 words to count as "has content"
                chunks_with_content += 1
    
    content_density = chunks_with_content / len(content_chunks) if content_chunks else 0
    
    # Check minimums
    if total_words < MIN_WORD_COUNT:
        issues.append("too_few_words")
    
    if chunks_with_content < MIN_CHUNK_WITH_CONTENT:
        issues.append("no_chunks_with_content")
    
    if content_density < MIN_CONTENT_DENSITY:
        issues.append("low_content_density")
    
    is_complete = len(issues) == 0
    
    return {
        "is_complete": is_complete,
        "word_count": total_words,
        "chunks_with_content": chunks_with_content,
        "total_chunks": len(content_chunks),
        "content_density": round(content_density, 2),
        "issues": issues
    }


def assess_content_coherence(content_chunks: List[Dict]) -> Dict:
    """
    Đánh giá tính mạch lạc của nội dung.
    
    Returns:
    {
        "is_coherent": bool,
        "has_structure": bool,
        "confidence_distribution": dict,
        "issues": [...]
    }
    """
    if not content_chunks:
        return {
            "is_coherent": False,
            "has_structure": False,
            "confidence_distribution": {},
            "issues": ["no_chunks"]
        }
    
    issues = []
    
    # Check content confidence distribution
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    
    for chunk in content_chunks:
        conf = chunk.get("content_confidence", "low")
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
    
    # Check if mostly low confidence
    total = len(content_chunks)
    low_ratio = confidence_counts.get("low", 0) / total if total > 0 else 1.0
    
    if low_ratio > 0.8:
        issues.append("mostly_low_confidence")
    
    # Check for structure (multiple scenes with content)
    has_structure = len(content_chunks) > 1 and confidence_counts.get("high", 0) + confidence_counts.get("medium", 0) > 0
    
    if not has_structure:
        issues.append("no_clear_structure")
    
    is_coherent = len(issues) == 0
    
    return {
        "is_coherent": is_coherent,
        "has_structure": has_structure,
        "confidence_distribution": confidence_counts,
        "low_confidence_ratio": round(low_ratio, 2),
        "issues": issues
    }


def assess_reasoning_potential(content_chunks: List[Dict]) -> Dict:
    """
    Đánh giá khả năng AI có thể suy luận từ nội dung.
    
    Checks:
    - Can we understand the topic?
    - Is there enough context?
    - Are there actionable insights?
    """
    if not content_chunks:
        return {
            "can_reason": False,
            "topic_clarity": "none",
            "context_level": "none",
            "issues": ["no_content"]
        }
    
    issues = []
    
    # Collect all text
    all_text = ""
    for chunk in content_chunks:
        text = chunk.get("final_text", "") or chunk.get("cleaned_text", "")
        if text:
            all_text += " " + text
    
    all_text = all_text.strip()
    word_count = len(all_text.split())
    
    # Topic clarity
    if word_count >= 20:
        topic_clarity = "clear"
    elif word_count >= 10:
        topic_clarity = "partial"
    elif word_count >= 5:
        topic_clarity = "vague"
    else:
        topic_clarity = "none"
        issues.append("topic_unclear")
    
    # Context level
    chunks_with_context = sum(1 for c in content_chunks 
                             if len((c.get("final_text", "") or "").split()) >= 5)
    
    if chunks_with_context >= 3:
        context_level = "rich"
    elif chunks_with_context >= 2:
        context_level = "adequate"
    elif chunks_with_context >= 1:
        context_level = "minimal"
    else:
        context_level = "none"
        issues.append("no_context")
    
    can_reason = topic_clarity in ["clear", "partial"] and context_level in ["rich", "adequate", "minimal"]
    
    return {
        "can_reason": can_reason,
        "topic_clarity": topic_clarity,
        "context_level": context_level,
        "total_words": word_count,
        "issues": issues
    }


# ============================================================
# MAIN CHECK
# ============================================================

def check_reasoning_ready(content_chunks: List[Dict], quality_data: Dict = None) -> Dict:
    """
    Kiểm tra tổng hợp: nội dung có đủ rõ để AI suy luận không?
    
    Args:
        content_chunks: Processed chunks from content pipeline
        quality_data: Quality info from Phase 2 (stt_quality, ocr_quality, data_status)
    
    Returns:
    {
        "reasoning_ready": True | False,
        "reason": str,
        "content_quality": "high" | "medium" | "low",
        "assessments": {
            "completeness": {...},
            "coherence": {...},
            "reasoning_potential": {...}
        },
        "recommended_actions": [...]
    }
    """
    if quality_data is None:
        quality_data = {}
    
    # Run all assessments
    completeness = assess_content_completeness(content_chunks)
    coherence = assess_content_coherence(content_chunks)
    reasoning = assess_reasoning_potential(content_chunks)
    
    # Collect all issues
    all_issues = (
        completeness.get("issues", []) +
        coherence.get("issues", []) +
        reasoning.get("issues", [])
    )
    
    # Check data_status from Phase 2
    data_status = quality_data.get("data_status", "valid")
    
    # Decision logic
    reasoning_ready = True
    reasons = []
    
    # Critical failures
    if not completeness["is_complete"]:
        reasoning_ready = False
        reasons.append("Content không đủ đầy đủ")
    
    if not reasoning["can_reason"]:
        reasoning_ready = False
        reasons.append("Không đủ context để suy luận")
    
    # Soft failures (warning but may proceed)
    if data_status == "weak" and not completeness["is_complete"]:
        reasoning_ready = False
        reasons.append("Dữ liệu yếu từ Phase 2")
    
    # Content quality
    issue_count = len(all_issues)
    
    if issue_count == 0:
        content_quality = "high"
    elif issue_count <= 2:
        content_quality = "medium"
    else:
        content_quality = "low"
    
    # Generate reason string
    if reasoning_ready:
        reason = "Nội dung đủ rõ ràng và có cấu trúc để AI suy luận"
    else:
        reason = "; ".join(reasons) if reasons else "Nội dung không đủ điều kiện"
    
    # Recommended actions
    recommended_actions = []
    
    if not reasoning_ready:
        if "too_few_words" in all_issues:
            recommended_actions.append("Giữ nguyên nội dung, không ép phân loại")
        if "topic_unclear" in all_issues:
            recommended_actions.append("Chỉ sử dụng metadata để phân loại")
        if "mostly_low_confidence" in all_issues:
            recommended_actions.append("Đánh dấu low-confidence, hạn chế suy luận")
    
    if not recommended_actions:
        if reasoning_ready:
            recommended_actions.append("Tiếp tục Phase tiếp theo (classification, scripting)")
        else:
            recommended_actions.append("Giữ metadata và scene structure, bỏ qua deep analysis")
    
    print(f"   📊 [REASONING] Ready: {reasoning_ready}")
    print(f"   📊 [REASONING] Quality: {content_quality}")
    if all_issues:
        print(f"   ⚠️ [REASONING] Issues: {', '.join(all_issues[:5])}")
    
    return {
        "reasoning_ready": reasoning_ready,
        "reason": reason,
        "content_quality": content_quality,
        "assessments": {
            "completeness": completeness,
            "coherence": coherence,
            "reasoning_potential": reasoning
        },
        "all_issues": all_issues,
        "recommended_actions": recommended_actions
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Reasoning Checker Test")
    print("=" * 60)
    
    # Test case 1: Good content
    print("\n📍 Test 1: Good content")
    good_chunks = [
        {"final_text": "Hôm nay mình sẽ hướng dẫn các bạn làm bánh.", "content_confidence": "high"},
        {"final_text": "Bước 1 là chuẩn bị nguyên liệu gồm bột và trứng.", "content_confidence": "high"},
        {"final_text": "Bước 2 là trộn đều và nướng trong 30 phút.", "content_confidence": "medium"},
    ]
    
    result1 = check_reasoning_ready(good_chunks, {"data_status": "valid"})
    print(f"   Ready: {result1['reasoning_ready']}")
    print(f"   Quality: {result1['content_quality']}")
    
    # Test case 2: Poor content
    print("\n📍 Test 2: Poor content")
    poor_chunks = [
        {"final_text": "Hi", "content_confidence": "low"},
        {"final_text": "", "content_confidence": "low"},
    ]
    
    result2 = check_reasoning_ready(poor_chunks, {"data_status": "weak"})
    print(f"   Ready: {result2['reasoning_ready']}")
    print(f"   Quality: {result2['content_quality']}")
    print(f"   Reason: {result2['reason']}")
    
    # Test case 3: Mixed
    print("\n📍 Test 3: Mixed content")
    mixed_chunks = [
        {"final_text": "Một video về nấu ăn đơn giản.", "content_confidence": "medium"},
        {"final_text": "", "content_confidence": "low"},
    ]
    
    result3 = check_reasoning_ready(mixed_chunks, {"data_status": "valid"})
    print(f"   Ready: {result3['reasoning_ready']}")
    print(f"   Quality: {result3['content_quality']}")
