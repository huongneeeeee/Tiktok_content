import os
import subprocess
import requests
import traceback
import glob
from config import Config

def get_audio_duration(audio_path):
    """Get duration of audio file in seconds using FFprobe"""
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{audio_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 0

def split_audio_chunks(audio_path, chunk_duration=120):
    """
    Split audio file into chunks of specified duration (default 2 minutes)
    Returns list of chunk file paths
    """
    duration = get_audio_duration(audio_path)
    if duration <= 0:
        return [audio_path]
    
    # If audio is short enough, no need to split
    if duration <= chunk_duration + 10:  # +10s buffer
        return [audio_path]
    
    chunk_files = []
    base_path = audio_path.replace(".wav", "")
    num_chunks = int(duration / chunk_duration) + 1
    
    print(f"   📌 Video dài {duration:.0f}s, chia thành {num_chunks} chunks...")
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        chunk_path = f"{base_path}_chunk_{i:03d}.wav"
        
        # FFmpeg command to extract chunk
        cmd = f'ffmpeg -i "{audio_path}" -ss {start_time} -t {chunk_duration} -acodec pcm_s16le -ar 16000 -ac 1 "{chunk_path}" -y'
        
        try:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 1000:  # Min 1KB
                chunk_files.append(chunk_path)
        except:
            pass
    
    return chunk_files if chunk_files else [audio_path]

def transcribe_chunk(audio_path, api_url, timeout=120):
    """Transcribe a single audio chunk"""
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            response = requests.post(api_url, files=files, timeout=timeout)
            
        if response.status_code == 200:
            data = response.json()
            return data.get("text", "")
    except requests.exceptions.Timeout:
        print(f"   ⚠️ Chunk timeout: {os.path.basename(audio_path)}")
    except Exception as e:
        print(f"   ⚠️ Chunk error: {e}")
    return ""

def transcribe_video(video_path):
    """
    Client-Side Transcriber with Audio Chunking:
    1. Convert Video -> Audio (WAV 16kHz, Mono)
    2. Split audio into 2-minute chunks for long videos
    3. Send each chunk to STT API
    4. Merge all transcripts
    """
    if not os.path.exists(video_path):
        print(f"❌ [Client] Không tìm thấy file video: {video_path}")
        return ""
    
    # Define file paths
    audio_path = video_path.replace(".mp4", ".wav")
    text_path = video_path.replace(".mp4", ".txt")
    api_url = Config.STT_API_URL
    
    # STEP 1: Convert Video -> Audio
    print(f"🎧 [Client] Đang tách audio từ video...")
    cmd = f'ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}" -y'
    
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("❌ Lỗi FFmpeg: Hãy đảm bảo bạn đã cài FFmpeg và thêm vào PATH.")
        return ""
    except Exception as e:
        print(f"❌ Lỗi xử lý Audio: {e}")
        return ""
    
    # STEP 2: Split into chunks if needed
    chunk_files = split_audio_chunks(audio_path, chunk_duration=120)  # 2 minutes per chunk
    
    # STEP 3: Transcribe each chunk
    print(f"🚀 [Client] Đang gửi {len(chunk_files)} chunk(s) tới API: {api_url}")
    
    all_transcripts = []
    for i, chunk_path in enumerate(chunk_files):
        print(f"   📤 Xử lý chunk {i+1}/{len(chunk_files)}...")
        transcript = transcribe_chunk(chunk_path, api_url, timeout=120)
        if transcript:
            all_transcripts.append(transcript)
            print(f"   ✅ Chunk {i+1}: {transcript[:50]}...")
    
    # STEP 4: Merge transcripts
    full_transcript = " ".join(all_transcripts)
    
    if full_transcript:
        print(f"   ✅ KẾT QUẢ TỔNG HỢP: {full_transcript[:100]}...")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(full_transcript)
    else:
        print("⚠️ Không thể transcribe video (Audio không có tiếng nói?).")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("")
    
    # STEP 5: Cleanup temp files
    # Remove main audio file
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except:
            pass
    
    # Remove chunk files
    base_path = video_path.replace(".mp4", "")
    for chunk_file in glob.glob(f"{base_path}_chunk_*.wav"):
        try:
            os.remove(chunk_file)
        except:
            pass
    
    return full_transcript