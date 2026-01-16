import os
import sys
import json
import re
import shutil
import time
import sqlite3
from moviepy import VideoFileClip

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import Config từ app.core
from app.core.config import Config

# Import Module Scraper (Xử lý lỗi nếu chưa tải thư viện)
try:
    from TT_Content_Scraper.tt_content_scraper import TT_Content_Scraper
except ImportError:
    print("⚠️ Cảnh báo: Không tìm thấy module 'TT_Content_Scraper'. Hãy đảm bảo folder này nằm ở root.")
    TT_Content_Scraper = None

# Định nghĩa đường dẫn DB của Scraper
DB_PATH = os.path.join(Config.SCRAPER_DIR, "progress.db")

# --- 2. QUẢN LÝ SCRAPER ENGINE (SINGLETON) ---
scraper_engine = None

def init_scraper():
    """
    Khởi tạo Scraper Engine.
    Sử dụng Singleton để tránh mở nhiều trình duyệt Chrome cùng lúc.
    """
    global scraper_engine
    if TT_Content_Scraper and scraper_engine is None:
        try:
            print("   ⚙️ [SYSTEM] Đang khởi tạo TikTok Scraper Engine...")
            scraper_engine = TT_Content_Scraper(
                wait_time=2,
                output_files_fp=f"{Config.SCRAPER_DIR}/", # Lưu tạm vào folder scraper_data
                progress_file_fn=f"scraper_data/progress.db", # Path tương đối từ root
                clear_console=False,
                browser_name="chrome" # Dùng Chrome để lấy cookie tốt nhất
            )
        except Exception as e:
            print(f"❌ Lỗi khởi tạo Scraper: {e}")

def close_scraper():
    """Đóng kết nối Scraper an toàn (Giải phóng file DB)."""
    global scraper_engine
    if scraper_engine:
        try:
            # Thử đóng các kết nối database nếu có
            if hasattr(scraper_engine, 'conn'): scraper_engine.conn.close()
            elif hasattr(scraper_engine, 'db_conn'): scraper_engine.db_conn.close()
        except: 
            pass
        finally: 
            scraper_engine = None

# Tự động khởi tạo khi import
init_scraper()

# --- 3. CÁC HÀM TIỆN ÍCH (HELPER FUNCTIONS) ---

def extract_video_id(url):
    """
    Trích xuất ID video từ URL TikTok.
    Hỗ trợ nhiều formats:
    - https://www.tiktok.com/@user/video/1234567890
    - https://www.tiktok.com/@user/photo/1234567890
    - https://vm.tiktok.com/ABC123/ (shortened)
    - https://www.tiktok.com/t/ABC123/ (shortened)
    """
    print(f"   🔍 [URL] Parsing URL: {url}")
    
    # Pattern 1: Standard /video/ or /photo/ URL
    match = re.search(r"/(?:video|photo)/(\d+)", url)
    if match:
        video_id = match.group(1)
        print(f"   ✅ [URL] Found video ID: {video_id}")
        return video_id
    
    # Pattern 2: Check if URL is just a number (raw ID)
    if url.strip().isdigit():
        print(f"   ✅ [URL] Raw ID detected: {url.strip()}")
        return url.strip()
    
    # Pattern 3: Short URL - try to find any long number sequence
    match = re.search(r"(\d{15,})", url)
    if match:
        video_id = match.group(1)
        print(f"   ✅ [URL] Found long number ID: {video_id}")
        return video_id
    
    print(f"   ❌ [URL] Could not extract video ID from URL")
    return None

def _convert_video_to_audio(video_path, audio_path):
    """
    Tách Audio từ Video MP4 (Dùng cho video thường).
    """
    if not VideoFileClip: return False
    try:
        if os.path.exists(audio_path): return True
        
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()
        return True
    except Exception as e:
        print(f"⚠️ Lỗi tách audio: {e}")
        return False

def _force_reset_id_in_db(video_id):
    """
    Xóa ID khỏi SQLite của Scraper để ép buộc tải lại (Re-download).
    """
    if not os.path.exists(DB_PATH): return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM objects WHERE id = ?", (video_id,))
            conn.commit()
    except: 
        pass




# --- 4. XỬ LÝ METADATA ---

def parse_metadata(raw_data, video_id, tiktok_url):
    """
    Chuẩn hóa dữ liệu JSON thô từ Scraper thành định dạng chuẩn của TikVault.
    Bao gồm source_metadata mới cho Phase 1 Content AI.
    """
    clean_meta = {}
    
    # CASE A: Cấu trúc Nested (Phiên bản Scraper mới)
    if 'video_metadata' in raw_data:
        vid = raw_data.get('video_metadata', {})
        auth = raw_data.get('author_metadata', {})
        music = raw_data.get('music_metadata', {})
        file_meta = raw_data.get('file_metadata', {})
        
        # === NEW: Source Metadata cho Content AI ===
        video_duration = file_meta.get('duration', 0)
        
        # Xác định video_type theo nội dung
        # Phân loại dựa trên diversification_labels từ TikTok
        labels = vid.get('diversification_labels', [])
        if any(l.lower() in ['education', 'learnontiktok'] for l in labels):
            video_type = "EDUCATE"
        elif any(l.lower() in ['entertainment', 'comedy'] for l in labels):
            video_type = "ENTERTAIN"
        else:
            video_type = "VIDEO"  # Default
        
        source_metadata = {
            "source_video_id": str(vid.get('id', video_id)),
            "source_video_url": tiktok_url,
            "video_duration": video_duration,
            "video_type": video_type,
            "video_resolution": {
                "width": file_meta.get('width', 0),
                "height": file_meta.get('height', 0)
            },
            "has_audio": file_meta.get('has_original_audio', True) or file_meta.get('enable_audio_caption', True),
            "tiktok_labels": vid.get('diversification_labels', []),
            "suggested_words": vid.get('suggested_words', [])
        }
        
        clean_meta = {
            "id": str(vid.get('id', video_id)),
            "title": vid.get('description') or vid.get('title') or "No Title",
            "hashtags": vid.get('hashtags', []),
            "stats": {
                "views": vid.get('playcount', 0),
                "likes": vid.get('diggcount', 0),
                "comments": vid.get('commentcount', 0),
                "shares": vid.get('sharecount', 0),
                "saves": vid.get('collectcount', 0)
            },
            "author": {
                "id": str(auth.get('id', '')),
                "nickname": auth.get('name', 'Unknown'),
                "unique_id": auth.get('username', 'user'),
                "avatar": auth.get('avatar', '') 
            },
            "music_info": {
                "title": music.get('title', 'Original Sound'),
                "author": music.get('author_name', 'Unknown'),
                "url": None
            },
            "create_time": vid.get('time_created'),
            "thumbnail": vid.get('cover') or vid.get('origin_cover') or vid.get('dynamic_cover'),
            # === NEW: Thêm source_metadata ===
            "source_metadata": source_metadata
        }

    # CASE B: Cấu trúc Phẳng (Phiên bản Scraper cũ - Dự phòng)
    else:
        # Fallback source_metadata cho scraper cũ
        source_metadata = {
            "source_video_id": str(video_id),
            "source_video_url": tiktok_url,
            "video_duration": 0,  # Sẽ được cập nhật từ FFprobe
            "video_type": "VIDEO",
            "video_resolution": {"width": 0, "height": 0},
            "has_audio": True,
            "tiktok_labels": [],
            "suggested_words": []
        }
        
        clean_meta = {
            "id": str(video_id),
            "title": raw_data.get('desc') or raw_data.get('title') or "No Title",
            "hashtags": [t.get('title') for t in raw_data.get('challenges', [])] if raw_data.get('challenges') else [],
            "stats": {
                "views": raw_data.get('stats', {}).get('playCount', 0),
                "likes": raw_data.get('stats', {}).get('diggCount', 0),
                "comments": raw_data.get('stats', {}).get('commentCount', 0),
                "shares": raw_data.get('stats', {}).get('shareCount', 0),
                "saves": raw_data.get('stats', {}).get('collectCount', 0)
            },
            "author": {
                "id": raw_data.get('author', {}).get('id'),
                "nickname": raw_data.get('author', {}).get('nickname'),
                "unique_id": raw_data.get('author', {}).get('uniqueId'),
                "avatar": raw_data.get('author', {}).get('avatarThumb'),
            },
            "music_info": {
                "title": raw_data.get('music', {}).get('title'),
                "author": raw_data.get('music', {}).get('authorName'),
                "url": raw_data.get('music', {}).get('playUrl')
            },
            "create_time": raw_data.get('createTime'),
            "thumbnail": raw_data.get('video', {}).get('cover'),
            # === NEW: Thêm source_metadata ===
            "source_metadata": source_metadata
        }

    clean_meta['original_url'] = tiktok_url
    return clean_meta

# --- 5. HÀM CHÍNH (MAIN FUNCTION) ---

def download_tiktok_full_data(tiktok_url):
    """
    Quy trình tải và xử lý video TikTok toàn diện:
    1. Reset DB -> Scrape Video/Audio/JSON.
    2. Di chuyển file từ folder Scraper sang folder Temp.
    3. Xử lý Slideshow (Convert MP3 -> MP4 giả).
    4. Parse Metadata chuẩn.
    """
    print(f"\n--- 📥 BẮT ĐẦU XỬ LÝ: {tiktok_url} ---")

    # 🛑 BLOCK PHOTO/SLIDESHOW LINKS
    if "/photo/" in tiktok_url:
        print(f"❌ [BLOCKED] Link Photo/Slideshow không được hỗ trợ: {tiktok_url}")
        return None
    
    if not scraper_engine: init_scraper()
    if not scraper_engine: return None
    
    # B1: Lấy ID và Reset trạng thái tải cũ
    video_id = extract_video_id(tiktok_url)
    if not video_id:
        print("❌ Lỗi: URL TikTok không hợp lệ.")
        return None
    _force_reset_id_in_db(video_id)

    # B2: Chạy lệnh Scrape
    try:
        print(f"   🔄 Đang quét ID: {video_id}...")
        scraper_engine.add_objects(ids=[video_id], type="content")
        scraper_engine.scrape_pending(scrape_files=True)
    except Exception as e:
        # Lỗi "No more pending" là bình thường (nghĩa là đã tải xong list)
        print(f"   ℹ️ Scraper Note: {e}")

    # B3: Xác định đường dẫn file thô (trong folder scraper_data)
    # Cấu trúc của thư viện này lưu file theo tên ID
    raw_video_path = os.path.join(Config.SCRAPER_DIR, "content_files", f"tiktok_video_{video_id}.mp4")
    raw_audio_path = os.path.join(Config.SCRAPER_DIR, "content_files", f"tiktok_audio_{video_id}.mp3")
    raw_json_path = os.path.join(Config.SCRAPER_DIR, "content_metadata", f"{video_id}.json")

    # Đợi một chút để hệ thống file kịp ghi (Fix lỗi trên máy chậm)
    timeout = 0
    while not (os.path.exists(raw_video_path) or os.path.exists(raw_audio_path)) and timeout < 5:
        time.sleep(1)
        timeout += 1

    # B4: Kiểm tra file tải về
    if not os.path.exists(raw_video_path):
        print(f"❌ Lỗi: Không tìm thấy file video. (ID: {video_id})")
        # Nếu chỉ có audio -> có thể là slideshow đã bị block ở bước đầu, nhưng scraper vẫn tải được audio
        if os.path.exists(raw_audio_path):
             print(f"❌ Lỗi: Đây là Slideshow (đã bị block), không hỗ trợ xử lý.")
        return None

    print("   🎥 Phát hiện: VIDEO (.mp4)")

    # B5: Di chuyển và Đổi tên sang thư mục TEMP
    final_video_path = os.path.join(Config.TEMP_DIR, f"{video_id}.mp4")
    final_music_path = os.path.join(Config.TEMP_DIR, f"{video_id}_music.mp3")
    final_meta_path = os.path.join(Config.TEMP_DIR, f"{video_id}_meta.json")

    try:
        # 1. Copy Video MP4
        shutil.copy(raw_video_path, final_video_path)
        # 2. Tách nhạc ra file MP3 riêng (để nghe/upload)
        _convert_video_to_audio(final_video_path, final_music_path)
    except Exception as e:
        print(f"❌ Lỗi copy/convert file: {e}")
        return None

    # B6: Xử lý Metadata
    try:
        if not os.path.exists(raw_json_path):
            print("❌ Lỗi: Không tìm thấy file Metadata JSON.")
            return None
            
        with open(raw_json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Parse về định dạng chuẩn
        clean_metadata = parse_metadata(raw_data, video_id, tiktok_url)
        
        # Lưu file Meta đã xử lý vào Temp
        with open(final_meta_path, 'w', encoding='utf-8') as f:
            json.dump(clean_metadata, f, ensure_ascii=False, indent=4)

        print(f"   ✅ Xử lý hoàn tất: {clean_metadata.get('title', 'No Title')[:40]}...")
        
        # Trả về kết quả cho Pipeline
        return {
            "local_path": final_video_path,
            "music_path": final_music_path,
            "meta_path": final_meta_path,
            "filename": f"{video_id}.mp4",
            "metadata": clean_metadata
        }

    except Exception as e:
        print(f"❌ Lỗi xử lý Metadata: {e}")
        return None