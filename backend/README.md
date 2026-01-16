# TikTok Content AI - Backend

Backend xử lý và phân tích nội dung TikTok.

## 📁 Cấu Trúc Thư Mục

```
backend/
├── app/
│   ├── main.py              # Entry point FastAPI (placeholder)
│   ├── api/                  # API routers (future)
│   ├── core/                 # Config, constants
│   │   └── config.py         # Configuration từ .env
│   ├── services/             # Business logic
│   │   ├── pipeline.py       # Main pipeline orchestrator
│   │   ├── analysis/         # Phase 2: Multimodal processing
│   │   │   ├── orchestrator.py
│   │   │   ├── stt.py        # Speech-to-Text
│   │   │   ├── ocr.py        # OCR processing
│   │   │   └── vision.py     # Scene detection
│   │   ├── processing/       # Phase 3: Content understanding
│   │   │   ├── synthesizer.py
│   │   │   ├── alignment.py
│   │   │   ├── cleaning.py
│   │   │   └── reasoning.py
│   │   └── ingest/           # Phase 1: Video input
│   │       ├── downloader.py
│   │       ├── normalizer.py
│   │       └── validator.py
│   ├── models/               # Schema / DB models (future)
│   └── utils/                # Helper functions (future)
│
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## 🚀 Cài Đặt

```bash
cd backend
pip install -r requirements.txt
```

## ⚙️ Cấu Hình

1. Copy `.env.example` thành `.env` ở thư mục gốc project
2. Điền các API keys và cấu hình

## 🔧 Sử Dụng

```python
from app.services.pipeline import process_tiktok

result, status = process_tiktok("https://tiktok.com/...")
```

## 📊 Pipeline Flow

```
Phase 1: Ingest → Phase 2: Analysis → Phase 3: Processing
   ↓                    ↓                    ↓
Download          STT + OCR           Understanding
Validate          Scene Detection     Normalization
Normalize         Quality Check       Reasoning Ready
```
