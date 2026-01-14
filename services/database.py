# services/database.py
"""
TikVault Database Service
Handles MongoDB collections and Qdrant vector database
"""

import os
import sys
import hashlib
import requests
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import Config
try:
    from config import Config
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config

_global_model = None
_global_reranker = None


class TikVaultDB:
    """
    Database service cho TikVault
    Quản lý 4 MongoDB collections + Qdrant vector DB
    """
    
    def __init__(self):
        print("   🔹 [INIT] Đang khởi động Database Service...")
        
        self.mongo_uri = Config.MONGO_URI
        self.db = None
        
        # MongoDB Collections
        self.users: Optional[Collection] = None
        self.videos: Optional[Collection] = None
        self.categories: Optional[Collection] = None
        self.search_logs: Optional[Collection] = None
        self.user_collections: Optional[Collection] = None  # Knowledge collections
        
        self._connect_mongo()
        
        # Qdrant Vector DB
        self.vector_collection = "video_chunks_bge_m3"
        self.qdrant_client = self._connect_qdrant()
        
        # ML Models
        self.model_path = os.path.join(Config.MODEL_DIR, "bge-m3")
        self.model = self._load_model()
        self.reranker = self._load_reranker()
        
        # Text Splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50, 
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    # ================================================
    # CONNECTION METHODS
    # ================================================
    
    def _connect_mongo(self):
        """Kết nối MongoDB và tạo các collections với indexes"""
        try:
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=3000)
            client.server_info()
            
            self.db = client["tikvault_db"]
            
            # Init collections
            self.users = self.db["users"]
            self.videos = self.db["videos"]
            self.categories = self.db["categories"]
            self.search_logs = self.db["search_logs"]
            self.user_collections = self.db["user_collections"]
            
            # Create indexes
            self._create_indexes()
            
            # Seed default categories if empty
            self._seed_categories()
            
            print("   ✅ [MONGO] Connected to tikvault_db")
            
        except Exception as e:
            print(f"   ❌ Lỗi kết nối MongoDB: {e}")
    
    def _create_indexes(self):
        """Tạo indexes cho tất cả collections"""
        try:
            # Users indexes
            self.users.create_index("email", unique=True)
            self.users.create_index([("oauth_provider", 1), ("oauth_id", 1)], sparse=True)
            
            # Videos indexes
            self.videos.create_index("video_id", unique=True)
            self.videos.create_index("user_id")
            self.videos.create_index("ai_analysis.classification.level_1")
            self.videos.create_index([("processed_at", DESCENDING)])
            self.videos.create_index([("title", TEXT), ("transcript", TEXT)])
            
            # Categories indexes
            self.categories.create_index("key", unique=True)
            self.categories.create_index([("order", ASCENDING)])
            
            # Search logs indexes
            self.search_logs.create_index("user_id")
            self.search_logs.create_index([("created_at", DESCENDING)])
            
            # User collections indexes
            self.user_collections.create_index("user_id")
            self.user_collections.create_index([("updated_at", DESCENDING)])
            self.search_logs.create_index([("query", TEXT)])
            
        except Exception as e:
            print(f"   ⚠️ Index creation warning: {e}")
    
    def _seed_categories(self):
        """Seed default categories nếu collection trống - v2.0 (8 categories)"""
        if self.categories.count_documents({}) > 0:
            return
        
        default_categories = [
            {
                "key": "HỌC_HỎI",
                "name": "Học Hỏi",
                "description": "Videos dạy kỹ năng, kiến thức có thể học hỏi và áp dụng",
                "icon": "fa-graduation-cap",
                "color": "#3b82f6",
                "order": 1,
                "subcategories": [
                    {"key": "Tutorial", "name": "Tutorial", "tags": ["Hướng_dẫn", "How_to", "DIY"]},
                    {"key": "Ngôn_Ngữ", "name": "Ngôn Ngữ", "tags": ["Tiếng_Anh", "Hàn", "Nhật", "Từ_vựng"]},
                    {"key": "Tech_Review", "name": "Tech Review", "tags": ["Công_nghệ", "App", "Unboxing"]},
                    {"key": "Mẹo_Hay", "name": "Mẹo Hay", "tags": ["Life_hacks", "Tips", "Tiết_kiệm"]},
                    {"key": "Kiến_Thức", "name": "Kiến Thức", "tags": ["Khoa_học", "Lịch_sử", "Facts"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "ẨM_THỰC",
                "name": "Ẩm Thực",
                "description": "Mọi thứ liên quan đến ăn uống, nấu nướng",
                "icon": "fa-utensils",
                "color": "#f59e0b",
                "order": 2,
                "subcategories": [
                    {"key": "Công_Thức", "name": "Công Thức", "tags": ["Recipe", "Món_ăn", "Làm_bánh"]},
                    {"key": "Review_Quán", "name": "Review Quán", "tags": ["Địa_điểm_ăn", "Street_food", "Quán_mới"]},
                    {"key": "Mẹo_Bếp", "name": "Mẹo Bếp", "tags": ["Tips_nấu_ăn", "Bảo_quản", "Dinh_dưỡng"]},
                    {"key": "Đồ_Uống", "name": "Đồ Uống", "tags": ["Cà_phê", "Trà_sữa", "Cocktail"]},
                    {"key": "Mukbang", "name": "Mukbang", "tags": ["ASMR", "Thử_thách_ăn", "Food_challenge"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "PHONG_CÁCH",
                "name": "Phong Cách",
                "description": "Thời trang, làm đẹp, chăm sóc bản thân",
                "icon": "fa-wand-magic-sparkles",
                "color": "#ec4899",
                "order": 3,
                "subcategories": [
                    {"key": "Outfit", "name": "Outfit", "tags": ["OOTD", "Phối_đồ", "GRWM"]},
                    {"key": "Makeup", "name": "Makeup", "tags": ["Trang_điểm", "Tutorial", "Biến_hình"]},
                    {"key": "Skincare", "name": "Skincare", "tags": ["Chăm_da", "Review_mỹ_phẩm", "Routine"]},
                    {"key": "Tóc_Nail", "name": "Tóc & Nail", "tags": ["Kiểu_tóc", "Nail_art", "Nhuộm_tóc"]},
                    {"key": "Review_SP", "name": "Review SP", "tags": ["Thời_trang", "Mỹ_phẩm", "Haul"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "KHÁM_PHÁ",
                "name": "Khám Phá",
                "description": "Du lịch, địa điểm, trải nghiệm mới lạ",
                "icon": "fa-earth-asia",
                "color": "#10b981",
                "order": 4,
                "subcategories": [
                    {"key": "Điểm_Đến", "name": "Điểm Đến", "tags": ["Check_in", "Hidden_gems", "Cảnh_đẹp"]},
                    {"key": "Lưu_Trú", "name": "Lưu Trú", "tags": ["Khách_sạn", "Resort", "Homestay"]},
                    {"key": "Trải_Nghiệm", "name": "Trải Nghiệm", "tags": ["Tour", "Camping", "Phượt"]},
                    {"key": "Ẩm_Thực_Local", "name": "Ẩm Thực Local", "tags": ["Đặc_sản", "Food_tour", "Ăn_vùng_miền"]},
                    {"key": "Tips_Du_Lịch", "name": "Tips Du Lịch", "tags": ["Kinh_nghiệm", "Packing", "Budget"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "ĐỜI_THƯỜNG",
                "name": "Đời Thường",
                "description": "Chia sẻ cuộc sống, vlog, câu chuyện hàng ngày",
                "icon": "fa-house",
                "color": "#8b5cf6",
                "order": 5,
                "subcategories": [
                    {"key": "Vlog", "name": "Vlog", "tags": ["Daily_life", "BTS", "Một_ngày"]},
                    {"key": "Gia_Đình", "name": "Gia Đình", "tags": ["Parenting", "Baby", "Thú_cưng"]},
                    {"key": "Tâm_Sự", "name": "Tâm Sự", "tags": ["Chia_sẻ", "Advice", "Confession"]},
                    {"key": "Công_Sở", "name": "Công Sở", "tags": ["Career", "WFH", "Phỏng_vấn"]},
                    {"key": "Tin_Tức", "name": "Tin Tức", "tags": ["Thời_sự", "Xu_hướng", "Cập_nhật"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "GIẢI_TRÍ",
                "name": "Giải Trí",
                "description": "Xem cho vui, thư giãn, nội dung giải trí thuần túy",
                "icon": "fa-face-laugh",
                "color": "#f472b6",
                "order": 6,
                "subcategories": [
                    {"key": "Hài", "name": "Hài", "tags": ["Comedy", "Prank", "POV_hài"]},
                    {"key": "Nhạc_Dance", "name": "Nhạc & Dance", "tags": ["Cover", "Vũ_đạo", "Challenge"]},
                    {"key": "Phim_Game", "name": "Phim & Game", "tags": ["Review_phim", "Gaming", "Esports"]},
                    {"key": "Trend", "name": "Trend", "tags": ["Meme", "Viral", "CapCut"]},
                    {"key": "Pets", "name": "Pets", "tags": ["Động_vật", "Cute", "Funny"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "CẢM_XÚC",
                "name": "Cảm Xúc",
                "description": "Nội dung thiên về cảm xúc, tâm trạng, mood",
                "icon": "fa-heart",
                "color": "#a855f7",
                "order": 7,
                "subcategories": [
                    {"key": "Chill", "name": "Chill", "tags": ["Aesthetic", "Lofi", "Thư_giãn"]},
                    {"key": "Motivation", "name": "Motivation", "tags": ["Động_lực", "Quotes", "Năng_lượng"]},
                    {"key": "Tình_Yêu", "name": "Tình Yêu", "tags": ["Couple", "Chia_tay", "Crush"]},
                    {"key": "Healing", "name": "Healing", "tags": ["Chữa_lành", "Self_care", "An_ủi"]},
                    {"key": "Throwback", "name": "Throwback", "tags": ["Hoài_niệm", "Kỷ_niệm", "Nostalgia"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "key": "KHÁC",
                "name": "Khác",
                "description": "Video không thuộc danh mục nào hoặc không có giá trị",
                "icon": "fa-box",
                "color": "#6b7280",
                "order": 8,
                "subcategories": [
                    {"key": "Quảng_Cáo", "name": "Quảng Cáo", "tags": ["Sponsored", "Ads", "Promote"]},
                    {"key": "Không_Rõ", "name": "Không Rõ", "tags": ["Chưa_phân_loại", "Mơ_hồ"]},
                    {"key": "Rác", "name": "Rác", "tags": ["Spam", "Lỗi", "Test"]}
                ],
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        try:
            self.categories.insert_many(default_categories)
            print("   ✅ [MONGO] Seeded default categories")
        except Exception as e:
            print(f"   ⚠️ Category seeding warning: {e}")
    
    def _connect_qdrant(self):
        """Kết nối Qdrant vector database"""
        try:
            client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)
            try:
                collections = client.get_collections()
                exists = any(c.name == self.vector_collection for c in collections.collections)
                if not exists:
                    client.create_collection(
                        collection_name=self.vector_collection,
                        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
                    )
                    print(f"   ✅ [QDRANT] Created collection: {self.vector_collection}")
            except:
                pass
            return client
        except Exception as e:
            print(f"   ❌ Lỗi kết nối Qdrant: {e}")
            return None
    
    def _load_model(self):
        """Load embedding model"""
        global _global_model
        if _global_model:
            return _global_model
        
        print(f"   🔹 [EMBED] Đang khởi tạo model Embedding...")
        try:
            if os.path.exists(self.model_path):
                print(f"   -> Load local: {self.model_path}")
                model = SentenceTransformer(self.model_path)
            else:
                print(f"   -> Load HuggingFace (BAAI/bge-m3)...")
                model = SentenceTransformer('BAAI/bge-m3')
                model.save(self.model_path)
            _global_model = model
            print("   ✅ Đã load xong model Embedding.")
            return model
        except Exception as e:
            print(f"❌ Lỗi tải Model: {e}")
            return None
    
    def _load_reranker(self):
        """Load reranker model"""
        global _global_reranker
        if _global_reranker:
            return _global_reranker
        try:
            print("   🔹 [RERANK] Đang tải model Reranker...")
            reranker = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2')
            _global_reranker = reranker
            return reranker
        except:
            return None
    
    # ================================================
    # VIDEO METHODS
    # ================================================
    
    def save_video(self, video_data: Dict, user_id: str = None) -> bool:
        """Lưu video vào MongoDB và Qdrant"""
        video_id = video_data.get("id") or video_data.get("video_id")
        if not video_id:
            return False
        
        # Chuẩn hóa document
        now = datetime.utcnow()
        doc = {
            "video_id": str(video_id),
            "user_id": user_id,
            "type": video_data.get("type", "video"),
            "title": video_data.get("title", ""),
            "original_url": video_data.get("original_url", ""),
            "filename": video_data.get("filename", ""),
            "author": video_data.get("author", {}),
            "stats": video_data.get("stats", {}),
            "transcript": video_data.get("transcript", ""),
            "hashtags": video_data.get("hashtags", []),
            "ai_analysis": video_data.get("ai_analysis", {}),
            "ocr_data": video_data.get("ocr_data", {}),  # OCR data from PaddleOCR
            "drive_links": video_data.get("drive_links", {}),
            "local_path": video_data.get("local_path", ""),
            "is_slideshow": video_data.get("is_slideshow", False),
            "slideshow_images": video_data.get("slideshow_images", []),
            "thumbnail": video_data.get("thumbnail"),
            "duration": video_data.get("duration"),
            "music_title": video_data.get("music_title"),
            "create_time": video_data.get("create_time"),
            "processed_at": video_data.get("processed_at", now),
            "updated_at": now
        }
        
        # Save to MongoDB
        if self.videos is not None:
            try:
                self.videos.update_one(
                    {"video_id": str(video_id)},
                    {"$set": doc},
                    upsert=True
                )
            except Exception as e:
                print(f"   ❌ Lỗi Mongo Write: {e}")
        
        # Save to Qdrant
        if self.qdrant_client is not None and self.model:
            self._save_video_embeddings(video_id, video_data)
        
        return True
    
    def _save_video_embeddings(self, video_id: str, video_data: Dict):
        """
        Lưu embeddings vào Qdrant với Knowledge Card data.
        
        Strategy: Embed summary + key_takeaways instead of raw transcript
        → Better search quality, less noise, more focused results
        """
        try:
            ai_analysis = video_data.get('ai_analysis', {})
            knowledge_card = ai_analysis.get('knowledge_card', {})
            
            # Get Knowledge Card fields
            kc_title = knowledge_card.get('title', video_data.get('title', ''))
            kc_summary = knowledge_card.get('summary', ai_analysis.get('summary', ''))
            kc_takeaways = knowledge_card.get('key_takeaways', [])
            kc_action_items = knowledge_card.get('action_items', [])
            kc_tags = knowledge_card.get('tags', [])
            category_path = knowledge_card.get('category_path', '') or ai_analysis.get('classification', {}).get('category_path', '')
            
            # Scores
            scores = ai_analysis.get('scores', {})
            knowledge_density = scores.get('knowledge_density', knowledge_card.get('knowledge_density', 5))
            actionability = scores.get('actionability', knowledge_card.get('actionability', 5))
            
            # Build semantic content for embedding
            # Format: Title + Category + Summary + Key Takeaways + Tags + OCR
            takeaways_text = "; ".join(kc_takeaways) if kc_takeaways else ""
            actions_text = "; ".join(kc_action_items) if kc_action_items else ""
            tags_text = ", ".join(kc_tags) if kc_tags else ""
            
            # Get OCR text if available (NEW)
            ocr_data = video_data.get("ocr_data", {})
            ocr_text = ocr_data.get("ocr_text", "")[:500] if ocr_data else ""  # Limit to 500 chars
            
            # Primary chunk: Summary + Key Takeaways + OCR (most important for search)
            primary_content = f"""
Tiêu đề: {kc_title}
Danh mục: {category_path}
Tóm tắt: {kc_summary}
Điểm chính: {takeaways_text}
Tags: {tags_text}
""".strip()
            
            # Add OCR text to primary content if available
            if ocr_text:
                primary_content += f"\nText trên màn hình: {ocr_text}"
            
            # Optional: Action items as second chunk if substantial
            chunks_to_embed = [primary_content]
            if actions_text and len(kc_action_items) >= 3:
                action_chunk = f"""
Tiêu đề: {kc_title}
Hướng dẫn thực hiện: {actions_text}
Danh mục: {category_path}
""".strip()
                chunks_to_embed.append(action_chunk)
            
            # Build Qdrant points
            points = []
            for idx, content in enumerate(chunks_to_embed):
                vector = self.get_embedding(content)
                
                payload = {
                    "video_id": str(video_id),
                    "title": video_data.get("title"),
                    "refined_title": kc_title,
                    "author": video_data.get("author", {}),
                    "chunk_text": content,
                    "summary": kc_summary,
                    "key_takeaways": kc_takeaways,
                    "filename": video_data.get("filename"),
                    "drive_links": video_data.get("drive_links", {}),
                    "stats": video_data.get("stats", {}),
                    "category_path": category_path,
                    "category_l1": ai_analysis.get("classification", {}).get("level_1", ""),
                    "knowledge_density": knowledge_density,
                    "actionability": actionability,
                    "tags": kc_tags
                }
                
                point_id = self._get_chunk_id(video_id, idx)
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))
            
            if points:
                self.qdrant_client.upsert(
                    collection_name=self.vector_collection,
                    points=points
                )
                print(f"   ✅ [DB] Saved {len(points)} Knowledge Card chunks to Qdrant.")
                
        except Exception as e:
            print(f"   ❌ Lỗi Qdrant Write: {e}")
    
    def get_video(self, video_id: str) -> Optional[Dict]:
        """Lấy video theo ID"""
        if not self.videos:
            return None
        return self.videos.find_one({"video_id": str(video_id)})
    
    def get_videos_by_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Lấy danh sách video của user"""
        if not self.videos:
            return []
        return list(self.videos.find(
            {"user_id": user_id}
        ).sort("processed_at", DESCENDING).limit(limit))
    
    def get_videos_by_category(self, category_key: str, limit: int = 50) -> List[Dict]:
        """Lấy videos theo category"""
        if not self.videos:
            return []
        return list(self.videos.find(
            {"ai_analysis.classification.level_1": category_key}
        ).sort("processed_at", DESCENDING).limit(limit))
    
    # ================================================
    # SEARCH METHODS
    # ================================================
    
    def _get_chunk_id(self, video_id_str, chunk_index):
        """Generate chunk ID từ video_id và chunk index"""
        raw_key = f"{video_id_str}_{chunk_index}"
        hex_digest = hashlib.md5(raw_key.encode('utf-8')).hexdigest()
        return int(hex_digest, 16) % (2**64)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector từ text"""
        if not text or not self.model:
            return [0.0] * 1024
        return self.model.encode(text).tolist()
    
    def search_videos(self, query_text: str, user_id: str = None, limit: int = 3) -> List[Dict]:
        """
        Hybrid Search: Qdrant semantic search + MongoDB metadata lookup
        1. Get relevant video_ids from Qdrant vector search
        2. Fetch full metadata from MongoDB
        3. Return top results with complete information
        """
        if self.qdrant_client is None or self.videos is None:
            print("❌ Search unavailable: Qdrant or MongoDB not connected")
            return []
        
        print(f"🔎 Hybrid Search: {query_text}")
        
        try:
            # Step 1: Get embedding for query
            query_vector = self.get_embedding(query_text)
            qdrant_results = []
            
            # Step 2: Search in Qdrant for relevant video chunks
            try:
                qdrant_results = self.qdrant_client.search(
                    collection_name=self.vector_collection,
                    query_vector=query_vector,
                    limit=limit * 3  # Get more to deduplicate
                )
            except AttributeError:
                # Fallback to REST API
                print("   ⚠️ Lib Error: Fallback to HTTP API...")
                url = f"http://{Config.QDRANT_HOST}:{Config.QDRANT_PORT}/collections/{self.vector_collection}/points/search"
                payload = {
                    "vector": query_vector,
                    "limit": limit * 3,
                    "with_payload": True
                }
                response = requests.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    from types import SimpleNamespace
                    for item in data.get('result', []):
                        hit = SimpleNamespace()
                        hit.score = item.get('score')
                        hit.payload = item.get('payload', {})
                        qdrant_results.append(hit)
            
            if not qdrant_results:
                print("   ⚠️ No Qdrant results, falling back to MongoDB text search")
                # Fallback: Simple MongoDB text search
                mongo_results = list(self.videos.find(
                    {"$text": {"$search": query_text}}
                ).limit(limit))
                
                # If no text index, try regex search on title
                if not mongo_results:
                    import re
                    mongo_results = list(self.videos.find({
                        "$or": [
                            {"title": {"$regex": query_text, "$options": "i"}},
                            {"transcript": {"$regex": query_text, "$options": "i"}}
                        ]
                    }).limit(limit))
                
                return self._format_mongo_results(mongo_results)
            
            # Step 3: Detect category intent from query
            # Map keywords to categories for category-aware filtering
            CATEGORY_KEYWORDS = {
                # KIẾN_THỨC
                "tin tức": ("KIẾN_THỨC", "Tin_tức"),
                "thời sự": ("KIẾN_THỨC", "Tin_tức"),
                "news": ("KIẾN_THỨC", "Tin_tức"),
                "review": ("KIẾN_THỨC", "Review_Sản_phẩm"),
                "đánh giá": ("KIẾN_THỨC", "Review_Sản_phẩm"),
                "mẹo": ("KIẾN_THỨC", "Mẹo_vặt"),
                "tips": ("KIẾN_THỨC", "Mẹo_vặt"),
                "hướng dẫn": ("KIẾN_THỨC", "Giáo_dục"),
                "học": ("KIẾN_THỨC", "Giáo_dục"),
                # ẨM_THỰC
                "nấu ăn": ("ẨM_THỰC", "Nấu_ăn"),
                "công thức": ("ẨM_THỰC", "Nấu_ăn"),
                "cách làm": ("ẨM_THỰC", "Nấu_ăn"),
                "món ăn": ("ẨM_THỰC", "Nấu_ăn"),
                "bánh": ("ẨM_THỰC", "Nấu_ăn"),
                "quán": ("ẨM_THỰC", "Review_Quán"),
                "nhà hàng": ("ẨM_THỰC", "Review_Quán"),
                "mukbang": ("ẨM_THỰC", "Mukbang"),
                # ĐỜI_SỐNG
                "outfit": ("ĐỜI_SỐNG", "Phong_cách"),
                "phối đồ": ("ĐỜI_SỐNG", "Phong_cách"),
                "thời trang": ("ĐỜI_SỐNG", "Phong_cách"),
                "ootd": ("ĐỜI_SỐNG", "Phong_cách"),
                "vlog": ("ĐỜI_SỐNG", "Vlog_Đời_thường"),
                # DU_LỊCH
                "du lịch": ("DU_LỊCH", "Địa_điểm"),
                "đi chơi": ("DU_LỊCH", "Địa_điểm"),
                "check in": ("DU_LỊCH", "Địa_điểm"),
                "resort": ("DU_LỊCH", "Resort_Khách_sạn"),
                "khách sạn": ("DU_LỊCH", "Resort_Khách_sạn"),
                "kinh nghiệm đi": ("DU_LỊCH", "Kinh_nghiệm"),
                # GIẢI_TRÍ
                "hài": ("GIẢI_TRÍ", "Hài_hước"),
                "funny": ("GIẢI_TRÍ", "Hài_hước"),
                "game": ("GIẢI_TRÍ", "Game"),
                "phim": ("GIẢI_TRÍ", "Phim_ảnh"),
                "nhảy": ("GIẢI_TRÍ", "Trình_diễn"),
                "dance": ("GIẢI_TRÍ", "Trình_diễn"),
                # CẢM_XÚC
                "chill": ("CẢM_XÚC", "Chill"),
                "động lực": ("CẢM_XÚC", "Động_lực"),
                "motivation": ("CẢM_XÚC", "Động_lực"),
            }
            
            # Detect category from query
            query_lower = query_text.lower()
            detected_category = None
            detected_subcategory = None
            
            for keyword, (cat, subcat) in CATEGORY_KEYWORDS.items():
                if keyword in query_lower:
                    detected_category = cat
                    detected_subcategory = subcat
                    print(f"   📂 Detected category intent: {cat} > {subcat}")
                    break
            
            # Step 4: Extract unique video_ids with best scores
            # Higher threshold to filter truly irrelevant results
            MIN_SCORE_THRESHOLD = 0.45  # Slightly lower to allow category filtering
            
            video_scores = {}
            video_categories = {}  # Track categories for each video
            
            for hit in qdrant_results:
                vid_id = hit.payload.get("video_id") or hit.payload.get("id")
                score = hit.score
                
                # Only include results above threshold
                if vid_id and score >= MIN_SCORE_THRESHOLD:
                    if vid_id not in video_scores or score > video_scores[vid_id]:
                        video_scores[vid_id] = score
                        # Store category info from payload if available
                        video_categories[vid_id] = hit.payload.get("category_l1", "")
            
            # If no results pass threshold, lower it slightly for best match only
            if not video_scores and qdrant_results:
                best_hit = max(qdrant_results, key=lambda x: x.score)
                if best_hit.score >= 0.35:  # At least 35% for fallback
                    vid_id = best_hit.payload.get("video_id") or best_hit.payload.get("id")
                    if vid_id:
                        video_scores[vid_id] = best_hit.score
                        print(f"   ⚠️ Fallback: Using best match with {best_hit.score*100:.0f}% score")
            
            # Step 5: Fetch metadata and apply category filtering
            results_with_meta = []
            for vid_id, score in video_scores.items():
                video_doc = self.videos.find_one({"video_id": vid_id})
                if video_doc:
                    # Get video's category
                    ai_analysis = video_doc.get("ai_analysis", {})
                    classification = ai_analysis.get("classification", {})
                    video_cat = classification.get("level_1", "")
                    video_subcat = classification.get("level_2", "")
                    
                    # Boost score if category matches detected intent
                    boost = 1.0
                    if detected_category:
                        if video_cat == detected_category:
                            boost = 1.3  # 30% boost for matching category
                            if video_subcat == detected_subcategory:
                                boost = 1.5  # 50% boost for exact subcategory match
                        else:
                            boost = 0.5  # Penalize non-matching categories
                    
                    adjusted_score = score * boost
                    
                    results_with_meta.append({
                        "video_id": vid_id,
                        "original_score": score,
                        "score": adjusted_score,
                        "video_doc": video_doc,
                        "category_match": video_cat == detected_category if detected_category else True
                    })
            
            # Sort by adjusted score and filter
            results_with_meta.sort(key=lambda x: x["score"], reverse=True)
            
            # If category was detected, ONLY return videos that match the category
            if detected_category:
                matching_results = [r for r in results_with_meta if r["category_match"]]
                if matching_results:
                    top_results = matching_results[:limit]
                    print(f"   ✅ Filtered to {len(top_results)} videos matching category: {detected_category}")
                else:
                    # No exact matches, show best results with warning
                    top_results = results_with_meta[:limit]
                    print(f"   ⚠️ No videos in category {detected_category}, showing best available")
            else:
                top_results = results_with_meta[:limit]
            
            # Log filtering stats
            original_count = len(qdrant_results)
            print(f"   → Found {len(top_results)} relevant videos (from {original_count} candidates, threshold {MIN_SCORE_THRESHOLD*100:.0f}%)")
            
            # Step 6: Format results for return
            results = []
            for item in top_results:
                video_doc = item["video_doc"]
                results.append({
                    "video_id": item["video_id"],
                    "score": item["score"],
                    "title": video_doc.get("title", ""),
                    "author": video_doc.get("author", {}),
                    "transcript": video_doc.get("transcript", ""),  # Full transcript for RAG
                    "thumbnail": video_doc.get("thumbnail"),
                    "filename": video_doc.get("filename"),
                    "is_slideshow": video_doc.get("is_slideshow", False),
                    "slideshow_images": video_doc.get("slideshow_images", []),
                    "stats": video_doc.get("stats", {}),
                    "ai_analysis": video_doc.get("ai_analysis", {}),
                    "drive_links": video_doc.get("drive_links", {}),
                    "duration": video_doc.get("duration"),
                    "original_url": video_doc.get("original_url")
                })
            
            print(f"   ✅ Returning {len(results)} videos with full metadata")
            return results
            
        except Exception as e:
            print(f"❌ Hybrid Search Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _format_mongo_results(self, mongo_results: List) -> List[Dict]:
        """Format MongoDB results for fallback search"""
        results = []
        for doc in mongo_results:
            results.append({
                "video_id": doc.get("video_id"),
                "score": 1.0,  # Default score for text search
                "title": doc.get("title", ""),
                "author": doc.get("author", {}),
                "transcript": doc.get("transcript", "")[:200] + "..." if doc.get("transcript") else "",
                "thumbnail": doc.get("thumbnail"),
                "filename": doc.get("filename"),
                "is_slideshow": doc.get("is_slideshow", False),
                "slideshow_images": doc.get("slideshow_images", []),
                "stats": doc.get("stats", {}),
                "ai_analysis": doc.get("ai_analysis", {}),
                "drive_links": doc.get("drive_links", {}),
                "duration": doc.get("duration"),
                "original_url": doc.get("original_url")
            })
        return results
    
    def _log_search(self, query: str, user_id: str, hits: List):
        """Log search query for analytics"""
        if self.search_logs is None:
            return
        try:
            self.search_logs.insert_one({
                "user_id": user_id,
                "query": query,
                "results_count": len(hits),
                "result_ids": [h.get("video_id") for h in hits if isinstance(h, dict)],
                "created_at": datetime.utcnow()
            })
        except:
            pass
    
    # ================================================
    # CATEGORY METHODS
    # ================================================
    
    def get_categories(self, active_only: bool = True) -> List[Dict]:
        """Lấy danh sách categories"""
        if not self.categories:
            return []
        query = {"is_active": True} if active_only else {}
        return list(self.categories.find(query).sort("order", ASCENDING))
    
    def get_category(self, key: str) -> Optional[Dict]:
        """Lấy category theo key"""
        if not self.categories:
            return None
        return self.categories.find_one({"key": key})
    
    # ================================================
    # LEGACY METHODS (backward compatibility)
    # ================================================
    
    def store_embedding(self, full_text: str, payload_info: Dict) -> bool:
        """Legacy method - redirect to save_video"""
        video_data = {
            "id": payload_info.get("id") or payload_info.get("video_id"),
            "title": payload_info.get("title"),
            "transcript": full_text,
            "author": {"nickname": payload_info.get("author", {}).get("nickname", "Unknown")},
        }
        video_data.update(payload_info)
        return self.save_video(video_data)
    
    def reset_database(self):
        """Reset tất cả data (DANGEROUS!)"""
        print("⚠️ [RESET] Resetting DB...")
        
        if self.videos is not None:
            self.videos.delete_many({})
        if self.search_logs is not None:
            self.search_logs.delete_many({})
        # Không xóa users và categories
        
        if self.qdrant_client:
            try:
                self.qdrant_client.delete_collection(self.vector_collection)
                self.qdrant_client.create_collection(
                    collection_name=self.vector_collection,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
            except:
                pass
        
        print("   ✅ Database Cleaned (videos + search_logs).")