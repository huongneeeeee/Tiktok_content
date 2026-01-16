# services/content_cleaner.py
"""
Phase 3 - Step 3.5 & 3.6: Content Cleaning & Language Normalization

Features:
- Loại bỏ filler words, noise, câu vô nghĩa
- Chuẩn hóa ngôn ngữ nhẹ (không rewrite)
- Giữ giọng nguyên bản
- Gộp câu rời rạc
"""

import re
from typing import List, Dict, Tuple


# ============================================================
# FILLER & NOISE PATTERNS
# ============================================================

# Vietnamese fillers
FILLER_VI = [
    r'\bừm+\b', r'\bà+\b', r'\bờ+\b', r'\bê+\b',
    r'\bthì\s+là\b', r'\bcũng\s+là\b',
    r'\bthật\s+ra\s+là\b', r'\bnói\s+chung\s+là\b',
    r'\bcơ\s+bản\s+là\b', r'\bý\s+là\b',
    r'\bđại\s+loại\b', r'\bkiểu\s+như\b',
]

# English fillers
FILLER_EN = [
    r'\bum+\b', r'\buh+\b', r'\bahm+\b', r'\bhmm+\b',
    r'\byou know\b', r'\blike\b(?!s?\b)',  # Avoid matching "likes"
    r'\bbasically\b', r'\bactually\b',
    r'\bi mean\b', r'\bkind of\b', r'\bsort of\b',
]

# Social media / CTA noise
NOISE_PATTERNS = [
    r'subscribe', r'like\s+and\s+share', r'follow\s+me',
    r'link\s+in\s+bio', r'comment\s+below', r'check\s+out',
    r'đăng\s+ký', r'theo\s+dõi', r'like\s+ủng\s+hộ',
    r'nhấn\s+like', r'bấm\s+subscribe', r'xem\s+thêm',
    r'mô\s+tả\s+bên\s+dưới', r'link\s+dưới\s+comment',
    r'@\w+',  # @mentions
    r'#\w{2,}',  # #hashtags (keep if > 2 chars for context sometimes)
]

# Watermarks and platform names
WATERMARK_PATTERNS = [
    r'tiktok', r'douyin', r'capcut', r'inshot',
    r'♬', r'🎵', r'🎶',
    r'original\s+sound', r'âm\s+thanh\s+gốc',
]

# Random characters / meaningless
MEANINGLESS_PATTERNS = [
    r'^[^\w\s]+$',  # Only special chars
    r'^\d+:\d+$',   # Timestamps like 0:15
    r'^\d+[km]$',   # View counts like 100k
    r'^[a-z]{1,2}$',  # Single/double letters
]


def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compile regex patterns with case insensitivity"""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


FILLER_REGEX = compile_patterns(FILLER_VI + FILLER_EN)
NOISE_REGEX = compile_patterns(NOISE_PATTERNS)
WATERMARK_REGEX = compile_patterns(WATERMARK_PATTERNS)
MEANINGLESS_REGEX = compile_patterns(MEANINGLESS_PATTERNS)


# ============================================================
# CONTENT CLEANING
# ============================================================

def remove_fillers(text: str) -> str:
    """Remove filler words while preserving sentence structure"""
    if not text:
        return ""
    
    result = text
    for pattern in FILLER_REGEX:
        result = pattern.sub('', result)
    
    # Clean up extra spaces
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def remove_noise(text: str) -> str:
    """Remove social media noise and CTAs"""
    if not text:
        return ""
    
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if entire line is noise
        is_noise = False
        line_lower = line.lower()
        
        for pattern in NOISE_REGEX:
            if pattern.search(line_lower):
                # If noise is > 50% of line, skip it
                match = pattern.search(line_lower)
                if match and len(match.group()) > len(line) * 0.5:
                    is_noise = True
                    break
        
        if not is_noise:
            # Remove inline noise
            for pattern in NOISE_REGEX:
                line = pattern.sub('', line)
            line = line.strip()
            if line:
                clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def remove_watermarks(text: str) -> str:
    """Remove watermarks and platform names"""
    if not text:
        return ""
    
    result = text
    for pattern in WATERMARK_REGEX:
        result = pattern.sub('', result)
    
    return re.sub(r'\s+', ' ', result).strip()


def remove_meaningless(text: str) -> str:
    """Remove meaningless lines"""
    if not text:
        return ""
    
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line is meaningless
        is_meaningless = False
        for pattern in MEANINGLESS_REGEX:
            if pattern.match(line):
                is_meaningless = True
                break
        
        # Also skip very short lines (< 3 chars)
        if len(line) < 3:
            is_meaningless = True
        
        if not is_meaningless:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def clean_content(text: str) -> str:
    """
    Full content cleaning pipeline.
    Removes: fillers, noise, watermarks, meaningless content.
    """
    if not text:
        return ""
    
    result = text
    
    # Step 1: Remove watermarks
    result = remove_watermarks(result)
    
    # Step 2: Remove noise/CTAs
    result = remove_noise(result)
    
    # Step 3: Remove fillers
    result = remove_fillers(result)
    
    # Step 4: Remove meaningless
    result = remove_meaningless(result)
    
    # Final cleanup
    result = re.sub(r'\n\s*\n', '\n', result)  # Remove empty lines
    result = re.sub(r'\s+', ' ', result.replace('\n', ' [SEP] ')).strip()
    result = result.replace(' [SEP] ', '\n')
    
    return result


# ============================================================
# LANGUAGE NORMALIZATION
# ============================================================

def merge_fragmented_sentences(text: str) -> str:
    """
    Gộp các câu rời rạc thành câu hoàn chỉnh.
    Nhẹ nhàng, không rewrite sáng tạo.
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    
    if len(lines) <= 1:
        return text
    
    merged = []
    buffer = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line starts with lowercase (continuation)
        if buffer and line[0].islower():
            buffer += " " + line
        # Check if previous buffer doesn't end with sentence ender
        elif buffer and not re.search(r'[.!?:。]$', buffer):
            buffer += ". " + line
        else:
            if buffer:
                merged.append(buffer)
            buffer = line
    
    if buffer:
        merged.append(buffer)
    
    return '\n'.join(merged)


def fix_common_errors(text: str) -> str:
    """
    Sửa lỗi phổ biến nhẹ.
    Không thay đổi ý nghĩa.
    """
    if not text:
        return ""
    
    result = text
    
    # Fix multiple spaces
    result = re.sub(r'\s+', ' ', result)
    
    # Fix space before punctuation
    result = re.sub(r'\s+([.,!?:;])', r'\1', result)
    
    # Fix missing space after punctuation
    result = re.sub(r'([.,!?:;])([A-Za-zÀ-ỹ])', r'\1 \2', result)
    
    # Capitalize first letter of sentences
    sentences = re.split(r'([.!?]\s+)', result)
    result = ''
    for i, part in enumerate(sentences):
        if i % 2 == 0 and part:
            # Sentence content
            part = part.strip()
            if part:
                part = part[0].upper() + part[1:] if len(part) > 1 else part.upper()
        result += part
    
    return result.strip()


def normalize_language(text: str) -> str:
    """
    Full language normalization pipeline.
    Giữ giọng nguyên bản, chỉ chuẩn hóa nhẹ.
    """
    if not text:
        return ""
    
    # Step 1: Merge fragmented sentences
    result = merge_fragmented_sentences(text)
    
    # Step 2: Fix common errors
    result = fix_common_errors(result)
    
    return result


# ============================================================
# FULL PROCESSING
# ============================================================

def process_text_full(text: str) -> Dict:
    """
    Full text processing: clean + normalize.
    
    Returns:
    {
        "original": str,
        "cleaned": str,
        "normalized": str,
        "removed_count": int,
        "final_word_count": int
    }
    """
    if not text:
        return {
            "original": "",
            "cleaned": "",
            "normalized": "",
            "removed_count": 0,
            "final_word_count": 0
        }
    
    original_words = len(text.split())
    
    # Clean
    cleaned = clean_content(text)
    
    # Normalize
    normalized = normalize_language(cleaned)
    
    final_words = len(normalized.split())
    removed = original_words - final_words
    
    return {
        "original": text,
        "cleaned": cleaned,
        "normalized": normalized,
        "removed_count": max(0, removed),
        "final_word_count": final_words
    }


def process_chunk_content(chunk: Dict) -> Dict:
    """
    Process content in a chunk (from content_aligner).
    Cleans and normalizes both STT and OCR.
    """
    priority = chunk.get("priority", {})
    primary_source = priority.get("primary_source", "stt")
    primary_text = priority.get("primary_text", "")
    secondary_text = priority.get("secondary_text", "")
    
    # Process primary text
    primary_result = process_text_full(primary_text)
    
    # Process secondary text (lighter processing)
    secondary_cleaned = clean_content(secondary_text)
    
    # Determine final text
    if primary_source == "merged":
        # Combine: primary + context from secondary
        final_text = primary_result["normalized"]
        if secondary_cleaned and secondary_cleaned not in final_text:
            final_text += f"\n[Context: {secondary_cleaned[:100]}]"
    else:
        final_text = primary_result["normalized"]
    
    return {
        **chunk,
        "cleaned_text": primary_result["normalized"],
        "final_text": final_text,
        "processing_stats": {
            "original_words": len(primary_text.split()) if primary_text else 0,
            "final_words": primary_result["final_word_count"],
            "removed_words": primary_result["removed_count"]
        }
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Content Cleaner Test")
    print("=" * 60)
    
    # Test Vietnamese
    test_vi = """
    Ừm, xin chào các bạn, thì là hôm nay mình sẽ hướng dẫn.
    Like và subscribe nhé!
    Bước 1 là chuẩn bị nguyên liệu.
    @user123 #cooking #viral
    TikTok
    """
    
    print("\n📍 Original Vietnamese:")
    print(test_vi)
    
    result = process_text_full(test_vi)
    print("\n📍 Cleaned & Normalized:")
    print(result["normalized"])
    print(f"\n📊 Removed {result['removed_count']} words")
    
    # Test English
    test_en = """
    Um, you know, basically today I'm gonna show you.
    Like and subscribe!
    Step 1 is preparing ingredients.
    Link in bio!
    """
    
    print("\n" + "=" * 40)
    print("\n📍 Original English:")
    print(test_en)
    
    result2 = process_text_full(test_en)
    print("\n📍 Cleaned & Normalized:")
    print(result2["normalized"])
