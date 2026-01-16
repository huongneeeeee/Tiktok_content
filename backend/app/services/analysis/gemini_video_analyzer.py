# backend/app/services/analysis/gemini_video_analyzer.py
"""
Gemini Video Analyzer Service

Phân tích video sử dụng Gemini API với structured JSON output.
Tích hợp LangChain JsonOutputParser để đảm bảo output đúng format.

Features:
- Upload video lên Gemini File API
- Prompt chi tiết cho phân tích video
- Parse response thành Pydantic model
- Xử lý lỗi và retry logic
"""

import os
import sys
import time
import json
import re
from typing import Dict, Optional
from datetime import datetime

# Ensure backend is in path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import Config
from app.models.video_analysis_models import VideoAnalysisResult
from app.services.ingest.gemini_uploader import GeminiFileUploader, GeminiUploadError

# Import Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ [GEMINI_ANALYZER] google-genai SDK not installed")

# Import LangChain for JsonOutputParser
try:
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️ [GEMINI_ANALYZER] langchain not installed")


# ============================================================
# PROMPT TEMPLATE
# ============================================================


SYSTEM_INSTRUCTION = """Bạn là chuyên gia phân tích nội dung video TikTok/short-form video chuyên nghiệp.
Nhiệm vụ của bạn là xem video và phân tích chi tiết các yếu tố kỹ thuật, nội dung, và tiềm năng viral.
Bạn có kiến thức sâu rộng về quay dựng, ánh sáng, âm thanh, và tâm lý người xem TikTok."""

ANALYSIS_PROMPT_TEMPLATE = """Hãy phân tích video này theo các tiêu chí sau và trả về kết quả JSON.

## 1. THÔNG TIN CHUNG (general_info)
- **title**: Đặt tiêu đề phù hợp cho video dựa trên nội dung
- **category**: Phân loại video (Vlog, Tutorial, Review, Drama, Ads, Entertainment, Education, Comedy, Lifestyle, etc.)
- **overall_sentiment**: Cảm xúc chủ đạo (Hài hước, Nghiêm túc, Cảm động, Gay cấn, Vui vẻ, Buồn, Kích thích, etc.)
- **target_audience**: Mô tả chân dung khán giả mục tiêu (độ tuổi, sở thích, hành vi)

## 2. PHÂN TÍCH NỘI DUNG (content_analysis)
- **main_objective**: Mục tiêu chính của video (Bán hàng, Branding, Giáo dục, Giải trí, Chia sẻ kinh nghiệm, etc.)
- **key_message**: Thông điệp cốt lõi mà video muốn truyền tải
- **hook_strategy**: Cách video giữ chân người xem trong 3-5 giây đầu tiên

## 3. PHÂN TÍCH KỊCH BẢN (script_breakdown)
Chia video thành các đoạn/scene rõ ràng. Với MỖI ĐOẠN, xác định:
- **segment_id**: Số thứ tự (1, 2, 3...)
- **time_range**: Khoảng thời gian (format: "00:00 - 00:15")
- **start_seconds**: Giây bắt đầu (số)
- **end_seconds**: Giây kết thúc (số)
- **visual_description**: Mô tả chi tiết cảnh quay (người, vật, hành động, bối cảnh, màu sắc)
- **camera_angle**: Góc máy (Toàn cảnh, Trung cảnh, Cận cảnh, POV, Aerial, Tracking, etc.)
- **audio_transcript**: Lời thoại hoặc mô tả âm thanh. Nếu là nhạc, ghi rõ thể loại và mood
- **on_screen_text**: Text xuất hiện trên màn hình (caption, subtitle, overlay)
- **pacing**: Nhịp độ (Nhanh, Chậm, Dồn dập, Vừa phải, Tĩnh lặng)

## 4. ĐÁNH GIÁ KỸ THUẬT (technical_audit)
- **editing_style**: Phong cách edit (Jump cuts, Mượt mà, Minimalist, Cinematic, Raw, Trend TikTok, etc.)
- **sound_design**: Đánh giá âm thanh/nhạc nền (chất lượng, phù hợp, mixing)
- **cta_analysis**: Phân tích Call to Action (có không, vị trí, hiệu quả)
- **video_quality**: Chất lượng hình ảnh (độ phân giải, ánh sáng, màu sắc)
- **transitions**: Các hiệu ứng chuyển cảnh

## 5. TIỀM NĂNG VIRAL (virality_factors)
- **score**: Điểm từ 1-10 (10 là tiềm năng cao nhất)
- **reasons**: Giải thích tại sao video có/không có tiềm năng viral
- **improvement_suggestions**: Đề xuất cụ thể để cải thiện video
- **strengths**: Danh sách điểm mạnh của video
- **weaknesses**: Danh sách điểm yếu cần cải thiện

---

⚠️ QUAN TRỌNG: Trả về kết quả DƯỚI DẠNG JSON hợp lệ theo schema sau:

{format_instructions}

Chỉ trả về JSON, không có text giải thích thêm trước hoặc sau JSON."""


# ============================================================
# GEMINI VIDEO ANALYZER
# ============================================================

class GeminiVideoAnalyzer:
    """
    Phân tích video sử dụng Gemini API.
    
    Usage:
        analyzer = GeminiVideoAnalyzer()
        result = analyzer.analyze_video("path/to/video.mp4")
        
        if result["success"]:
            analysis = result["analysis"]  # VideoAnalysisResult
    """
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash"):
        """
        Khởi tạo Gemini Video Analyzer.
        
        Args:
            api_key: Optional API key. Lấy từ Config nếu không cung cấp.
            model_name: Gemini model để sử dụng
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai SDK not installed. Run: pip install google-genai")
        
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain not installed. Run: pip install langchain langchain-core")
        
        self.api_key = api_key or Config.GEMINI_API_KEY
        
        # Fallback: Try loading .env again if key is missing
        if not self.api_key:
            try:
                from dotenv import load_dotenv
                print("⚠️ [GEMINI_ANALYZER] API Key not found in Config, attempting manual .env load...")
                load_dotenv(override=True)
                self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            except Exception as e:
                print(f"❌ [GEMINI_ANALYZER] Fallback load failed: {e}")

        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY. Set it in .env file.")
        
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)
        self.uploader = GeminiFileUploader(api_key=self.api_key)
        
        # Initialize JSON parser with Pydantic schema
        self.json_parser = JsonOutputParser(pydantic_object=VideoAnalysisResult)
        
        print(f"✅ [GEMINI_ANALYZER] Initialized with model: {model_name}")
    
    def analyze_video(self, video_path: str, cleanup_after: bool = True) -> Dict:
        """
        Phân tích video và trả về structured result.
        
        Args:
            video_path: Đường dẫn file video local
            cleanup_after: Xóa file khỏi Gemini sau khi phân tích xong
        
        Returns:
            {
                "success": True/False,
                "analysis": VideoAnalysisResult (dict format),
                "file_uri": "files/...",
                "processing_time_ms": int,
                "error": str (nếu thất bại)
            }
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🎬 [GEMINI_ANALYZER] Starting Video Analysis")
        print(f"{'='*60}")
        print(f"   Video: {os.path.basename(video_path)}")
        print(f"   Model: {self.model_name}")
        
        file_name = None
        
        try:
            # Step 1: Upload video to Gemini
            print(f"\n📤 Step 1: Uploading video to Gemini...")
            upload_result = self.uploader.upload_video(video_path)
            
            if not upload_result.get("success"):
                raise GeminiUploadError(f"Upload failed: {upload_result.get('error')}")
            
            file_uri = upload_result["file_uri"]
            file_name = upload_result["file_name"]
            print(f"   ✅ Uploaded: {file_uri}")
            
            # Step 2: Build prompt with format instructions
            print(f"\n📝 Step 2: Building analysis prompt...")
            format_instructions = self.json_parser.get_format_instructions()
            prompt = ANALYSIS_PROMPT_TEMPLATE.format(format_instructions=format_instructions)
            
            # Step 3: Call Gemini with video + prompt
            print(f"\n🤖 Step 3: Calling Gemini for analysis...")
            
            # Create file reference for the uploaded video
            video_file = self.client.files.get(name=file_name)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_uri(
                                file_uri=video_file.uri,
                                mime_type=video_file.mime_type
                            ),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=8192,
                        system_instruction=SYSTEM_INSTRUCTION
                    )
            )
            
            # Step 4: Parse response
            print(f"\n📊 Step 4: Parsing response...")
            response_text = response.text
            
            # Try to extract JSON from response
            analysis_dict = self._extract_json(response_text)
            
            # Validate with Pydantic
            analysis = VideoAnalysisResult.model_validate(analysis_dict)
            
            # Calculate time range seconds if missing
            analysis_dict = self._enrich_time_data(analysis.model_dump())
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            print(f"\n{'='*60}")
            print(f"✅ [GEMINI_ANALYZER] Analysis Complete!")
            print(f"{'='*60}")
            print(f"   Title: {analysis_dict['general_info']['title']}")
            print(f"   Category: {analysis_dict['general_info']['category']}")
            print(f"   Viral Score: {analysis_dict['virality_factors']['score']}/10")
            print(f"   Segments: {len(analysis_dict['script_breakdown'])}")
            print(f"   Time: {processing_time_ms}ms")
            
            # Cleanup
            if cleanup_after and file_name:
                self.uploader.delete_file(file_name)
            
            return {
                "success": True,
                "analysis": analysis_dict,
                "file_uri": file_uri,
                "processing_time_ms": processing_time_ms,
                "analyzed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            import traceback
            print(f"\n❌ [GEMINI_ANALYZER] Error: {e}")
            traceback.print_exc()
            
            # Try cleanup on error
            if cleanup_after and file_name:
                try:
                    self.uploader.delete_file(file_name)
                except:
                    pass
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
    
    def _extract_json(self, text: str) -> Dict:
        """
        Extract JSON from response text.
        Handles cases where JSON is wrapped in markdown code blocks.
        """
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code block
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        raise ValueError(f"Could not extract valid JSON from response: {text[:500]}...")
    
    def _enrich_time_data(self, analysis_dict: Dict) -> Dict:
        """
        Enrich script_breakdown with start_seconds and end_seconds if missing.
        Parses time_range format "MM:SS - MM:SS" to seconds.
        """
        for segment in analysis_dict.get("script_breakdown", []):
            time_range = segment.get("time_range", "")
            
            if segment.get("start_seconds") is None or segment.get("end_seconds") is None:
                try:
                    # Parse "00:15 - 00:30" format
                    parts = time_range.split(" - ")
                    if len(parts) == 2:
                        start_parts = parts[0].strip().split(":")
                        end_parts = parts[1].strip().split(":")
                        
                        start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
                        end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])
                        
                        segment["start_seconds"] = start_seconds
                        segment["end_seconds"] = end_seconds
                except (ValueError, IndexError):
                    pass
        
        return analysis_dict
    
    def get_analysis_prompt(self) -> str:
        """
        Get the full analysis prompt (for debugging/testing).
        """
        format_instructions = self.json_parser.get_format_instructions()
        return ANALYSIS_PROMPT_TEMPLATE.format(format_instructions=format_instructions)


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def analyze_video(video_path: str, api_key: str = None) -> Dict:
    """
    Convenience function to analyze a video.
    
    Args:
        video_path: Path to video file
        api_key: Optional API key
    
    Returns:
        Analysis result dict
    """
    analyzer = GeminiVideoAnalyzer(api_key=api_key)
    return analyzer.analyze_video(video_path)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Gemini Video Analyzer Test")
    print("=" * 60)
    
    # Test video path
    test_video = r"E:\Tiktok_content_AI\scraper_data\content_files\tiktok_video_7296055437135252738.mp4"
    
    # Find any MP4 if test video doesn't exist
    if not os.path.exists(test_video):
        scraper_dir = r"E:\Tiktok_content_AI\scraper_data\content_files"
        if os.path.exists(scraper_dir):
            for f in os.listdir(scraper_dir):
                if f.endswith(".mp4"):
                    test_video = os.path.join(scraper_dir, f)
                    break
    
    if os.path.exists(test_video):
        print(f"\n📹 Testing with: {os.path.basename(test_video)}")
        print(f"   Size: {os.path.getsize(test_video) / (1024*1024):.1f}MB")
        
        try:
            analyzer = GeminiVideoAnalyzer()
            result = analyzer.analyze_video(test_video)
            
            if result["success"]:
                print(f"\n📊 Analysis Result:")
                analysis = result["analysis"]
                
                print(f"\n🎬 General Info:")
                print(f"   Title: {analysis['general_info']['title']}")
                print(f"   Category: {analysis['general_info']['category']}")
                print(f"   Sentiment: {analysis['general_info']['overall_sentiment']}")
                
                print(f"\n📝 Script Breakdown ({len(analysis['script_breakdown'])} segments):")
                for seg in analysis['script_breakdown'][:3]:  # Show first 3
                    print(f"   [{seg['time_range']}] {seg['visual_description'][:50]}...")
                
                print(f"\n🔥 Viral Score: {analysis['virality_factors']['score']}/10")
                print(f"   Reasons: {analysis['virality_factors']['reasons'][:100]}...")
                
                # Save full result
                output_path = r"E:\Tiktok_content_AI\temp\analysis_test_output.json"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n📁 Full result saved to: {output_path}")
                
            else:
                print(f"\n❌ Analysis failed: {result['error']}")
                
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ No test video found")
