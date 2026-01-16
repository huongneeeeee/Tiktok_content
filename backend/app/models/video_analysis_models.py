# backend/app/models/video_analysis_models.py
"""
Pydantic Models for Video Analysis Output

Defines structured output format for Gemini video analysis.
Used with LangChain JsonOutputParser to ensure consistent JSON responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================
# GENERAL INFO
# ============================================================

class GeneralInfo(BaseModel):
    """Thông tin chung về video."""
    
    title: str = Field(
        description="Tiêu đề video (nếu có hoặc AI tự đặt dựa trên nội dung)"
    )
    category: str = Field(
        description="Thể loại video: Vlog, Tutorial, Review, Drama, Ads, Entertainment, Education, etc."
    )
    overall_sentiment: str = Field(
        description="Cảm xúc chủ đạo: Hài hước, Nghiêm túc, Cảm động, Gay cấn, Vui vẻ, Buồn, etc."
    )
    target_audience: str = Field(
        description="Chân dung khán giả mục tiêu: độ tuổi, sở thích, hành vi, demographic"
    )


# ============================================================
# CONTENT ANALYSIS
# ============================================================

class ContentAnalysis(BaseModel):
    """Phân tích nội dung video."""
    
    main_objective: str = Field(
        description="Mục tiêu chính của video: Bán hàng, Branding, Giáo dục, Giải trí, Chia sẻ kinh nghiệm, etc."
    )
    key_message: str = Field(
        description="Thông điệp cốt lõi (Core Message) mà video muốn truyền tải"
    )
    hook_strategy: str = Field(
        description="Cách video giữ chân người xem trong 3-5 giây đầu tiên"
    )


# ============================================================
# SCRIPT BREAKDOWN
# ============================================================

class ScriptSegment(BaseModel):
    """Phân tích từng đoạn/scene trong video."""
    
    segment_id: int = Field(
        description="ID của đoạn (1, 2, 3...)"
    )
    time_range: str = Field(
        description="Khoảng thời gian của đoạn, format: '00:00 - 00:15'"
    )
    start_seconds: Optional[float] = Field(
        default=None,
        description="Thời điểm bắt đầu tính bằng giây (để video player seek)"
    )
    end_seconds: Optional[float] = Field(
        default=None,
        description="Thời điểm kết thúc tính bằng giây"
    )
    visual_description: str = Field(
        description="Mô tả chi tiết cảnh quay: người, vật, hành động, bối cảnh"
    )
    camera_angle: str = Field(
        description="Góc máy: Toàn cảnh, Trung cảnh, Cận cảnh, POV, Aerial, Tracking, etc."
    )
    audio_transcript: str = Field(
        description="Lời thoại hoặc mô tả âm thanh nền. Nếu là nhạc, ghi rõ thể loại"
    )
    on_screen_text: str = Field(
        description="Text xuất hiện trên màn hình (caption, subtitle, overlay text)"
    )
    pacing: str = Field(
        description="Nhịp độ của đoạn: Nhanh, Chậm, Dồn dập, Vừa phải, Tĩnh lặng"
    )


# ============================================================
# TECHNICAL AUDIT
# ============================================================

class TechnicalAudit(BaseModel):
    """Đánh giá kỹ thuật video."""
    
    editing_style: str = Field(
        description="Phong cách edit: Giật giật (jump cuts), Mượt mà, Minimalist, Cinematic, Raw, etc."
    )
    sound_design: str = Field(
        description="Đánh giá về âm thanh/nhạc nền: chất lượng, phù hợp, mixing"
    )
    cta_analysis: str = Field(
        description="Phân tích Call to Action: có CTA không, vị trí, độ hiệu quả"
    )
    video_quality: Optional[str] = Field(
        default=None,
        description="Chất lượng hình ảnh: độ phân giải, ánh sáng, màu sắc"
    )
    transitions: Optional[str] = Field(
        default=None,
        description="Các hiệu ứng chuyển cảnh được sử dụng"
    )


# ============================================================
# VIRALITY FACTORS
# ============================================================

class ViralityFactors(BaseModel):
    """Đánh giá tiềm năng viral của video."""
    
    score: int = Field(
        ge=1, le=10,
        description="Điểm dự đoán viral từ 1-10 (10 là cao nhất)"
    )
    reasons: str = Field(
        description="Lý do tại sao video này có thể viral hoặc không"
    )
    improvement_suggestions: str = Field(
        description="Đề xuất cải thiện video để tăng khả năng viral"
    )
    strengths: Optional[List[str]] = Field(
        default=None,
        description="Điểm mạnh của video"
    )
    weaknesses: Optional[List[str]] = Field(
        default=None,
        description="Điểm yếu cần cải thiện"
    )


# ============================================================
# COMPLETE VIDEO ANALYSIS RESULT
# ============================================================

class VideoAnalysisResult(BaseModel):
    """
    Kết quả phân tích video đầy đủ.
    
    Đây là schema chính được sử dụng với LangChain JsonOutputParser
    để đảm bảo Gemini trả về đúng format JSON.
    """
    
    general_info: GeneralInfo = Field(
        description="Thông tin chung về video"
    )
    content_analysis: ContentAnalysis = Field(
        description="Phân tích nội dung và mục tiêu video"
    )
    script_breakdown: List[ScriptSegment] = Field(
        description="Phân tích chi tiết từng đoạn trong video"
    )
    technical_audit: TechnicalAudit = Field(
        description="Đánh giá kỹ thuật sản xuất video"
    )
    virality_factors: ViralityFactors = Field(
        description="Đánh giá tiềm năng viral và đề xuất cải thiện"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "general_info": {
                    "title": "Cách làm bánh mì tại nhà siêu đơn giản",
                    "category": "Tutorial",
                    "overall_sentiment": "Vui vẻ, thân thiện",
                    "target_audience": "18-35 tuổi, thích nấu ăn, làm bánh tại nhà"
                },
                "content_analysis": {
                    "main_objective": "Giáo dục - hướng dẫn làm bánh mì",
                    "key_message": "Bất kỳ ai cũng có thể làm bánh mì ngon tại nhà",
                    "hook_strategy": "Mở đầu bằng cảnh bánh mì thành phẩm giòn rụm"
                },
                "script_breakdown": [
                    {
                        "segment_id": 1,
                        "time_range": "00:00 - 00:05",
                        "start_seconds": 0,
                        "end_seconds": 5,
                        "visual_description": "Cận cảnh ổ bánh mì vàng óng, giòn rụm",
                        "camera_angle": "Cận cảnh",
                        "audio_transcript": "Bánh mì làm tại nhà siêu đơn giản!",
                        "on_screen_text": "Bánh mì homemade 🍞",
                        "pacing": "Nhanh"
                    }
                ],
                "technical_audit": {
                    "editing_style": "Jump cuts nhanh, trend TikTok",
                    "sound_design": "Nhạc nền vui tươi, voice-over rõ ràng",
                    "cta_analysis": "CTA cuối video: Follow để xem thêm công thức"
                },
                "virality_factors": {
                    "score": 8,
                    "reasons": "Nội dung hữu ích, hook mạnh, editing trend",
                    "improvement_suggestions": "Thêm text overlay cho từng bước"
                }
            }
        }


# ============================================================
# REQUEST/RESPONSE MODELS FOR API
# ============================================================

class AnalyzeVideoRequest(BaseModel):
    """Request body cho analyze video endpoint."""
    
    video_id: Optional[str] = Field(
        default=None,
        description="ID của video đã upload"
    )
    video_path: Optional[str] = Field(
        default=None,
        description="Đường dẫn file video local"
    )
    video_url: Optional[str] = Field(
        default=None,
        description="URL của video (TikTok, YouTube)"
    )


class AnalyzeVideoResponse(BaseModel):
    """Response cho analyze video endpoint."""
    
    success: bool
    video_id: str
    analysis: Optional[VideoAnalysisResult] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None


class VideoSearchRequest(BaseModel):
    """Request body cho search videos endpoint."""
    
    query: str = Field(
        description="Search query (tìm trong title, category, key_message)"
    )
    category: Optional[str] = Field(
        default=None,
        description="Filter by category"
    )
    min_viral_score: Optional[int] = Field(
        default=None, ge=1, le=10,
        description="Minimum viral score filter"
    )
    limit: int = Field(
        default=20, ge=1, le=100,
        description="Number of results to return"
    )
    skip: int = Field(
        default=0, ge=0,
        description="Number of results to skip (pagination)"
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    # Test creating instance
    sample = VideoAnalysisResult(
        general_info=GeneralInfo(
            title="Test Video",
            category="Tutorial",
            overall_sentiment="Vui vẻ",
            target_audience="18-30 tuổi"
        ),
        content_analysis=ContentAnalysis(
            main_objective="Giáo dục",
            key_message="Học lập trình dễ dàng",
            hook_strategy="Câu hỏi gây tò mò"
        ),
        script_breakdown=[
            ScriptSegment(
                segment_id=1,
                time_range="00:00 - 00:10",
                start_seconds=0,
                end_seconds=10,
                visual_description="Intro",
                camera_angle="Cận cảnh",
                audio_transcript="Xin chào",
                on_screen_text="Welcome!",
                pacing="Vừa phải"
            )
        ],
        technical_audit=TechnicalAudit(
            editing_style="Minimalist",
            sound_design="Nhạc nhẹ nhàng",
            cta_analysis="Subscribe cuối video"
        ),
        virality_factors=ViralityFactors(
            score=7,
            reasons="Nội dung hữu ích",
            improvement_suggestions="Thêm effects"
        )
    )
    
    print("✅ VideoAnalysisResult created successfully")
    print(f"   JSON Schema: {len(sample.model_json_schema())} keys")
    
    # Get format instructions for LangChain
    from langchain_core.output_parsers import JsonOutputParser
    parser = JsonOutputParser(pydantic_object=VideoAnalysisResult)
    print(f"\n📝 Format Instructions Preview:")
    print(parser.get_format_instructions()[:500] + "...")
