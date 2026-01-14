# services/llm_chat.py
"""
TikVault LLM Chat - RAG Answer Generation (OpenAI Version)
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Cấu hình OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def expand_query(original_query):
    """
    Kỹ thuật Query Expansion: Sử dụng AI để sinh ra các biến thể tìm kiếm.
    Kết hợp: Từ đồng nghĩa + Từ cụ thể hóa + Từ liên quan ngữ cảnh.
    """
    try:
        prompt = f"""
        Đóng vai một chuyên gia tối ưu hóa công cụ tìm kiếm (SEO) cho nền tảng Video ngắn.
        Nhiệm vụ: Mở rộng câu truy vấn của người dùng thành 3 phiên bản khác nhau để tăng khả năng tìm kiếm Vector (Semantic Search).
        
        Chiến lược mở rộng:
        1. Biến thể 1: Dùng từ đồng nghĩa hoặc từ chuyên môn chính xác hơn.
        2. Biến thể 2: Cụ thể hóa câu hỏi (thêm các từ như "cách làm", "hướng dẫn", "review").
        3. Biến thể 3: Dùng từ lóng, từ viết tắt hoặc ngôn ngữ nói thường gặp trên TikTok.

        VÍ DỤ MẪU (FEW-SHOT):
        Input: "cách làm món cuốn"
        Output:
        - công thức làm gỏi cuốn tôm thịt
        - hướng dẫn làm bánh tráng cuốn
        - cách pha nước chấm món cuốn ngon

        Input: "đi đà lạt mặc gì"
        Output:
        - phối đồ đi đà lạt cho nữ
        - outfit check in đà lạt sống ảo
        - gợi ý trang phục du lịch mùa lạnh

        Input: "{original_query}"
        Output (Chỉ trả về 3 dòng kết quả, không giải thích gì thêm):
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=200
        )
        
        # Xử lý text trả về (tách dòng, xóa gạch đầu dòng)
        variations = []
        for line in response.choices[0].message.content.split('\n'):
            clean_line = line.strip().replace('- ', '').replace('* ', '')
            if clean_line:
                variations.append(clean_line)
        
        # Luôn luôn thêm câu gốc vào danh sách
        variations.append(original_query)
        
        # Lọc trùng lặp và lấy tối đa 4 câu
        return list(set(variations))

    except Exception as e:
        print(f"⚠️ Lỗi Expand Query: {e}")
        return [original_query]


def generate_rag_answer(user_query, search_results, conversation_history=None):
    """
    Generate detailed AI answer using RAG with full transcript context (OpenAI Version)
    Supports multi-turn conversation with optional history.
    """
    if not search_results:
        return "Xin lỗi, tôi không tìm thấy video nào liên quan đến câu hỏi của bạn."

    # Build comprehensive context from search results
    context_parts = []
    
    for idx, item in enumerate(search_results):
        video_num = idx + 1
        title = item.get('title', 'Không có tiêu đề')
        
        # Author info
        author = item.get('author', {})
        author_name = author.get('nickname', 'Unknown') if isinstance(author, dict) else str(author)
        
        # Full transcript
        transcript = item.get('transcript', '')
        if transcript and len(transcript) > 500:
            transcript = transcript[:1500]
        
        # AI analysis data - Support both old and new format
        ai_analysis = item.get('ai_analysis', {})
        
        # Try new Knowledge Card format first
        knowledge_card = ai_analysis.get('knowledge_card', {})
        if knowledge_card:
            ai_summary = knowledge_card.get('summary', '')
            key_takeaways = knowledge_card.get('key_takeaways', [])
            action_items = knowledge_card.get('action_items', [])
            entities = knowledge_card.get('entities', {})
            
            structured_info = ""
            if key_takeaways:
                structured_info += f"\n   • Điểm chính: {'; '.join(key_takeaways)}"
            if action_items:
                structured_info += f"\n   • Các bước: {'; '.join(action_items[:5])}"
            if entities.get('ingredients'):
                structured_info += f"\n   • Nguyên liệu: {', '.join(entities['ingredients'])}"
            if entities.get('products'):
                structured_info += f"\n   • Sản phẩm: {', '.join(entities['products'])}"
            if entities.get('locations'):
                structured_info += f"\n   • Địa điểm: {', '.join(entities['locations'])}"
        else:
            # Fallback to old format
            ai_summary = ai_analysis.get('summary', '') or ai_analysis.get('meta', {}).get('summary', '')
            rag_data = ai_analysis.get('rag_data', {})
            
            structured_info = ""
            if rag_data:
                if rag_data.get('ingredients'):
                    structured_info += f"\n   • Nguyên liệu: {', '.join(rag_data['ingredients'])}"
                if rag_data.get('steps'):
                    structured_info += f"\n   • Các bước: {'; '.join(rag_data['steps'][:5])}"
                if rag_data.get('products'):
                    structured_info += f"\n   • Sản phẩm: {', '.join(rag_data['products'])}"
                if rag_data.get('locations'):
                    structured_info += f"\n   • Địa điểm: {', '.join(rag_data['locations'])}"
                if rag_data.get('tips'):
                    structured_info += f"\n   • Mẹo hay: {', '.join(rag_data['tips'])}"
        
        # Classification
        classification = ai_analysis.get('classification', {})
        category = classification.get('category_path', '') or classification.get('level_1', '')
        
        context_parts.append(f"""
═══════════════════════════════════════
📹 VIDEO {video_num}: {title}
👤 Tác giả: @{author_name}
📂 Danh mục: {category}
───────────────────────────────────────
🤖 TÓM TẮT AI: {ai_summary}
{f"📋 THÔNG TIN CHI TIẾT:{structured_info}" if structured_info else ""}
───────────────────────────────────────
📝 NỘI DUNG ĐẦY ĐỦ (TRANSCRIPT):
{transcript if transcript else "[Không có transcript]"}
═══════════════════════════════════════
""")

    full_context = "\n".join(context_parts)

    system_prompt = """Bạn là TikVault AI Assistant - chuyên gia phân tích nội dung video TikTok.
Nhiệm vụ: Trả lời câu hỏi của người dùng dựa trên DỮ LIỆU VIDEO một cách CHI TIẾT và CỤ THỂ.

Nguyên tắc:
1. ĐỌC KỸ TRANSCRIPT - Đây là nguồn thông tin chính xác nhất
2. TRÍCH DẪN NGUỒN - Ghi [Video 1], [Video 2] khi lấy thông tin
3. CỤ THỂ VÀ CHI TIẾT - Đưa ra số liệu, tên gọi, bước làm cụ thể
4. KHÔNG bịa thông tin - Chỉ dựa vào dữ liệu được cung cấp
5. Trả lời bằng tiếng Việt, thân thiện, dễ hiểu"""

    user_prompt = f"""# CÂU HỎI
"{user_query}"

# DỮ LIỆU VIDEO THAM KHẢO
{full_context}

Hãy trả lời câu hỏi dựa trên dữ liệu video trên."""

    try:
        # Build messages with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 6 messages (3 turns)
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current user query with context
        messages.append({"role": "user", "content": user_prompt})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=2500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Lỗi OpenAI RAG: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, hệ thống AI đang bận. Vui lòng thử lại sau."


# ============================================================
# PHASE 3: PLANNER AGENT
# ============================================================

PLANNING_KEYWORDS = [
    "lên kế hoạch", "plan ", "lịch trình", "hành trình", "gợi ý lịch",
    "itinerary", "ngày 1", "ngày 2", "đi chơi", "du lịch", "trip",
    "ở đâu ăn gì", "2 ngày", "3 ngày", "cuối tuần", "weekend",
    "địa điểm", "quán ăn", "checklist", "kế hoạch"
]


def detect_planning_intent(query):
    """
    Detect if the query is asking for a plan/itinerary.
    Returns True if planning mode should be activated.
    """
    query_lower = query.lower()
    for keyword in PLANNING_KEYWORDS:
        if keyword in query_lower:
            return True
    return False


def generate_travel_plan(user_query, search_results, conversation_history=None):
    """
    Planner Agent: Synthesize multiple videos into a structured travel/activity plan.
    """
    if not search_results:
        return "Xin lỗi, tôi không tìm thấy đủ thông tin trong thư viện video để lập kế hoạch."

    # Build comprehensive video data
    video_data = []
    for idx, item in enumerate(search_results):
        ai_analysis = item.get('ai_analysis', {})
        knowledge_card = ai_analysis.get('knowledge_card', {})
        classification = ai_analysis.get('classification', {})
        
        video_info = {
            "video_num": idx + 1,
            "title": knowledge_card.get('title') or item.get('title', 'Untitled'),
            "category": classification.get('category_path', 'N/A'),
            "summary": knowledge_card.get('summary', ai_analysis.get('summary', '')),
            "locations": knowledge_card.get('entities', {}).get('locations', []),
            "ingredients": knowledge_card.get('entities', {}).get('ingredients', []),
            "products": knowledge_card.get('entities', {}).get('products', []),
            "key_takeaways": knowledge_card.get('key_takeaways', []),
            "action_items": knowledge_card.get('action_items', []),
            "tags": knowledge_card.get('tags', [])
        }
        video_data.append(video_info)

    # Format video context for planner
    video_context = ""
    for v in video_data:
        video_context += f"""
═══════════════════════════════════════
📹 VIDEO {v['video_num']}: {v['title']}
📂 Danh mục: {v['category']}
📝 Tóm tắt: {v['summary']}
📍 Địa điểm: {', '.join(v['locations']) if v['locations'] else 'N/A'}
💡 Highlights: {', '.join(v['key_takeaways'][:3]) if v['key_takeaways'] else 'N/A'}
🏷️ Tags: {', '.join(v['tags']) if v['tags'] else 'N/A'}
═══════════════════════════════════════
"""

    system_prompt = """Bạn là TikVault Travel Planner - chuyên gia lập kế hoạch du lịch và trải nghiệm.
Nhiệm vụ: Tổng hợp thông tin từ nhiều video TikTok để tạo ra KẾ HOẠCH CỤ THỂ.

NGUYÊN TẮC LẬP KẾ HOẠCH:
1. Sắp xếp theo THỜI GIAN hợp lý (sáng → trưa → chiều → tối)
2. Ghi RÕ nguồn video cho mỗi gợi ý: [Video X]
3. Ước tính THỜI GIAN và CHI PHÍ nếu có thông tin
4. Thêm TIPS từ các video vào kế hoạch

FORMAT OUTPUT:
📅 **NGÀY 1: [Chủ đề]**

🌅 **Sáng:**
- [Hoạt động 1] [Video X]
- [Hoạt động 2] [Video Y]

🌞 **Trưa:**
- [Địa điểm ăn trưa] [Video Z]

🌆 **Chiều - Tối:**
- [Hoạt động] [Video X]

💡 **Tips:**
- [Mẹo từ video]

📅 **NGÀY 2: [Chủ đề]**
...

💰 **Ước tính chi phí:** [nếu có]
⚠️ **Lưu ý:** [những điều cần chú ý]"""

    user_prompt = f"""# YÊU CẦU LẬP KẾ HOẠCH
"{user_query}"

# DỮ LIỆU TỪ CÁC VIDEO ĐÃ LƯU
{video_context}

Hãy tổng hợp thông tin từ các video trên và tạo kế hoạch chi tiết.
Nhớ ghi [Video X] sau mỗi gợi ý để người dùng biết nguồn."""

    try:
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-4:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        messages.append({"role": "user", "content": user_prompt})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4,
            max_tokens=3000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Lỗi Planner: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, không thể tạo kế hoạch lúc này. Vui lòng thử lại."


def generate_comparison(user_query, videos, conversation_history=None):
    """
    Generate comparison analysis between multiple videos.
    Used when user selects multiple videos and clicks Compare.
    """
    if len(videos) < 2:
        return "Cần ít nhất 2 video để so sánh."
    
    # Build context for each video
    video_summaries = []
    for idx, video in enumerate(videos):
        num = idx + 1
        title = video.get('title', 'Không có tiêu đề')
        
        # Get transcript for deep comparison
        transcript = video.get('transcript', '')
        if transcript and len(transcript) > 2000:
            transcript = transcript[:2000] + "...(đã cắt bớt)"
        elif not transcript:
            transcript = "[Không có transcript]"

        ai_analysis = video.get('ai_analysis', {})
        knowledge_card = ai_analysis.get('knowledge_card', {})
        
        summary = knowledge_card.get('summary', ai_analysis.get('summary', ''))
        category_path = knowledge_card.get('category_path', 
                         ai_analysis.get('classification', {}).get('category_path', 'Chưa phân loại'))
        key_takeaways = knowledge_card.get('key_takeaways', [])
        action_items = knowledge_card.get('action_items', [])
        
        entities = knowledge_card.get('entities', {})
        ingredients = entities.get('ingredients', [])
        locations = entities.get('locations', [])
        products = entities.get('products', [])
        
        video_info = f"""
### Video {num}: {title}
- **Danh mục:** {category_path}
- **Tóm tắt:** {summary}
- **Điểm chính:** {', '.join(map(str, key_takeaways)) if key_takeaways else 'Không có'}
- **Các bước:** {', '.join(map(str, action_items)) if action_items else 'Không có'}

#### Chi tiết Entities:
{f"- Nguyên liệu: {', '.join(map(str, ingredients))}" if ingredients else ""}
{f"- Địa điểm: {', '.join(map(str, locations))}" if locations else ""}
{f"- Sản phẩm: {', '.join(map(str, products))}" if products else ""}

#### Transcript (Trích đoạn):
{transcript}
--------------------------------------------------
"""
        video_summaries.append(video_info)
    
    videos_context = "\n".join(video_summaries)
    
    system_prompt = """Bạn là TikVault Expert - chuyên gia phân tích và so sánh nội dung video.
Nhiệm vụ: So sánh các video được cung cấp và đưa ra phân tích chi tiết, sâu sắc.

Cấu trúc trả lời:
1. **Tổng quan:** Nêu ngắn gọn chủ đề chung của các video.
2. **So sánh chi tiết:** (Tạo bảng hoặc danh sách so sánh)
   - **Về Nội dung/Phương pháp:** Cách làm khác nhau thế nào? Nguyên liệu/Công cụ khác nhau ra sao?
   - **Về Phong cách:** Tone giọng, cách truyền đạt, độ chi tiết.
   - **Về Thông tin:** Video nào có thông tin độc đáo mà video kia không có?
3. **Ưu điểm & Nhược điểm:** Phân tích điểm mạnh/yếu của từng video.
4. **Kết luận & Đề xuất:** 
   - [Video X] phù hợp cho ai/trường hợp nào?
   - [Video Y] phù hợp cho ai/trường hợp nào?

Sử dụng [Video X] để chỉ rõ nguồn.
Hãy phân tích SÂU dựa trên transcript và các bước thực hiện cụ thể, không chỉ nói chung chung."""

    user_prompt = f"""# YÊU CẦU SO SÁNH
"{user_query}"

# DỮ LIỆU CÁC VIDEO
{videos_context}

Hãy phân tích và so sánh các video trên một cách chi tiết nhất có thể."""

    try:
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history[-4:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        messages.append({"role": "user", "content": user_prompt})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Lỗi Compare: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, không thể so sánh video lúc này. Vui lòng thử lại."