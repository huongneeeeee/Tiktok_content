# TỔNG QUAN HỆ THỐNG TIKTOK CONTENT AI (SYSTEM OVERVIEW)

Tài liệu này mô tả chi tiết quy trình, kiến trúc và luồng dữ liệu của hệ thống phân tích video TikTok sử dụng Gemini AI.

---

## 1. MỤC TIÊU HỆ THỐNG
Xây dựng một nền tảng tự động hóa việc phân tích nội dung video ngắn (TikTok/Shorts) để:
- Hiểu sâu nội dung (Deep Understanding) qua AI.
- Phân tích kỹ thuật quay dựng, kịch bản.
- Đánh giá tiềm năng Viral.
- Tìm kiếm video dựa trên ngữ nghĩa (Semantic Search).

---

## 2. KIẾN TRÚC TỔNG QUAN (ARCHITECTURE)

Hệ thống hoạt động theo mô hình Client-Server hiện đại:

| Thành phần | Công nghệ | Vai trò |
|------------|----------|---------|
| **Frontend** | Next.js 14, TailwindCSS | Giao diện người dùng (Upload, View, Search). |
| **Backend** | FastAPI (Python) | API Server, điều phối tác vụ nền. |
| **AI Core** | Google Gemini 1.5 Flash | Mô hình đa phương thức (Multimodal) phân tích Video + Text. |
| **Database** | MongoDB | Lưu trữ Metadata và kết quả phân tích JSON. |
| **Storage** | Local Filesystem | Lưu tạm video trước khi upload lên Gemini. |

---

## 3. QUY TRÌNH XỬ LÝ (WORKFLOW)

Quy trình xử lý một video đi qua 4 giai đoạn chính:

### Giai đoạn 1: Ingestion (Tiếp nhận đầu vào)
Người dùng có 2 cách đưa video vào hệ thống:
1.  **Upload File**: Upload file `.mp4` trực tiếp từ máy tính.
2.  **Import Link**: Paste link TikTok/YouTube, hệ thống tự động tải về (sử dụng `yt-dlp` hoặc scraper).

**Tác vụ:**
- Kiểm tra định dạng và kích thước.
- Lưu file vào thư mục local.
- Tạo bản ghi trong MongoDB với trạng thái `pending`.

### Giai đoạn 2: Pre-Analysis (Chuẩn bị phân tích)
Ngay khi có file:
- **Module `GeminiFileUploader`**: Upload video lên Google AI Studio (File API).
- **Trạng thái File**: Hệ thống poll (kiểm tra liên tục) cho đến khi file chuyển trạng thái từ `PROCESSING` sang `ACTIVE`.

### Giai đoạn 3: AI Analysis (Phân tích cốt lõi)
Hệ thống gọi Gemini API với cấu hình:
- **Model**: `gemini-1.5-flash` (Tối ưu tốc độ & chi phí).
- **Input**: Video File URI + Prompt chi tiết.
- **System Instruction**: Persona "Chuyên gia Media & Marketing".
- **Prompt**: Yêu cầu phân tích 5 khía cạnh:
    1.  **Thông tin chung**: Title, Category, Sentiment.
    2.  **Nội dung**: Mục tiêu, thông điệp, Hook 3 giây đầu.
    3.  **Kịch bản (Script)**: Phân rã từng giây (Visual, Audio, Text, Camera Angle).
    4.  **Kỹ thuật**: Edit style, m nhạc, Transitions.
    5.  **Viral**: Chấm điểm tiềm năng, lý do thành công/thất bại.

**Output Processing:**
- Nhận kết quả dạng JSON Raw.
- Dùng **LangChain JsonOutputParser** để validate và đưa về đúng cấu trúc Pydantic (`VideoAnalysisResult`).

### Giai đoạn 4: Storage & Serving (Lưu trữ & Trả về)
- **Lưu Database**: Cập nhật document trong MongoDB với full kết quả JSON.
- **Metadata**: Lưu URL gốc, ngày phân tích, thời gian xử lý.
- **Frontend Display**:
    - Hiển thị Video Player.
    - Bảng phân tích kịch bản (Click dòng nào video nhảy tới đoạn đó).
    - Biểu đồ điểm Viral.

---

## 4. CẤU TRÚC DỮ LIỆU (DATA SCHEMA)

Dữ liệu được lưu trong MongoDB (collection `videos`) với cấu trúc chính:

```json
{
  "video_id": "vid_20240116_...",
  "status": "analyzed",
  "url": "https://tiktok.com/@user/video/...",
  "metadata": {
    "duration": 60.5,
    "file_size_mb": 15.2
  },
  "analysis": {
    "general_info": { "title": "...", "category": "..." },
    "content_analysis": { "key_message": "...", "hook_strategy": "..." },
    "script_breakdown": [
      {
        "time_range": "00:00 - 00:05",
        "visual_description": "Cận cảnh món ăn...",
        "audio_transcript": "Xin chào các bạn...",
        "pacing": "Nhanh"
      }
    ],
    "virality_factors": { "score": 8, "reasons": "..." }
  },
  "created_at": "ISODate(...)",
  "analyzed_at": "ISODate(...)"
}
```

---

## 5. HỆ THỐNG API (KEY ENDPOINTS)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/videos/analyze` | Upload/Link -> Phân tích -> Trả về JSON (Sync). |
| `POST` | `/videos/{id}/analyze` | Trigger phân tích ngầm (Async Background Task). |
| `GET` | `/videos/{id}/analysis` | Lấy kết quả phân tích của video. |
| `GET` | `/videos/search/query` | Tìm kiếm video theo ngữ nghĩa/category. |
| `GET` | `/videos/config/upload-info`| Lấy thông tin cấu hình upload. |

---

## 6. GHI CHÚ VẬN HÀNH

- **Debug Server**: Chạy lệnh `uvicorn backend.app.main:app --reload` để dev.
- **Reload Loop Fix**: Luôn dùng flag `--reload-exclude "scraper_data"` để tránh restart loop khi scraper ghi DB.
- **API Key**: Đảm bảo `GEMINI_API_KEY` trong `.env` có quota hợp lệ (ưu tiên `gemini-1.5-flash` cho Free Tier).
