# TikTok Content AI

A powerful AI-driven tool for analyzing TikTok videos, extracting insights, and calculating virality scores using Google Gemini API.

## Features

- **Video Ingestion**: Upload video files or download directly from TikTok URLs.
- **AI Analysis**:
  - **Speech-to-Text (STT)**: Transcribes audio with timestamps.
  - **OCR**: Extracts text from video frames.
  - **Scene Detection**: Identifies key visual scenes.
  - **Content Understanding**: Uses Google Gemini to analyze script, pacing, hooks, and virality factors.
- **Rich Metadata**: Extracts hashtags, engagement stats (views, likes, comments), and creator info.
- **API First**: Robust FastAPI backend with MongoDB storage.

## Tech Stack

- **Backend**: FastAPI, Python 3.9+
- **Database**: MongoDB (Metadata), Qdrant (Vector Search - optional)
- **AI/ML**: Google Gemini API, Tesseract OCR, Faster Whisper (stt), Sentence Transformers.
- **Scraper**: Custom TikTok scraper based on [TT_Content_Scraper](https://github.com/d4g10/TT_Content_Scraper).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/tiktok-content-ai.git
    cd tiktok-content-ai
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install External Tools**:
    - **FFmpeg**: Required for video processing. Ensure it's in your system PATH.
    - **Tesseract OCR**: Required for text extraction. Install and set path in `.env`.

5.  **Configuration**:
    Create a `.env` file in the root directory (see `.env.example`):
    ```env
    MONGO_URI=mongodb://localhost:27017/video_analysis_ai
    GEMINI_API_KEY=your_gemini_api_key
    TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
    UPLOAD_DIR=uploads
    ```

## Usage

1.  **Start the Backend**:
    ```bash
    cd backend
    python -m uvicorn app.main:app --reload
    ```
    The API will be available at `http://localhost:8000`.
    API Docs: `http://localhost:8000/docs`.

2.  **Start the Frontend**:
    (Instructions for frontend if applicable)

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/           # API Endpoints
│   │   ├── services/      # Business Logic (Ingest, Analysis, Core)
│   │   ├── models/        # Database Models
│   │   └── core/          # Configuration
├── frontend/              # Next.js Frontend
├── TT_Content_Scraper/    # TikTok Scraper Module
└── requirements.txt
```

## License

MIT License
