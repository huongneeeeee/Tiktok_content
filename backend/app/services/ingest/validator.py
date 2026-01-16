# services/video_validator.py
"""
Video Validator Module - Phase 1: Tiếp nhận & Chuẩn hóa Video
Xử lý các edge cases: video quá ngắn/dài, không có audio, codec lỗi
"""

import os
import subprocess
import json
from typing import Dict, Any, Optional

# Cấu hình Validation
MIN_DURATION = 3        # Video < 3s = low_confidence
MAX_DURATION = 600      # Video > 10 phút = warning (vẫn xử lý)
VALID_CODECS = ["h264", "hevc", "h265", "vp9", "av1", "mpeg4"]


def get_video_metadata(video_path: str) -> Optional[Dict[str, Any]]:
    """
    Sử dụng FFprobe để trích xuất metadata từ video file.
    Returns: Dict chứa duration, fps, codec, has_audio, resolution
    """
    if not os.path.exists(video_path):
        return None
    
    try:
        # FFprobe command để lấy thông tin video và audio streams
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"   ⚠️ [VALIDATOR] FFprobe error: {result.stderr}")
            return None
        
        data = json.loads(result.stdout)
        
        # Tìm video stream
        video_stream = None
        audio_stream = None
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and video_stream is None:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and audio_stream is None:
                audio_stream = stream
        
        # Trích xuất thông tin
        format_info = data.get('format', {})
        duration = float(format_info.get('duration', 0))
        
        # Nếu duration từ format không có, thử lấy từ video stream
        if duration == 0 and video_stream:
            duration = float(video_stream.get('duration', 0))
        
        # FPS calculation
        fps = 0
        if video_stream:
            fps_str = video_stream.get('r_frame_rate', '0/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                if int(den) > 0:
                    fps = round(int(num) / int(den), 2)
        
        metadata = {
            "duration": round(duration, 2),
            "fps": fps,
            "codec": video_stream.get('codec_name', 'unknown') if video_stream else 'unknown',
            "has_audio": audio_stream is not None,
            "width": int(video_stream.get('width', 0)) if video_stream else 0,
            "height": int(video_stream.get('height', 0)) if video_stream else 0,
            "bitrate": int(format_info.get('bit_rate', 0)),
            "file_size": int(format_info.get('size', 0))
        }
        
        return metadata
        
    except subprocess.TimeoutExpired:
        print(f"   ⚠️ [VALIDATOR] FFprobe timeout")
        return None
    except json.JSONDecodeError:
        print(f"   ⚠️ [VALIDATOR] FFprobe output parse error")
        return None
    except Exception as e:
        print(f"   ⚠️ [VALIDATOR] FFprobe error: {e}")
        return None


def validate_video(video_path: str, scraper_metadata: Dict = None) -> Dict[str, Any]:
    """
    Validate video và trả về kết quả với confidence level.
    
    Args:
        video_path: Đường dẫn tới file video
        scraper_metadata: Metadata từ scraper JSON (optional, để cross-check)
    
    Returns:
        {
            "is_valid": True/False,
            "confidence": "high" | "medium" | "low",
            "warnings": [...],
            "metadata": {...}
        }
    """
    result = {
        "is_valid": True,
        "confidence": "high",
        "warnings": [],
        "metadata": None
    }
    
    # Kiểm tra file tồn tại
    if not os.path.exists(video_path):
        result["is_valid"] = False
        result["confidence"] = "low"
        result["warnings"].append("file_not_found")
        return result
    
    # Lấy metadata từ FFprobe
    metadata = get_video_metadata(video_path)
    
    if metadata is None:
        # Thử dùng scraper metadata nếu FFprobe thất bại
        if scraper_metadata and 'file_metadata' in scraper_metadata:
            file_meta = scraper_metadata['file_metadata']
            metadata = {
                "duration": file_meta.get('duration', 0),
                "fps": 0,  # Không có từ scraper
                "codec": "unknown",
                "has_audio": file_meta.get('has_original_audio', True),
                "width": file_meta.get('width', 0),
                "height": file_meta.get('height', 0),
                "bitrate": 0,
                "file_size": 0
            }
            result["warnings"].append("ffprobe_failed_using_scraper_metadata")
        else:
            result["is_valid"] = False
            result["confidence"] = "low"
            result["warnings"].append("cannot_read_metadata")
            return result
    
    result["metadata"] = metadata
    
    # === VALIDATION CHECKS ===
    
    # 1. Check duration
    duration = metadata.get("duration", 0)
    
    if duration < MIN_DURATION:
        result["confidence"] = "low"
        result["warnings"].append("video_too_short")
        print(f"   ⚠️ [VALIDATOR] Video quá ngắn: {duration}s < {MIN_DURATION}s")
    
    if duration > MAX_DURATION:
        # Vẫn valid nhưng cảnh báo
        if result["confidence"] == "high":
            result["confidence"] = "medium"
        result["warnings"].append("video_too_long")
        print(f"   ⚠️ [VALIDATOR] Video dài: {duration}s > {MAX_DURATION}s (10 phút)")
    
    # 2. Check audio
    if not metadata.get("has_audio", True):
        if result["confidence"] == "high":
            result["confidence"] = "medium"
        result["warnings"].append("no_audio")
        print(f"   ⚠️ [VALIDATOR] Video không có audio - sẽ bỏ qua STT")
    
    # 3. Check codec
    codec = metadata.get("codec", "unknown").lower()
    if codec not in VALID_CODECS and codec != "unknown":
        if result["confidence"] == "high":
            result["confidence"] = "medium"
        result["warnings"].append("unusual_codec")
        print(f"   ⚠️ [VALIDATOR] Codec không phổ biến: {codec} - có thể cần normalize")
    
    # 4. Check resolution (sanity check)
    width = metadata.get("width", 0)
    height = metadata.get("height", 0)
    
    if width == 0 or height == 0:
        result["warnings"].append("invalid_resolution")
        result["confidence"] = "low"
    
    # Tổng kết
    print(f"   ✅ [VALIDATOR] Kết quả: valid={result['is_valid']}, confidence={result['confidence']}")
    if result["warnings"]:
        print(f"   ⚠️ [VALIDATOR] Warnings: {', '.join(result['warnings'])}")
    
    return result


def should_normalize(validation_result: Dict) -> bool:
    """
    Quyết định xem video có cần normalize (re-encode) không.
    """
    warnings = validation_result.get("warnings", [])
    
    # Cần normalize nếu:
    # - Codec không phổ biến
    # - FFprobe thất bại (file có thể bị lỗi)
    return "unusual_codec" in warnings or "cannot_read_metadata" in warnings


# === TEST ===
if __name__ == "__main__":
    # Test với video mẫu
    test_path = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    if os.path.exists(test_path):
        print(f"\n🧪 Testing with: {test_path}")
        result = validate_video(test_path)
        print(f"\n📊 Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Test file not found: {test_path}")
