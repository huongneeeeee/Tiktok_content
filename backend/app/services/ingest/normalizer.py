# services/video_normalizer.py
"""
Video Normalizer Module - Phase 1: Tiếp nhận & Chuẩn hóa Video
Re-encode video về format chuẩn (H.264 + AAC) khi cần
"""

import os
import subprocess
from typing import Optional


def normalize_video(input_path: str, force: bool = False) -> Optional[str]:
    """
    Re-encode video về format chuẩn: H.264 video + AAC audio.
    Đảm bảo tương thích với mọi player và công cụ xử lý.
    
    Args:
        input_path: Đường dẫn video gốc
        force: True = luôn normalize, False = chỉ normalize nếu cần
    
    Returns:
        Đường dẫn file mới nếu thành công, None nếu thất bại
    """
    if not os.path.exists(input_path):
        print(f"   ❌ [NORMALIZER] File không tồn tại: {input_path}")
        return None
    
    # Tạo tên file output
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_normalized.mp4"
    
    # Nếu đã có file normalized, return luôn
    if os.path.exists(output_path) and not force:
        print(f"   ✅ [NORMALIZER] File đã được normalize trước đó")
        return output_path
    
    print(f"   🔄 [NORMALIZER] Đang chuẩn hóa video...")
    
    try:
        # FFmpeg command: Re-encode với H.264 + AAC
        # -c:v libx264 : Video codec H.264
        # -preset fast : Cân bằng giữa tốc độ và chất lượng
        # -crf 23      : Chất lượng trung bình-tốt (18-28 range)
        # -c:a aac     : Audio codec AAC
        # -b:a 128k    : Audio bitrate
        # -movflags +faststart : Cho phép streaming
        # -y           : Overwrite output
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        # Chạy FFmpeg (ẩn output)
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # 5 phút timeout
        )
        
        if result.returncode != 0:
            print(f"   ❌ [NORMALIZER] FFmpeg error: {result.stderr[-500:]}")  # Last 500 chars
            return None
        
        # Verify output file
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"   ✅ [NORMALIZER] Hoàn tất: {output_path}")
            return output_path
        else:
            print(f"   ❌ [NORMALIZER] Output file quá nhỏ hoặc không tồn tại")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ [NORMALIZER] Timeout (> 5 phút)")
        return None
    except FileNotFoundError:
        print(f"   ❌ [NORMALIZER] FFmpeg không được cài đặt hoặc không có trong PATH")
        return None
    except Exception as e:
        print(f"   ❌ [NORMALIZER] Lỗi: {e}")
        return None


def extract_audio_wav(video_path: str, output_path: str = None) -> Optional[str]:
    """
    Trích xuất audio từ video và convert sang WAV 16kHz mono.
    Chuẩn bị cho STT (Speech-to-Text).
    
    Args:
        video_path: Đường dẫn video
        output_path: Đường dẫn WAV output (optional)
    
    Returns:
        Đường dẫn file WAV nếu thành công
    """
    if not os.path.exists(video_path):
        return None
    
    if output_path is None:
        output_path = video_path.replace(".mp4", ".wav")
    
    # Nếu đã có, return luôn
    if os.path.exists(output_path):
        return output_path
    
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',              # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '16000',     # 16kHz sample rate (tốt cho STT)
            '-ac', '1',         # Mono
            '-y',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        
        # Kiểm tra nếu video không có audio
        if "does not contain any stream" in result.stderr or "Output file is empty" in result.stderr:
            print(f"   ⚠️ [NORMALIZER] Video không có audio track")
            return None
            
        return None
        
    except Exception as e:
        print(f"   ⚠️ [NORMALIZER] Lỗi trích xuất audio: {e}")
        return None


def check_ffmpeg_installed() -> bool:
    """Kiểm tra FFmpeg đã được cài đặt chưa."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


# === TEST ===
if __name__ == "__main__":
    print("🧪 Video Normalizer Test")
    print("=" * 50)
    
    # Check FFmpeg
    if check_ffmpeg_installed():
        print("✅ FFmpeg đã được cài đặt")
    else:
        print("❌ FFmpeg chưa được cài đặt. Vui lòng cài đặt FFmpeg và thêm vào PATH")
        exit(1)
    
    # Test với video mẫu
    test_path = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    if os.path.exists(test_path):
        print(f"\n📹 Testing with: {test_path}")
        
        # Test extract audio
        audio_path = extract_audio_wav(test_path, test_path.replace(".mp4", "_test.wav"))
        if audio_path:
            print(f"✅ Audio extracted: {audio_path}")
            # Cleanup
            os.remove(audio_path)
        else:
            print("⚠️ No audio or extraction failed")
    else:
        print(f"❌ Test file not found: {test_path}")
