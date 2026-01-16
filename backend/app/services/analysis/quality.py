# services/quality_assessor.py
"""
Phase 2 - Global Quality Decision

Features:
- Assess overall data quality
- Determine data_status (valid/weak)
- Recommend processing approach for Phase 3+
"""

from typing import Dict, List


def assess_global_quality(stt_result: Dict, ocr_result: Dict) -> Dict:
    """
    Assess global quality based on STT and OCR results.
    
    Decision logic:
    - If BOTH stt_quality AND ocr_quality are "low" -> data_status = "weak"
    - Otherwise -> data_status = "valid"
    
    Args:
        stt_result: Output from stt_processor
        ocr_result: Output from ocr_processor_v2
    
    Returns:
    {
        "data_status": "valid" | "weak",
        "stt_quality": "good" | "low",
        "ocr_quality": "good" | "low",
        "usable_sources": ["stt", "ocr"] or ["metadata_only"],
        "primary_source": "stt" | "ocr" | "both" | "none",
        "recommendation": str,
        "quality_summary": str
    }
    """
    stt_quality = stt_result.get("stt_quality", "low")
    ocr_quality = ocr_result.get("ocr_quality", "low")
    
    # Check what's usable
    usable_sources = []
    
    if stt_quality == "good":
        usable_sources.append("stt")
    
    if ocr_quality == "good":
        usable_sources.append("ocr")
    
    # Determine primary source
    if "stt" in usable_sources and "ocr" in usable_sources:
        primary_source = "both"
    elif "stt" in usable_sources:
        primary_source = "stt"
    elif "ocr" in usable_sources:
        primary_source = "ocr"
    else:
        primary_source = "none"
        usable_sources = ["metadata_only"]
    
    # Global status decision
    # WEAK only if BOTH are low quality
    if stt_quality == "low" and ocr_quality == "low":
        data_status = "weak"
        recommendation = "Limited analysis - use metadata, scene structure, and any available text"
        quality_summary = "Both STT and OCR returned low quality. Analysis will be limited."
    else:
        data_status = "valid"
        
        if primary_source == "both":
            recommendation = "Full multimodal analysis with STT and OCR"
            quality_summary = "Both STT and OCR are usable for comprehensive analysis."
        elif primary_source == "stt":
            recommendation = "Focus on audio/speech analysis, supplement with OCR where available"
            quality_summary = "Good STT quality. OCR is weak - prioritize spoken content analysis."
        elif primary_source == "ocr":
            recommendation = "Focus on visual/text analysis, supplement with STT where available"
            quality_summary = "Good OCR quality. STT is weak - prioritize on-screen text analysis."
        else:
            recommendation = "Metadata-only analysis"
            quality_summary = "No usable content sources."
    
    # Collect all issues
    stt_issues = stt_result.get("quality_metrics", {}).get("issues", [])
    ocr_issues = ocr_result.get("quality_metrics", {}).get("issues", [])
    all_issues = stt_issues + ocr_issues
    
    # Generate detailed metrics
    stt_metrics = stt_result.get("quality_metrics", {})
    ocr_metrics = ocr_result.get("quality_metrics", {})
    
    print(f"   📊 [QUALITY] Global assessment: {data_status}")
    print(f"   📊 [QUALITY] STT: {stt_quality}, OCR: {ocr_quality}")
    print(f"   📊 [QUALITY] Primary source: {primary_source}")
    
    return {
        "data_status": data_status,
        "stt_quality": stt_quality,
        "ocr_quality": ocr_quality,
        "usable_sources": usable_sources,
        "primary_source": primary_source,
        "recommendation": recommendation,
        "quality_summary": quality_summary,
        "all_issues": all_issues,
        "metrics": {
            "stt": stt_metrics,
            "ocr": ocr_metrics
        }
    }


def get_content_richness_score(
    stt_result: Dict, 
    ocr_result: Dict,
    merged_data: Dict = None
) -> Dict:
    """
    Calculate a content richness score for the video.
    Useful for prioritizing which videos to analyze in depth.
    
    Returns:
    {
        "score": 0-100,
        "level": "high" | "medium" | "low",
        "factors": {...}
    }
    """
    score = 0
    factors = {}
    
    # STT factors (up to 50 points)
    stt_metrics = stt_result.get("quality_metrics", {})
    word_count = stt_metrics.get("word_count", 0)
    
    if word_count > 100:
        stt_score = 50
    elif word_count > 50:
        stt_score = 40
    elif word_count > 20:
        stt_score = 30
    elif word_count > 10:
        stt_score = 20
    elif word_count > 5:
        stt_score = 10
    else:
        stt_score = 0
    
    factors["stt_word_count"] = word_count
    factors["stt_score"] = stt_score
    score += stt_score
    
    # OCR factors (up to 50 points)
    ocr_metrics = ocr_result.get("quality_metrics", {})
    char_count = ocr_metrics.get("total_chars", 0)
    
    if char_count > 200:
        ocr_score = 50
    elif char_count > 100:
        ocr_score = 40
    elif char_count > 50:
        ocr_score = 30
    elif char_count > 20:
        ocr_score = 20
    elif char_count > 10:
        ocr_score = 10
    else:
        ocr_score = 0
    
    factors["ocr_char_count"] = char_count
    factors["ocr_score"] = ocr_score
    score += ocr_score
    
    # Determine level
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"
    
    return {
        "score": score,
        "level": level,
        "factors": factors
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Quality Assessor Test")
    print("=" * 60)
    
    # Test case 1: Both good
    mock_stt_good = {"stt_quality": "good", "quality_metrics": {"word_count": 50, "issues": []}}
    mock_ocr_good = {"ocr_quality": "good", "quality_metrics": {"total_chars": 100, "issues": []}}
    
    result1 = assess_global_quality(mock_stt_good, mock_ocr_good)
    print(f"\n✅ Both Good: {result1['data_status']} - {result1['recommendation']}")
    
    # Test case 2: Both low
    mock_stt_low = {"stt_quality": "low", "quality_metrics": {"word_count": 2, "issues": ["very_few_words"]}}
    mock_ocr_low = {"ocr_quality": "low", "quality_metrics": {"total_chars": 3, "issues": ["almost_no_text"]}}
    
    result2 = assess_global_quality(mock_stt_low, mock_ocr_low)
    print(f"\n⚠️ Both Low: {result2['data_status']} - {result2['recommendation']}")
    
    # Test case 3: Mixed
    result3 = assess_global_quality(mock_stt_good, mock_ocr_low)
    print(f"\n🔄 Mixed (STT good, OCR low): {result3['data_status']} - {result3['recommendation']}")
    
    # Content richness
    richness = get_content_richness_score(mock_stt_good, mock_ocr_good)
    print(f"\n📈 Content Richness: {richness['score']}/100 ({richness['level']})")
