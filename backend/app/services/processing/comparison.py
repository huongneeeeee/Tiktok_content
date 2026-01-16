# services/content_comparator.py
"""
Phase 3 - Step 3.3 & 3.4: STT/OCR Comparison & Source Prioritization

Features:
- So sánh semantic giữa STT và OCR
- Phát hiện: reinforce, complement, conflict, independent
- Chọn nguồn nội dung đáng tin hơn
- Gán trọng số cho mỗi nguồn
"""

import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


# ============================================================
# TEXT SIMILARITY
# ============================================================

def normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison (lowercase, remove punctuation)"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts.
    Returns 0.0 to 1.0
    """
    if not text1 or not text2:
        return 0.0
    
    norm1 = normalize_for_comparison(text1)
    norm2 = normalize_for_comparison(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Use SequenceMatcher for similarity
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    return round(similarity, 3)


def find_common_keywords(text1: str, text2: str, min_word_len: int = 3) -> List[str]:
    """Find common keywords between two texts"""
    if not text1 or not text2:
        return []
    
    words1 = set(w.lower() for w in text1.split() if len(w) >= min_word_len)
    words2 = set(w.lower() for w in text2.split() if len(w) >= min_word_len)
    
    common = words1 & words2
    return list(common)


# ============================================================
# STT/OCR COMPARISON
# ============================================================

def compare_stt_ocr(stt_text: str, ocr_text: str) -> Dict:
    """
    So sánh ngữ nghĩa giữa STT (audio) và OCR (visual).
    
    Relations:
    - reinforce: Cùng nội dung, củng cố lẫn nhau
    - complement: Bổ sung cho nhau (STT nói, OCR hiển thị khác)
    - conflict: Mâu thuẫn nhau
    - independent: Không liên quan
    
    Returns:
    {
        "relation": "reinforce" | "complement" | "conflict" | "independent",
        "similarity_score": 0.0-1.0,
        "common_keywords": [...],
        "confidence": "high" | "medium" | "low",
        "explanation": str
    }
    """
    # Handle empty cases
    if not stt_text and not ocr_text:
        return {
            "relation": "independent",
            "similarity_score": 0.0,
            "common_keywords": [],
            "confidence": "low",
            "explanation": "Both STT and OCR are empty"
        }
    
    if not stt_text:
        return {
            "relation": "independent",
            "similarity_score": 0.0,
            "common_keywords": [],
            "confidence": "medium",
            "explanation": "Only OCR available, no STT to compare"
        }
    
    if not ocr_text:
        return {
            "relation": "independent",
            "similarity_score": 0.0,
            "common_keywords": [],
            "confidence": "medium",
            "explanation": "Only STT available, no OCR to compare"
        }
    
    # Calculate similarity
    similarity = calculate_text_similarity(stt_text, ocr_text)
    common_keywords = find_common_keywords(stt_text, ocr_text)
    
    # Determine relation
    if similarity >= 0.6:
        # High similarity - reinforce
        relation = "reinforce"
        confidence = "high"
        explanation = f"STT and OCR have high similarity ({similarity:.0%}), content reinforces each other"
    elif similarity >= 0.3 or len(common_keywords) >= 3:
        # Medium similarity with common keywords - complement
        relation = "complement"
        confidence = "medium"
        explanation = f"STT and OCR share keywords ({len(common_keywords)}), complementing each other"
    elif similarity >= 0.1:
        # Low similarity but some overlap - might be conflict or complement
        # Check if they're talking about completely different things
        if len(common_keywords) >= 1:
            relation = "complement"
            confidence = "low"
            explanation = f"Low similarity ({similarity:.0%}), but some common keywords found"
        else:
            relation = "independent"
            confidence = "low"
            explanation = f"Very low similarity ({similarity:.0%}), sources appear independent"
    else:
        # No similarity
        relation = "independent"
        confidence = "low"
        explanation = "STT and OCR have no meaningful overlap, treating as independent sources"
    
    return {
        "relation": relation,
        "similarity_score": similarity,
        "common_keywords": common_keywords,
        "confidence": confidence,
        "explanation": explanation
    }


# ============================================================
# SOURCE PRIORITIZATION
# ============================================================

def calculate_information_density(text: str) -> float:
    """
    Calculate information density of text.
    Higher = more meaningful content.
    """
    if not text:
        return 0.0
    
    words = text.split()
    word_count = len(words)
    
    if word_count == 0:
        return 0.0
    
    # Factors:
    # - Unique words ratio (more unique = more info)
    unique_words = set(w.lower() for w in words)
    uniqueness = len(unique_words) / word_count
    
    # - Average word length (longer words often = more specific)
    avg_word_len = sum(len(w) for w in words) / word_count
    word_len_factor = min(avg_word_len / 6, 1.0)  # Normalize to 0-1
    
    # - Length bonus (more content = more potential info)
    length_factor = min(word_count / 50, 1.0)  # Cap at 50 words
    
    density = (uniqueness * 0.4 + word_len_factor * 0.3 + length_factor * 0.3)
    
    return round(density, 3)


def prioritize_source(
    stt_text: str,
    ocr_text: str,
    stt_quality: str,
    ocr_quality: str,
    comparison: Dict = None
) -> Dict:
    """
    Quyết định nguồn nội dung chính dựa trên chất lượng và mật độ thông tin.
    
    Rules:
    - STT tốt, OCR nhiễu → Ưu tiên STT
    - OCR rõ, STT yếu → Ưu tiên OCR
    - Cả hai tốt + reinforce → Merge với STT làm chính
    - Cả hai yếu → Không suy diễn
    
    Returns:
    {
        "primary_source": "stt" | "ocr" | "merged" | "none",
        "primary_text": str,
        "secondary_text": str,
        "weight": {"stt": float, "ocr": float},
        "reason": str,
        "content_confidence": "high" | "medium" | "low"
    }
    """
    if comparison is None:
        comparison = compare_stt_ocr(stt_text, ocr_text)
    
    # Calculate densities
    stt_density = calculate_information_density(stt_text)
    ocr_density = calculate_information_density(ocr_text)
    
    # Quality scores
    quality_score = {"good": 1.0, "low": 0.3}
    stt_q = quality_score.get(stt_quality, 0.5)
    ocr_q = quality_score.get(ocr_quality, 0.5)
    
    # Combined scores
    stt_score = stt_q * 0.6 + stt_density * 0.4
    ocr_score = ocr_q * 0.6 + ocr_density * 0.4
    
    relation = comparison.get("relation", "independent")
    
    # Decision logic
    if not stt_text and not ocr_text:
        return {
            "primary_source": "none",
            "primary_text": "",
            "secondary_text": "",
            "weight": {"stt": 0.0, "ocr": 0.0},
            "reason": "No content available from either source",
            "content_confidence": "low"
        }
    
    # Case: Both sources reinforce each other
    if relation == "reinforce":
        # Use STT as primary (spoken word is usually more complete)
        stt_weight = 0.6
        ocr_weight = 0.4
        
        return {
            "primary_source": "merged",
            "primary_text": stt_text,
            "secondary_text": ocr_text,
            "weight": {"stt": stt_weight, "ocr": ocr_weight},
            "reason": "STT and OCR reinforce each other, using merged content",
            "content_confidence": "high"
        }
    
    # Case: Sources complement each other
    if relation == "complement":
        if stt_score >= ocr_score:
            return {
                "primary_source": "merged",
                "primary_text": stt_text,
                "secondary_text": ocr_text,
                "weight": {"stt": 0.5, "ocr": 0.5},
                "reason": "Sources complement each other, merging with equal weight",
                "content_confidence": "medium"
            }
        else:
            return {
                "primary_source": "merged",
                "primary_text": ocr_text,
                "secondary_text": stt_text,
                "weight": {"stt": 0.4, "ocr": 0.6},
                "reason": "OCR stronger, using as primary with STT support",
                "content_confidence": "medium"
            }
    
    # Case: Independent sources - choose the stronger one
    if stt_score > ocr_score and stt_text:
        if stt_quality == "low":
            confidence = "low"
        else:
            confidence = "medium"
        
        return {
            "primary_source": "stt",
            "primary_text": stt_text,
            "secondary_text": ocr_text,
            "weight": {"stt": 0.8, "ocr": 0.2},
            "reason": f"STT has higher score ({stt_score:.2f} vs {ocr_score:.2f})",
            "content_confidence": confidence
        }
    elif ocr_text:
        if ocr_quality == "low":
            confidence = "low"
        else:
            confidence = "medium"
        
        return {
            "primary_source": "ocr",
            "primary_text": ocr_text,
            "secondary_text": stt_text,
            "weight": {"stt": 0.2, "ocr": 0.8},
            "reason": f"OCR has higher score ({ocr_score:.2f} vs {stt_score:.2f})",
            "content_confidence": confidence
        }
    
    # Fallback
    return {
        "primary_source": "stt" if stt_text else "ocr",
        "primary_text": stt_text or ocr_text,
        "secondary_text": ocr_text if stt_text else stt_text,
        "weight": {"stt": 0.5, "ocr": 0.5},
        "reason": "Using available source as primary",
        "content_confidence": "low"
    }


def process_chunk_comparison(
    chunk: Dict,
    stt_quality: str,
    ocr_quality: str
) -> Dict:
    """
    Process comparison for a single content chunk.
    Adds comparison and prioritization results to chunk.
    """
    stt_text = chunk.get("stt_text", "")
    ocr_text = chunk.get("ocr_text", "")
    
    # Compare
    comparison = compare_stt_ocr(stt_text, ocr_text)
    
    # Prioritize
    priority = prioritize_source(stt_text, ocr_text, stt_quality, ocr_quality, comparison)
    
    return {
        **chunk,
        "comparison": comparison,
        "priority": priority,
        "content_confidence": priority["content_confidence"]
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Content Comparator Test")
    print("=" * 60)
    
    # Test case 1: Reinforce
    print("\n📍 Test 1: Reinforce")
    stt1 = "Hôm nay mình sẽ hướng dẫn làm bánh"
    ocr1 = "Hướng dẫn làm bánh ngon"
    result1 = compare_stt_ocr(stt1, ocr1)
    print(f"   Relation: {result1['relation']}")
    print(f"   Similarity: {result1['similarity_score']:.0%}")
    
    # Test case 2: Complement
    print("\n📍 Test 2: Complement")
    stt2 = "Xin chào các bạn, hôm nay mình..."
    ocr2 = "Bước 1: Chuẩn bị nguyên liệu"
    result2 = compare_stt_ocr(stt2, ocr2)
    print(f"   Relation: {result2['relation']}")
    print(f"   Similarity: {result2['similarity_score']:.0%}")
    
    # Test case 3: Independent
    print("\n📍 Test 3: Independent")
    stt3 = "Nhạc vui vẻ"
    ocr3 = "Follow @user123"
    result3 = compare_stt_ocr(stt3, ocr3)
    print(f"   Relation: {result3['relation']}")
    print(f"   Similarity: {result3['similarity_score']:.0%}")
    
    # Test prioritization
    print("\n📍 Test 4: Prioritization")
    priority = prioritize_source(stt1, ocr1, "good", "good", result1)
    print(f"   Primary source: {priority['primary_source']}")
    print(f"   Weight: STT={priority['weight']['stt']}, OCR={priority['weight']['ocr']}")
    print(f"   Confidence: {priority['content_confidence']}")
