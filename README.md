# TikVault 

Hệ thống quản lý và phân tích video TikTok với AI - tự động trích xuất kiến thức, phân loại nội dung, và tổ chức thông tin.

## 🚀 Tính năng chính

- **Auto Import**: Tự động tải video từ TikTok để lưu trữ vĩnh viễn
- **AI Analysis**: Phân tích nội dung video bằng Gemini AI - trích xuất kiến thức, phân loại tự động
- **Speech-to-Text**: Chuyển đổi audio thành text bằng Whisper
- **Collections**: Tổ chức video theo bộ sưu tập tùy chỉnh
- **Search**: Tìm kiếm semantic trong toàn bộ nội dung đã phân tích
- **Compare**: So sánh kiến thức giữa các video

## 📋 Yêu cầu hệ thống

- Python 3.10+
- MongoDB (local hoặc cloud)
- Qdrant (vector database)
- Node.js (cho một số tính năng)

## 🔧 Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/your-username/TikVault.git
cd TikVault
```

### 2. Tạo virtual environment

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình môi trường

```bash
# Copy file mẫu
cp .env.example .env

# Mở file .env và điền các giá trị thật
```

**Các biến cần cấu hình:**
- `GEMINI_API_KEY`: API key từ Google AI Studio
- `GDRIVE_FOLDER_ID`: ID thư mục Google Drive để backup video
- `MONGO_URI`: Connection string MongoDB
- `QDRANT_HOST/PORT`: Địa chỉ Qdrant server

### 5. Cấu hình Google Drive (tùy chọn)

Nếu muốn backup video lên Google Drive:
1. Tạo project tại [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Drive API
3. Tạo OAuth 2.0 credentials
4. Download `credentials.json` vào thư mục `secrets/`

### 6. Chạy ứng dụng

```bash
uvicorn main:app --reload --port 8000
```

Truy cập: http://localhost:8000

## 📁 Cấu trúc dự án

```
TikVault/
├── app/                    # FastAPI application
│   ├── routers/           # API endpoints
│   └── database.py        # Database connections
├── services/              # Core services
│   ├── analyzer.py        # AI analysis
│   ├── gdrive.py          # Google Drive integration
│   ├── stt.py             # Speech-to-text
│   └── embedding.py       # Vector embeddings
├── templates/             # Jinja2 HTML templates
├── static/                # CSS/JS files
├── TT_Content_Scraper/    # Video scraping module
├── secrets/               # Credentials (gitignored)
├── main.py               # Application entry
└── config.py             # Configuration loader
```

## 🔐 Bảo mật

> ⚠️ **QUAN TRỌNG**: Không commit các file sau lên Git:
> - `.env` - chứa API keys
> - `secrets/` - chứa Google credentials
> - `credentials.json`, `token.json` - OAuth tokens

Các file này đã được liệt kê trong `.gitignore`

## 📝 License

MIT License

## 🤝 Đóng góp

Mọi đóng góp đều được hoan nghênh! Vui lòng tạo Issue hoặc Pull Request.
