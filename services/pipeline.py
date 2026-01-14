# services/pipeline.py
import time
import traceback
from datetime import datetime

from services.tiktok_tool import download_tiktok_full_data
from services.gdrive_sync import upload_to_gdrive
from services.ai_processor import transcribe_video
from services.analyzer import analyze_video_content
from services.ocr_processor import process_video_ocr

import os

GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")


def process_tiktok(url: str, db, user_id: str = None):
    """Xử lý video TikTok với logging chi tiết"""
    print(f"\n🎬 [PIPELINE] Bắt đầu xử lý: {url}")
    
    try:
        dl = download_tiktok_full_data(url)
    except Exception as e:
        print(f"❌ [PIPELINE] Lỗi download: {e}")
        traceback.print_exc()
        return None, f"Download error: {str(e)}"
    
    if not dl:
        print("❌ [PIPELINE] Download trả về None - có thể URL không hợp lệ hoặc scraper lỗi")
        return None, "Download failed - URL không hợp lệ hoặc không thể tải video"

    video_info = dl["metadata"]
    video_info["video_id"] = video_info.get("id")  # Ensure video_id is set
    video_info["filename"] = dl["filename"]
    video_info["type"] = "video"
    video_info["processed_at"] = datetime.now()
    
    # Add user_id to associate video with user
    if user_id:
        video_info["user_id"] = user_id
    
    # Add slideshow_images if present
    if dl.get("slideshow_images"):
        video_info["slideshow_images"] = dl["slideshow_images"]
    # Add absolute paths for OCR processing
    if dl.get("slideshow_images_abs"):
        video_info["slideshow_images_abs"] = dl["slideshow_images_abs"]

    local_path = dl["local_path"]

    # Upload Drive (optional)
    if GDRIVE_FOLDER_ID:
        try:
            video_info["drive_links"] = upload_to_gdrive(local_path, GDRIVE_FOLDER_ID)
        except Exception:
            pass

    # Transcribe (STT)
    transcript = transcribe_video(local_path)
    video_info["transcript"] = transcript

    # OCR Processing - Kết hợp với transcript để phân loại tốt hơn
    print("   🔍 [PIPELINE] OCR processing...")
    try:
        ocr_result = process_video_ocr(local_path, video_info)
        video_info["ocr_data"] = ocr_result
        if ocr_result.get("ocr_text"):
            print(f"   ✅ [PIPELINE] OCR: {ocr_result.get('text_count', 0)} text items extracted")
        else:
            print("   ⚠️ [PIPELINE] OCR: No text found in video")
    except Exception as e:
        print(f"   ⚠️ [PIPELINE] OCR error (non-fatal): {e}")
        video_info["ocr_data"] = {"ocr_text": "", "error": str(e)}

    # Analyze - Truyền thêm ocr_result
    ai = analyze_video_content(transcript, video_info, ocr_result=video_info.get("ocr_data"))
    video_info["ai_analysis"] = ai

    # Save DB using proper upsert method
    if db is not None:
        try:
            db.save_video(video_info)
            print(f"   ✅ [DB] Video saved: {video_info.get('video_id')}")
        except Exception as e:
            print(f"   ❌ [DB] Error saving video: {e}")

    return video_info, "OK"


def process_text(content: str, filename: str, db):
    if not content.strip():
        return None, "Empty text"

    data = {
        "id": f"text_{int(time.time())}",
        "type": "text",
        "filename": filename,
        "content": content,
        "created_at": datetime.now()
    }

    ai = analyze_video_content(content, {"title": filename})
    data["ai_analysis"] = ai

    if db is not None and db.videos is not None:
        db.videos.insert_one(data)

        db.store_embedding(
            content,
            {
                "id": data["id"],
                "type": "text",
                "summary": ai.get("meta", {}).get("summary", ""),
                "category": ai.get("classification", {}),
                "rag_data": ai.get("rag_data", {})
            }
        )

    return data, "OK"
