# services/analyzer.py
"""
TikVault Refiner - Knowledge Card Generation Engine (OpenAI Version)
Biến video TikTok thành Knowledge Cards có cấu trúc để lưu trữ tri thức cá nhân.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Cấu hình OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================
# CÂY DANH MỤC TIKVAULT v2.0 (8 DANH MỤC GỐC)
# ============================================================

CATEGORY_TREE = {
    "HỌC_HỎI": {
        "desc": "Videos dạy kỹ năng, kiến thức có thể học hỏi và áp dụng",
        "icon": "📚",
        "subcategories": {
            "Tutorial": "Hướng dẫn từng bước, how-to, DIY, làm đồ handmade",
            "Ngôn_Ngữ": "Học tiếng Anh, Hàn, Nhật, Trung, từ vựng, ngữ pháp",
            "Tech_Review": "Review công nghệ, app, tool, software, unboxing",
            "Mẹo_Hay": "Life hacks, tips tiết kiệm, mẹo vặt, shortcuts",
            "Kiến_Thức": "Khoa học, lịch sử, giải thích hiện tượng, fact thú vị"
        }
    },
    "ẨM_THỰC": {
        "desc": "Mọi thứ liên quan đến ăn uống, nấu nướng",
        "icon": "🍳",
        "subcategories": {
            "Công_Thức": "Recipe chi tiết, cách làm món ăn, làm bánh",
            "Review_Quán": "Địa điểm ăn uống, nhà hàng, street food, quán mới",
            "Mẹo_Bếp": "Tips nấu ăn, bảo quản thực phẩm, dinh dưỡng",
            "Đồ_Uống": "Pha chế cà phê, trà, trà sữa, cocktail, smoothie",
            "Mukbang": "ASMR ăn, thử thách ăn, food challenge, ăn sập quán"
        }
    },
    "PHONG_CÁCH": {
        "desc": "Thời trang, làm đẹp, chăm sóc bản thân",
        "icon": "💄",
        "subcategories": {
            "Outfit": "OOTD, phối đồ, thời trang theo mùa, GRWM",
            "Makeup": "Trang điểm, tutorial makeup, biến hình, makeup trend",
            "Skincare": "Chăm sóc da, review mỹ phẩm, routine, serum/kem",
            "Tóc_Nail": "Kiểu tóc, nhuộm tóc, nail art, chăm sóc tóc",
            "Review_SP": "Đánh giá sản phẩm thời trang, mỹ phẩm, haul"
        }
    },
    "KHÁM_PHÁ": {
        "desc": "Du lịch, địa điểm, trải nghiệm mới lạ",
        "icon": "🌍",
        "subcategories": {
            "Điểm_Đến": "Check-in, địa điểm hot, hidden gems, cảnh đẹp",
            "Lưu_Trú": "Review khách sạn, resort, homestay, Airbnb",
            "Trải_Nghiệm": "Tour, activity, camping, phượt, roadtrip",
            "Ẩm_Thực_Local": "Đặc sản vùng miền, ăn gì ở đâu, food tour",
            "Tips_Du_Lịch": "Kinh nghiệm du lịch, packing, lịch trình, budget"
        }
    },
    "ĐỜI_THƯỜNG": {
        "desc": "Chia sẻ cuộc sống, vlog, câu chuyện hàng ngày",
        "icon": "📱",
        "subcategories": {
            "Vlog": "Daily vlog, một ngày của tôi, behind the scenes",
            "Gia_Đình": "Parenting, baby, thú cưng, mẹ bỉm sữa",
            "Tâm_Sự": "Chia sẻ câu chuyện, advice, confession, drama",
            "Công_Sở": "Tips làm việc, career, WFH, phỏng vấn, công việc",
            "Tin_Tức": "Thời sự, xu hướng, cập nhật tin hot, giải thích trend"
        }
    },
    "GIẢI_TRÍ": {
        "desc": "Xem cho vui, thư giãn, nội dung giải trí thuần túy",
        "icon": "🎬",
        "subcategories": {
            "Hài": "Comedy, sketch hài, prank, POV hài, parody",
            "Nhạc_Dance": "Cover nhạc, vũ đạo, dance challenge, karaoke",
            "Phim_Game": "Review phim, reaction, gaming, esports highlights",
            "Trend": "Meme, TikTok challenge, viral, edit CapCut sáng tạo",
            "Pets": "Video động vật cute, funny, chó mèo hài hước"
        }
    },
    "CẢM_XÚC": {
        "desc": "Nội dung thiên về cảm xúc, tâm trạng, mood",
        "icon": "❤️",
        "subcategories": {
            "Chill": "Aesthetic, lofi, cảnh đẹp, thư giãn, vibes",
            "Motivation": "Quotes động lực, năng lượng tích cực, khích lệ",
            "Tình_Yêu": "Couple, friendzone, chia tay, crush, tình cảm",
            "Healing": "Chữa lành, self-care mental, an ủi, ôm ấp",
            "Throwback": "Hoài niệm, kỷ niệm, nostalgia, hồi đó"
        }
    },
    "KHÁC": {
        "desc": "Video không thuộc danh mục nào hoặc không có giá trị",
        "icon": "📦",
        "subcategories": {
            "Quảng_Cáo": "Sponsored content, quảng cáo rõ ràng, promote",
            "Không_Rõ": "Nội dung mơ hồ, không xác định được chủ đề",
            "Rác": "Spam, lỗi kỹ thuật, không có nội dung, video test"
        }
    }
}


# ============================================================
# TIKVAULT REFINER SYSTEM PROMPT
# ============================================================

def _build_refiner_prompt():
    """
    Xây dựng System Prompt cho TikVault Refiner.
    
    CHIẾN LƯỢC PROMPT THÔNG MINH:
    - Prompt này hướng dẫn AI phân loại VÀ trích xuất trong 1 bước
    - Tùy theo category, AI sẽ tự điều chỉnh độ chi tiết của output:
      + NHÓM KIẾN THỨC (ẨM_THỰC, KHÁM_PHÁ, PHONG_CÁCH, HỌC_HỎI, ĐỜI_THƯỜNG): Trích xuất chi tiết
      + NHÓM GIẢI TRÍ (GIẢI_TRÍ, CẢM_XÚC, KHÁC): Chỉ cần summary ngắn gọn
    """
    
    # Build detailed category list with descriptions
    cat_details = ""
    for lvl0, data in CATEGORY_TREE.items():
        cat_details += f"\n### {data['icon']} {lvl0}\n"
        cat_details += f"**Mô tả**: {data['desc']}\n"
        cat_details += "**Subcategories**:\n"
        for sub, desc in data['subcategories'].items():
            cat_details += f"  - `{sub}`: {desc}\n"
    
    prompt = f"""# TikVault Knowledge Card Generator

Bạn là AI chuyên phân loại và trích xuất thông tin từ video TikTok.

---

## 📂 CÂY DANH MỤC CHI TIẾT
{cat_details}

---

## 🔍 BƯỚC 1: PHÂN LOẠI CHÍNH XÁC

### 1.1 Phân tích Hashtags (RẤT QUAN TRỌNG)
Hashtags là TÍN HIỆU MẠNH để xác định chủ đề. Phân tích theo nhóm:

| Nhóm Hashtag | Ví dụ | Gợi ý Category |
|--------------|-------|----------------|
| Ẩm thực | #recipe, #cooking, #reviewan, #domtui, #nauan | ẨM_THỰC |
| Du lịch | #travel, #checkin, #dulich, #vietnam, #review[địa điểm] | KHÁM_PHÁ |
| Làm đẹp | #makeup, #skincare, #ootd, #fashion, #grwm | PHONG_CÁCH |
| Học tập | #hoctienganh, #tips, #review[app/tool], #tutorial | HỌC_HỎI |
| Đời sống | #vlog, #daily, #momlife, #worklife, #tamsu | ĐỜI_THƯỜNG |
| Giải trí | #haihuoc, #trending, #challenge, #meme, #funny, #fyp | GIẢI_TRÍ |
| Cảm xúc | #chill, #motivation, #love, #sad, #healing | CẢM_XÚC |

⚠️ **LƯU Ý VỀ HASHTAGS**:
- `#fyp`, `#viral`, `#trending`, `#xuhuong` là hashtags SEO, KHÔNG dùng để phân loại
- Ưu tiên hashtags mô tả NỘI DUNG thực sự của video
- Nếu có nhiều hashtags, tìm NHÓM CHỦ ĐỀ CHÍNH (ví dụ: 3 hashtags về ẩm thực + 1 hashtag #fyp → ẨM_THỰC)

### 1.2 Quy tắc phân loại theo MỤC ĐÍCH CHÍNH của video

**Câu hỏi quyết định**: Video này MUỐN người xem làm gì?

| Mục đích chính | Category | Ví dụ |
|----------------|----------|-------|
| Học cách NẤU món ăn | ẨM_THỰC > Công_Thức | "Cách làm bánh flan" |
| Biết NƠI ĂN ngon | ẨM_THỰC > Review_Quán | "Review quán phở ngon quận 1" |
| Học cách TRANG ĐIỂM | PHONG_CÁCH > Makeup | "Tutorial makeup Hàn Quốc" |
| Biết ĐỊA ĐIỂM đẹp để đi | KHÁM_PHÁ > Điểm_Đến | "Check-in Đà Lạt" |
| Học một KỸ NĂNG/KIẾN THỨC | HỌC_HỎI | "Cách dùng ChatGPT" |
| Chia sẻ CUỘC SỐNG hàng ngày | ĐỜI_THƯỜNG > Vlog | "Một ngày của mình" |
| CHỈ ĐỂ GIẢI TRÍ, không học gì | GIẢI_TRÍ | Hài, meme, nhảy, trend |
| Tạo CẢM XÚC (không có action) | CẢM_XÚC | Quote động lực, video chill |

### 1.3 Các trường hợp DỄ NHẦM LẪN

| Trường hợp | Phân loại ĐÚNG | Giải thích |
|------------|----------------|------------|
| Tutorial nấu ăn | ẨM_THỰC > Công_Thức | ⚠️ KHÔNG phải HỌC_HỎI! |
| Review quán ăn ở Đà Nẵng | ẨM_THỰC > Review_Quán | Trừ khi focus vào DU LỊCH Đà Nẵng |
| Food tour Hội An | KHÁM_PHÁ > Ẩm_Thực_Local | Focus là KHÁM PHÁ địa phương |
| Video hài về nấu ăn | ẨM_THỰC hoặc GIẢI_TRÍ | Nếu có công thức → ẨM_THỰC, nếu chỉ hài → GIẢI_TRÍ |
| Vlog chia sẻ buồn | ĐỜI_THƯỜNG > Tâm_Sự | Có kể chuyện cá nhân |
| Video quote buồn với nhạc | CẢM_XÚC > Healing | Không có nội dung, chỉ mood |
| Video trend nhảy | GIẢI_TRÍ > Trend | Chỉ để giải trí |
| Video pets cute | GIẢI_TRÍ > Pets | Không có kiến thức nuôi thú cưng |
| Hướng dẫn nuôi mèo | HỌC_HỎI > Kiến_Thức | Có kiến thức thực tế |

---

## 📝 BƯỚC 2: TRÍCH XUẤT THEO NHÓM

### 🎓 LUỒNG 1: NHÓM KIẾN THỨC (Trích xuất CHI TIẾT)
**Áp dụng cho**: ẨM_THỰC, KHÁM_PHÁ, PHONG_CÁCH, HỌC_HỎI, ĐỜI_THƯỜNG

Với nhóm này, cần TRÍCH XUẤT ĐẦY ĐỦ thông tin có giá trị:

#### ẨM_THỰC
```
entities.ingredients: ["thịt bò 500g", "hành tây 2 củ", "nước mắm 2 muỗng"]
action_items: ["Bước 1: Ướp thịt với...", "Bước 2: Phi hành..."]
key_takeaways: ["Mẹo: Thịt mềm hơn khi...", "Lưu ý: Không nấu quá lâu"]
```

#### KHÁM_PHÁ
```
entities.locations: ["Quán Cô Ba - 123 Nguyễn Huệ, Q1, HCM", "Café The Latte - Thủ Đức"]
action_items: ["Đặt bàn trước qua Zalo", "Nên đi vào buổi sáng"]
key_takeaways: ["Giá trung bình 150k/người", "Mở cửa 7h-22h"]
```

#### PHONG_CÁCH
```
entities.products: ["Son MAC Ruby Woo", "Kem lót Maybelline Baby Skin", "Phấn phủ Innisfree No Sebum"]
action_items: ["Bước 1: Dưỡng ẩm trước", "Bước 2: Bôi kem lót", "Bước 3: Đánh cushion"]
key_takeaways: ["Mẹo: Xịt setting spray để lâu trôi", "Da dầu nên dùng phấn phủ kiềm dầu"]
```

#### HỌC_HỎI
```
entities.tools_software: ["ChatGPT (miễn phí)", "Notion AI ($10/tháng)", "Canva Pro"]
action_items: ["Bước 1: Tạo tài khoản", "Bước 2: Nhập prompt...", "Bước 3: Chỉnh sửa output"]
key_takeaways: ["Từ vựng: 'deadline' = hạn chót", "Công thức: Subject + Verb + Object"]
```

#### ĐỜI_THƯỜNG
```
action_items: ["Dậy sớm 5h mỗi ngày", "Tập thể dục 30 phút", "Đọc sách trước ngủ"]
key_takeaways: ["Bài học: Kiên trì quan trọng hơn hoàn hảo", "Insight: Thói quen tốt cần 21 ngày"]
```

---

### 🎬 LUỒNG 2: NHÓM GIẢI TRÍ (Chỉ cần TÓM TẮT)
**Áp dụng cho**: GIẢI_TRÍ, CẢM_XÚC, KHÁC

Với nhóm này, KHÔNG CẦN trích xuất chi tiết. Chỉ cần:

```
summary: "Video hài parody cảnh phỏng vấn xin việc với tình huống bất ngờ."
tags: ["hài", "parody", "phỏng vấn", "viral"]
key_takeaways: []  ← MẢNG RỖNG
action_items: []   ← MẢNG RỖNG
entities: {{}}      ← ĐỂ TRỐNG
```

**Tại sao?** Nhóm Giải trí không có thông tin cần lưu trữ để tra cứu sau. Chỉ cần summary để nhớ video nói gì.

---

## 📤 OUTPUT JSON FORMAT

```json
{{
  "category_path": "DANH_MỤC > Subcategory",
  "title": "Tiêu đề hấp dẫn, súc tích (tối đa 50 ký tự)",
  "summary": "2-3 câu tóm tắt nội dung chính của video",
  "key_takeaways": ["Điểm quan trọng 1", "Điểm 2", "..."],
  "action_items": ["Bước/Việc cần làm 1", "Bước 2", "..."],
  "entities": {{
    "ingredients": ["Nguyên liệu nếu là ẨM_THỰC"],
    "locations": ["Địa điểm nếu là KHÁM_PHÁ"],
    "products": ["Sản phẩm nếu là PHONG_CÁCH"],
    "tools_software": ["App/Tool nếu là HỌC_HỎI"]
  }},
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}
```

---

## ✅ CHECKLIST TRƯỚC KHI OUTPUT

1. ☐ Đã phân tích hashtags để xác định chủ đề?
2. ☐ Đã xác định MỤC ĐÍCH CHÍNH của video?
3. ☐ Category có đúng với nội dung thực tế không?
4. ☐ Nếu NHÓM KIẾN THỨC: Đã trích xuất đầy đủ entities, action_items, key_takeaways?
5. ☐ Nếu NHÓM GIẢI TRÍ: Đã để mảng rỗng cho entities, action_items, key_takeaways?
6. ☐ Chỉ trả JSON, không có text khác?"""
    
    return prompt


# ============================================================
# AGGREGATED TEXT BUILDER - Tính trọng số theo content type
# ============================================================

def build_aggregated_text(content_type: str, ocr_text: str, transcript: str, caption: str) -> dict:
    """
    Xây dựng AGGREGATED_TEXT theo trọng số dựa trên content_type.
    
    CÔNG THỨC:
    - VIDEO: 40% OCR + 40% Transcript + 20% Caption
    - PHOTO: 70% OCR + 30% Caption (không có transcript)
    
    Returns:
        {
            "aggregated_text": str,
            "weights": {"ocr": float, "transcript": float, "caption": float},
            "sources_available": ["ocr", "transcript", "caption"]
        }
    """
    # Normalize inputs
    ocr_text = (ocr_text or "").strip()
    transcript = (transcript or "").strip()
    caption = (caption or "").strip()
    
    sources_available = []
    if ocr_text:
        sources_available.append("ocr")
    if transcript:
        sources_available.append("transcript")
    if caption:
        sources_available.append("caption")
    
    # Determine weights based on content_type
    if content_type == "photo":
        # PHOTO: OCR là chính (70%), Caption phụ (30%)
        weights = {"ocr": 0.7, "transcript": 0.0, "caption": 0.3}
    else:
        # VIDEO: OCR và Transcript ngang nhau (40% mỗi), Caption 20%
        weights = {"ocr": 0.4, "transcript": 0.4, "caption": 0.2}
    
    # Build aggregated text with priority markers
    parts = []
    
    if content_type == "photo":
        # Photo: OCR first, then caption
        if ocr_text:
            parts.append(f"[OCR - TRỌNG SỐ 70%]:\n{ocr_text}")
        if caption:
            parts.append(f"[CAPTION - TRỌNG SỐ 30%]:\n{caption}")
    else:
        # Video: OCR và Transcript có trọng số bằng nhau
        if ocr_text:
            parts.append(f"[OCR - TRỌNG SỐ 40%]:\n{ocr_text}")
        if transcript:
            parts.append(f"[TRANSCRIPT - TRỌNG SỐ 40%]:\n{transcript}")
        if caption:
            parts.append(f"[CAPTION - TRỌNG SỐ 20%]:\n{caption}")
    
    aggregated_text = "\n\n".join(parts) if parts else ""
    
    return {
        "aggregated_text": aggregated_text,
        "weights": weights,
        "sources_available": sources_available,
        "content_type": content_type
    }


# ============================================================
# HÀM PHÂN TÍCH CHÍNH - KNOWLEDGE CARD GENERATOR
# ============================================================

def analyze_video_content(transcript: str, metadata: dict, ocr_result: dict = None, custom_tree: dict = None):
    """
    TikVault Refiner: Phân tích video và tạo Knowledge Card (OpenAI Version).
    
    Args:
        transcript: Transcript từ STT
        metadata: Video metadata
        ocr_result: OCR data từ ocr_processor (optional)
        custom_tree: Custom category tree (optional)
    """
    # Validate Input
    ocr_text = ""
    if ocr_result and ocr_result.get("ocr_text"):
        ocr_text = ocr_result.get("ocr_text", "")
    
    has_content = transcript or metadata.get('title') or metadata.get('hashtags') or ocr_text
    if not has_content:
        print("   ⚠️ No content to analyze")
        return _default_result()
    
    # Build System Prompt
    system_instruction = _build_refiner_prompt()
    
    # Build User Prompt
    author_info = metadata.get('author', {})
    author_name = author_info.get('nickname', 'Unknown') if isinstance(author_info, dict) else str(author_info)
    
    hashtags = metadata.get('hashtags', [])
    if isinstance(hashtags, list):
        hashtags_str = ', '.join(hashtags) if hashtags else 'Không có hashtags'
    else:
        hashtags_str = str(hashtags) if hashtags else 'Không có hashtags'
    
    has_transcript = bool(transcript and len(transcript.strip()) > 10)
    has_ocr = bool(ocr_text and len(ocr_text.strip()) > 5)
    
    # Determine content_type from metadata
    content_type = "photo" if metadata.get("slideshow_images") else "video"
    caption = metadata.get('title', '')
    
    # Build AGGREGATED_TEXT with weights
    agg_result = build_aggregated_text(
        content_type=content_type,
        ocr_text=ocr_text[:2000] if ocr_text else "",
        transcript=transcript[:8000] if transcript else "",
        caption=caption
    )
    
    aggregated_text = agg_result["aggregated_text"]
    weights = agg_result["weights"]
    sources = agg_result["sources_available"]
    
    # Build weight explanation for prompt
    weight_explanation = f"""
## TRỌNG SỐ PHÂN LOẠI (Content Type: {content_type.upper()})

Các nguồn thông tin có sẵn: {', '.join(sources) if sources else 'Không có'}

Trọng số áp dụng:
- OCR: {int(weights['ocr'] * 100)}%
- Transcript: {int(weights['transcript'] * 100)}%  
- Caption: {int(weights['caption'] * 100)}%

**QUAN TRỌNG:**
- KHÔNG phân loại chỉ dựa vào caption
- OCR và Transcript là CHỨNG CỨ CHÍNH, không phải phụ trợ
- Photo → OCR là tín hiệu CHÍNH
- Video → OCR và Transcript quan trọng ngang nhau
- Phân loại dựa trên ngữ nghĩa tổng hợp, không dựa keyword đơn lẻ
"""
    
    # Build user prompt with aggregated text
    user_prompt = f"""
METADATA:
- Author: @{author_name}
- Content Type: {content_type.upper()}
- Hashtags: {hashtags_str}
- Duration: {metadata.get('duration', 'N/A')}s

{weight_explanation}

## NỘI DUNG ĐÃ TỔNG HỢP (AGGREGATED_TEXT):

{aggregated_text if aggregated_text else "Không có nội dung text"}

---

Dựa trên AGGREGATED_TEXT ở trên, hãy:
1. Hiểu mục đích nội dung chính
2. So khớp với CÂY DANH MỤC TIKVAULT (LV0 → LV1)
3. Chọn 1 main_category và 1 sub_category phù hợp nhất
4. Trả về confidence trong khoảng 0.0 → 1.0, dựa trên:
   - Mức độ rõ ràng của nội dung
   - Sự đồng thuận giữa OCR / Transcript / Caption
   - Có hay không tín hiệu mâu thuẫn

Trả về JSON theo format đã định nghĩa, BẮT BUỘC thêm field "confidence": 0.0-1.0
"""
    
    try:
        print(f"   🧠 Generating Knowledge Card (OpenAI)...")
        print(f"   📝 Has transcript: {has_transcript}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        card = json.loads(response.choices[0].message.content)
        
        # Parse category_path and clean emoji prefixes
        category_path = card.get("category_path", "KHÁC > Không_Rõ")
        parts = [p.strip() for p in category_path.split(">")]
        
        # Strip emoji prefix (e.g., "📚 HỌC_HỎI" -> "HỌC_HỎI")
        import re
        def clean_category(cat):
            # Remove emoji and leading/trailing whitespace
            return re.sub(r'^[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+\s*', '', cat).strip()
        
        level_1 = clean_category(parts[0]) if len(parts) > 0 else "KHÁC"
        level_2 = clean_category(parts[1]) if len(parts) > 1 else "Không_Rõ"
        
        # Get confidence from AI response (default 0.7 if not provided)
        confidence = card.get("confidence", 0.7)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except:
                confidence = 0.7
        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
        
        # Log
        print(f"   📂 Category: {category_path}")
        print(f"   🎯 Confidence: {confidence:.2f}")
        print(f"   📦 Content Type: {content_type}")
        
        return {
            "knowledge_card": card,
            "summary": card.get("summary", ""),
            "classification": {
                "level_1": level_1,
                "level_2": level_2,
                "category_path": category_path,
                "confidence": confidence,
                "content_type": content_type
            },
            "aggregation_info": {
                "weights": weights,
                "sources_available": sources
            },
            "rag_data": {
                "ingredients": card.get("entities", {}).get("ingredients", []),
                "steps": card.get("action_items", []),
                "products": card.get("entities", {}).get("products", []),
                "locations": card.get("entities", {}).get("locations", []),
                "tools": card.get("entities", {}).get("tools_software", []),
                "tips": card.get("key_takeaways", [])
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        
        if "429" in error_msg or "rate" in error_msg.lower():
            print(f"   ⚠️ Rate limit! Waiting 30s...")
            import time
            time.sleep(30)
            
            try:
                print(f"   🔄 Retrying...")
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                card = json.loads(response.choices[0].message.content)
                category_path = card.get("category_path", "KHÁC > Không_Rõ")
                parts = [p.strip() for p in category_path.split(">")]
                level_1 = parts[0] if len(parts) > 0 else "KHÁC"
                level_2 = parts[1] if len(parts) > 1 else "Không_Rõ"
                
                return {
                    "knowledge_card": card,
                    "summary": card.get("summary", ""),
                    "classification": {"level_1": level_1, "level_2": level_2, "category_path": category_path},
                    "rag_data": {
                        "ingredients": card.get("entities", {}).get("ingredients", []),
                        "steps": card.get("action_items", []),
                        "products": card.get("entities", {}).get("products", []),
                        "locations": card.get("entities", {}).get("locations", []),
                        "tools": card.get("entities", {}).get("tools_software", []),
                        "tips": card.get("key_takeaways", [])
                    }
                }
            except Exception as retry_error:
                print(f"   ❌ Retry failed: {retry_error}")
                return _default_result_quota()
        
        print(f"❌ OpenAI Error: {e}")
        import traceback
        traceback.print_exc()
        return _default_result()


def _default_result():
    """Trả về kết quả mặc định khi có lỗi"""
    return {
        "knowledge_card": {
            "category_path": "KHÁC > Rác",
            "title": "Không thể phân tích",
            "summary": "Video không thể phân tích hoặc không có nội dung.",
            "key_takeaways": [],
            "action_items": [],
            "entities": {"tools_software": [], "locations": [], "products": [], "ingredients": []},
            "tags": []
        },
        "summary": "Không thể phân tích nội dung",
        "classification": {"level_1": "KHÁC", "level_2": "Rác", "category_path": "KHÁC > Rác"},
        "rag_data": {}
    }


def _default_result_quota():
    """Trả về kết quả khi API quota exceeded"""
    return {
        "knowledge_card": {
            "category_path": "KHÁC > Không_Rõ",
            "title": "Đang chờ xử lý",
            "summary": "Video đã lưu nhưng chưa phân tích do API limit. Thử lại sau.",
            "key_takeaways": [],
            "action_items": [],
            "entities": {"tools_software": [], "locations": [], "products": [], "ingredients": []},
            "tags": ["pending"]
        },
        "summary": "Chờ phân tích",
        "classification": {"level_1": "KHÁC", "level_2": "Không_Rõ", "category_path": "KHÁC > Không_Rõ"},
        "rag_data": {}
    }


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_category_tree():
    """Lấy cây danh mục hiện tại"""
    return CATEGORY_TREE


def get_all_categories():
    """Lấy danh sách tất cả categories (Level 0)"""
    return list(CATEGORY_TREE.keys())


def get_subcategories(level_0: str):
    """Lấy subcategories của một Level 0"""
    return list(CATEGORY_TREE.get(level_0, {}).get("subcategories", {}).keys())


def validate_category(level_0: str, level_1: str) -> bool:
    """Kiểm tra category có hợp lệ không"""
    if level_0 not in CATEGORY_TREE:
        return False
    return level_1 in CATEGORY_TREE[level_0].get("subcategories", {})


def get_knowledge_grade(kd_score: int, ac_score: int) -> str:
    """Convert scores to letter grade"""
    avg = (kd_score + ac_score) / 2
    if avg >= 8.5: return "A"
    elif avg >= 7: return "B"
    elif avg >= 5: return "C"
    elif avg >= 3: return "D"
    else: return "F"


def get_category_icon(category: str) -> str:
    """Get icon for category"""
    return CATEGORY_TREE.get(category, {}).get("icon", "📁")
