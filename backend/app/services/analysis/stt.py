# backend/app/services/analysis/stt.py
"""
Phase 2 - Audio Branch: STT Processor with Quality Assessment

Features:
- Transcribe video với timestamps (segment-level)
- Assess STT quality (good/low)
- Split long audio into chunks
- Handle videos without audio gracefully
"""

import os
import sys
import subprocess
import requests
import glob
import re
from typing import Dict, List, Optional

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Config


# ============================================================
# AUDIO EXTRACTION
# ============================================================

def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds using FFprobe"""
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{audio_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except:
        return 0.0


def extract_audio(video_path: str) -> Optional[str]:
    """
    Extract audio from video file as WAV (16kHz, mono).
    Returns path to audio file or None if failed.
    """
    if not os.path.exists(video_path):
        return None
    
    audio_path = video_path.replace(".mp4", "_audio.wav")
    
    # Skip if already exists
    if os.path.exists(audio_path):
        return audio_path
    
    cmd = f'ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}" -y'
    
    try:
        result = subprocess.run(
            cmd, shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            return audio_path
        
        # Check if video has no audio
        if "does not contain any stream" in result.stderr:
            print("   ⚠️ [STT] Video không có audio track")
            return None
            
        return None
        
    except subprocess.TimeoutExpired:
        print("   ⚠️ [STT] Audio extraction timeout")
        return None
    except Exception as e:
        print(f"   ⚠️ [STT] Audio extraction error: {e}")
        return None


def split_audio_chunks(audio_path: str, chunk_duration: int = 120) -> List[Dict]:
    """
    Split audio into chunks with timestamps.
    Returns list of {path, start_time, end_time}
    """
    duration = get_audio_duration(audio_path)
    if duration <= 0:
        return [{"path": audio_path, "start_time": 0.0, "end_time": 0.0}]
    
    # If short enough, no split needed
    if duration <= chunk_duration + 10:
        return [{"path": audio_path, "start_time": 0.0, "end_time": duration}]
    
    chunks = []
    base_path = audio_path.replace(".wav", "")
    num_chunks = int(duration / chunk_duration) + 1
    
    print(f"   📌 [STT] Audio dài {duration:.0f}s, chia thành {num_chunks} chunks...")
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        end_time = min((i + 1) * chunk_duration, duration)
        chunk_path = f"{base_path}_chunk_{i:03d}.wav"
        
        cmd = f'ffmpeg -i "{audio_path}" -ss {start_time} -t {chunk_duration} -acodec pcm_s16le -ar 16000 -ac 1 "{chunk_path}" -y'
        
        try:
            subprocess.run(cmd, shell=True, check=True, 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=30)
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 1000:
                chunks.append({
                    "path": chunk_path,
                    "start_time": start_time,
                    "end_time": end_time
                })
        except:
            pass
    
    return chunks if chunks else [{"path": audio_path, "start_time": 0.0, "end_time": duration}]


# ============================================================
# STT API CALL
# ============================================================

def transcribe_chunk(audio_path: str, timeout: int = 120) -> Dict:
    """
    Transcribe a single audio chunk.
    Returns {text, segments (if available)}
    """
    api_url = Config.STT_API_URL
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            response = requests.post(api_url, files=files, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "text": data.get("text", ""),
                "segments": data.get("segments", []),  # If API supports
                "success": True
            }
        else:
            return {"text": "", "segments": [], "success": False, "error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"text": "", "segments": [], "success": False, "error": "timeout"}
    except Exception as e:
        return {"text": "", "segments": [], "success": False, "error": str(e)}


# ============================================================
# QUALITY ASSESSMENT
# ============================================================

def assess_stt_quality(transcript: str, segments: List[Dict], audio_duration: float) -> Dict:
    """
    Assess STT quality based on various metrics.
    
    Returns:
    {
        "quality": "good" | "low",
        "metrics": {
            "word_count": int,
            "char_count": int,
            "words_per_second": float,
            "silence_ratio": float,
            "repetition_ratio": float,
            "issues": [...]
        }
    }
    """
    issues = []
    
    # Basic text analysis
    text = transcript.strip()
    words = text.split() if text else []
    word_count = len(words)
    char_count = len(text)
    
    # Words per second (normal speech: 2-3 words/sec)
    words_per_second = word_count / max(audio_duration, 1)
    
    # Silence ratio estimation (if segments available)
    silence_ratio = 0.0
    if segments and audio_duration > 0:
        spoken_time = sum(s.get("end", 0) - s.get("start", 0) for s in segments)
        silence_ratio = 1.0 - (spoken_time / audio_duration)
    elif word_count == 0:
        silence_ratio = 1.0
    
    # Repetition check
    repetition_ratio = 0.0
    if word_count > 5:
        word_lower = [w.lower() for w in words]
        unique_words = set(word_lower)
        repetition_ratio = 1.0 - (len(unique_words) / len(word_lower))
    
    # Fragmentation check (very short words/segments)
    avg_word_len = char_count / max(word_count, 1)
    
    # Issue detection
    if word_count < 5:
        issues.append("very_few_words")
    elif word_count < 10:
        issues.append("few_words")
    
    if silence_ratio > 0.7:
        issues.append("mostly_silence")
    elif silence_ratio > 0.5:
        issues.append("high_silence")
    
    if repetition_ratio > 0.4:
        issues.append("high_repetition")
    
    if words_per_second > 5:
        issues.append("possibly_fast_or_noise")
    
    if avg_word_len < 2:
        issues.append("fragmented_words")
    
    # Quality decision
    # LOW if: very few words OR mostly silence OR multiple issues
    is_low = (
        word_count < 5 or
        silence_ratio > 0.7 or
        len(issues) >= 3
    )
    
    quality = "low" if is_low else "good"
    
    return {
        "quality": quality,
        "metrics": {
            "word_count": word_count,
            "char_count": char_count,
            "words_per_second": round(words_per_second, 2),
            "silence_ratio": round(silence_ratio, 2),
            "repetition_ratio": round(repetition_ratio, 2),
            "avg_word_length": round(avg_word_len, 1),
            "issues": issues
        }
    }


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def transcribe_with_timestamps(video_path: str, has_audio: bool = True) -> Dict:
    """
    Complete STT processing with timestamps and quality assessment.
    
    Args:
        video_path: Path to video file
        has_audio: Whether video has audio (from Phase 1 validation)
    
    Returns:
    {
        "transcript": "Full text...",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Xin chào", "chunk_id": 0},
            ...
        ],
        "stt_quality": "good" | "low",
        "quality_metrics": {...},
        "audio_duration": float,
        "success": True
    }
    """
    print(f"   🎧 [STT] Processing: {os.path.basename(video_path)}")
    
    # Handle videos without audio
    if not has_audio:
        print("   ⚠️ [STT] Video không có audio - skipping STT")
        return {
            "transcript": "",
            "segments": [],
            "stt_quality": "low",
            "quality_metrics": {
                "word_count": 0,
                "issues": ["no_audio"]
            },
            "audio_duration": 0,
            "success": True,
            "skipped": True,
            "reason": "no_audio"
        }
    
    # Step 1: Extract audio
    print("   🔄 [STT] Extracting audio...")
    audio_path = extract_audio(video_path)
    
    if not audio_path:
        print("   ⚠️ [STT] Could not extract audio")
        return {
            "transcript": "",
            "segments": [],
            "stt_quality": "low",
            "quality_metrics": {
                "word_count": 0,
                "issues": ["audio_extraction_failed"]
            },
            "audio_duration": 0,
            "success": False,
            "error": "audio_extraction_failed"
        }
    
    audio_duration = get_audio_duration(audio_path)
    print(f"   ✅ [STT] Audio duration: {audio_duration:.1f}s")
    
    # Step 2: Split into chunks
    chunks = split_audio_chunks(audio_path, chunk_duration=120)
    
    # Step 3: Transcribe each chunk
    print(f"   🚀 [STT] Transcribing {len(chunks)} chunk(s)...")
    
    all_segments = []
    all_texts = []
    
    for i, chunk in enumerate(chunks):
        chunk_path = chunk["path"]
        chunk_start = chunk["start_time"]
        
        print(f"   📤 [STT] Processing chunk {i+1}/{len(chunks)}...")
        result = transcribe_chunk(chunk_path)
        
        if result["success"] and result["text"]:
            all_texts.append(result["text"])
            
            # Create segment for this chunk
            # If API provides segments, adjust timestamps
            if result.get("segments"):
                for seg in result["segments"]:
                    all_segments.append({
                        "start": chunk_start + seg.get("start", 0),
                        "end": chunk_start + seg.get("end", 0),
                        "text": seg.get("text", ""),
                        "chunk_id": i
                    })
            else:
                # Create single segment for chunk
                all_segments.append({
                    "start": chunk_start,
                    "end": chunk["end_time"],
                    "text": result["text"],
                    "chunk_id": i
                })
            
            preview = result["text"][:50] + "..." if len(result["text"]) > 50 else result["text"]
            print(f"   ✅ [STT] Chunk {i+1}: {preview}")
        else:
            error = result.get("error", "unknown")
            print(f"   ⚠️ [STT] Chunk {i+1} failed: {error}")
    
    # Step 4: Merge transcripts
    full_transcript = " ".join(all_texts)
    
    # Step 5: Assess quality
    quality_result = assess_stt_quality(full_transcript, all_segments, audio_duration)
    
    print(f"   📊 [STT] Quality: {quality_result['quality']} ({quality_result['metrics']['word_count']} words)")
    if quality_result["metrics"]["issues"]:
        print(f"   ⚠️ [STT] Issues: {', '.join(quality_result['metrics']['issues'])}")
    
    # Step 6: Cleanup temp files
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        base_path = video_path.replace(".mp4", "_audio")
        for chunk_file in glob.glob(f"{base_path}_chunk_*.wav"):
            os.remove(chunk_file)
    except:
        pass
    
    return {
        "transcript": full_transcript,
        "segments": all_segments,
        "stt_quality": quality_result["quality"],
        "quality_metrics": quality_result["metrics"],
        "audio_duration": audio_duration,
        "success": True
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("🧪 STT Processor Test")
    print("=" * 60)
    
    test_video = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    if os.path.exists(test_video):
        result = transcribe_with_timestamps(test_video, has_audio=True)
        print("\n📊 Result:")
        print(json.dumps({
            "transcript_preview": result["transcript"][:200] if result["transcript"] else "",
            "segment_count": len(result["segments"]),
            "stt_quality": result["stt_quality"],
            "quality_metrics": result["quality_metrics"],
            "audio_duration": result["audio_duration"]
        }, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Test video not found: {test_video}")
