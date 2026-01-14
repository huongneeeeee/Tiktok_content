# 📱 TIKVAULT - HƯỚNG DẪN SỬ DỤNG GIAO DIỆN NGƯỜI DÙNG

## 📋 Mục Lục
1. [Tổng Quan](#1-tổng-quan)
2. [Trang Dashboard](#2-trang-dashboard)
3. [Trang Library (Thư Viện)](#3-trang-library-thư-viện)
4. [Trang Video Detail (Chi Tiết Video)](#4-trang-video-detail-chi-tiết-video)
5. [Trang Search (Tìm Kiếm AI)](#5-trang-search-tìm-kiếm-ai)
6. [Tính Năng Chung](#6-tính-năng-chung)

---

## 1. Tổng Quan

**TikVault** là ứng dụng quản lý và lưu trữ video TikTok thông minh với khả năng:
- Tải và lưu trữ video TikTok
- Tự động phân tích nội dung bằng AI
- Phân loại video theo chủ đề
- Tìm kiếm thông minh với AI

### Giao Diện Chính
| Trang | Đường dẫn | Mô tả |
|-------|-----------|-------|
| Dashboard | `/` | Trang chủ, hiển thị tất cả video |
| Library | `/library` | Thư viện phân loại theo danh mục |
| Video Detail | `/video/{id}` | Chi tiết từng video |
| Search | `/search` | Tìm kiếm AI thông minh |

---

## 2. Trang Dashboard

### 📍 Truy cập: URL gốc `/`

### Mô tả
Trang chủ hiển thị tất cả video đã import dưới dạng lưới (grid).

### Thành Phần Giao Diện

#### 🔹 Sidebar (Thanh bên trái)
- **Logo TikVault**: Click để về trang chủ
- **Dashboard**: Xem tất cả video (active)
- **Import Video**: Mở popup nhập video mới
- **Library**: Đến trang thư viện phân loại
- **Search**: Đến trang tìm kiếm AI

#### 🔹 Header (Thanh trên)
- **Ô tìm kiếm**: Tìm kiếm nhanh video
- **Nút Reset Database**: Xóa toàn bộ dữ liệu (cẩn thận!)
- **Avatar người dùng**: Menu dropdown

#### 🔹 Video Grid (Lưới video)
Mỗi video card hiển thị:
- **Thumbnail**: Hình ảnh/video preview
  - Video: Hiển thị frame đầu tiên
  - Slideshow: Hiển thị ảnh đầu với badge "📷 [số ảnh]"
- **Duration**: Thời lượng video
- **Title**: Tiêu đề video (tối đa 2 dòng)
- **Views/Likes**: Số lượt xem và thích

#### 🔹 Nút "Upload New"
Card đặc biệt để import video mới.

### Các Hành Động

| Hành động | Cách thực hiện |
|-----------|----------------|
| Import video | Click "Import Video" hoặc card "Upload New" |
| Xem chi tiết | Click vào video card |
| Tìm kiếm | Nhập từ khóa + Enter |
| Sắp xếp | Chọn dropdown: Newest/Oldest/Most Views/Most Likes |
| Reset DB | Click biểu tượng thùng rác (❗cần xác nhận 2 lần) |

### 📥 Import Video Modal
1. Dán URL TikTok vào ô input
2. Click "Import"
3. Chờ xử lý qua 4 bước:
   - Đang tải video...
   - Đang transcript audio...
   - AI đang phân tích...
   - Lưu vào database...

---

## 3. Trang Library (Thư Viện)

### 📍 Truy cập: `/library`

### Mô tả
Thư viện video được phân loại theo danh mục (Category) và danh mục con (Subcategory).

### Thành Phần Giao Diện

#### 🔹 Breadcrumb (Đường dẫn)
Hiển thị vị trí hiện tại: `Library > [Category] > [Subcategory]`

#### 🔹 Category Tabs (Tab danh mục)
- **Tất cả**: Xem toàn bộ video
- Các tab danh mục với icon và số lượng video

#### 🔹 Subcategory Chips (Chips danh mục con)
Khi chọn Category, hiển thị các chip subcategory để lọc sâu hơn.

#### 🔹 Video Grid với Multi-Select
Mỗi video card có:
- **Checkbox chọn**: Góc trên trái (ẩn mặc định)
- Thumbnail, badge duration/type
- Views, title, author avatar

### Tính Năng Multi-Select

#### ⚡ Chọn nhiều video
- Click checkbox góc trên trái mỗi video
- **Giới hạn**: Tối đa **5 video** cùng lúc
- Khi chọn, thanh công cụ nổi xuất hiện phía dưới

#### 🔧 Floating Toolbar (Thanh công cụ nổi)
| Nút | Chức năng |
|-----|-----------|
| **Copy** | Copy nội dung các video đã chọn (Markdown format) |
| **Chat** | Mở chat AI với context các video đã chọn |
| **X** | Bỏ chọn tất cả |

### Các Hành Động

| Hành động | Cách thực hiện |
|-----------|----------------|
| Lọc theo Category | Click tab danh mục |
| Lọc theo Subcategory | Click chip danh mục con |
| Sắp xếp | Dropdown Sort: Newest/Oldest/Views/Likes |
| Xem chi tiết | Click vào video (ngoài vùng checkbox) |
| Chọn video | Click checkbox góc trên trái |
| Copy nội dung | Chọn video → Click "Copy" |
| Chat AI | Chọn video → Click "Chat" |

---

## 4. Trang Video Detail (Chi Tiết Video)

### 📍 Truy cập: `/video/{video_id}`

### Mô tả
Trang chi tiết hiển thị đầy đủ thông tin video và kết quả phân tích AI.

### Thành Phần Giao Diện

#### 🔹 Cột Trái: Media Preview
- **Video thường**: Video player với controls
- **Slideshow**: Carousel ảnh với nút Previous/Next
  - Audio player cho nhạc nền
- **Hashtags**: Danh sách hashtag của video

#### 🔹 Cột Phải: Thông Tin Chi Tiết

**📌 Tiêu đề & Author**
- Title lớn
- Avatar, @nickname, nút Follow
- Ngày đăng, lượt xem

**📊 Stats**
- ❤️ Likes | 💬 Comments | ↗️ Shares | 🔖 Saves

**⚙️ Actions Card**
- URL TikTok gốc + nút Copy
- Nút **Delete Video** (cần xác nhận)

**🧠 Knowledge Card** (Thẻ tri thức AI)
- **Summary**: Tóm tắt nội dung
- **Điểm chính**: Các key takeaways
- **Các bước thực hiện**: Action items (nếu có)
- **Entities**: Nguyên liệu, sản phẩm, công cụ, địa điểm
- **Tags**: Các tag liên quan

**📝 Transcript**
- Phần có thể mở rộng (click để xem)
- Hiển thị toàn bộ nội dung audio đã được chuyển thành text

### Các Hành Động Knowledge Card

| Nút | Chức năng |
|-----|-----------|
| **Copy** | Dropdown copy: JSON / Markdown / Plain Text |
| **Chat** | Mở floating chat với context video này |
| **⟳ Re-analyze** | Yêu cầu AI phân tích lại |
| **Export** | Tải xuống file Markdown |

### 🗨️ Floating Chat Window
- Chat trực tiếp với AI về nội dung video
- Input ở dưới, messages ở trên
- Nút đóng góc phải

---

## 5. Trang Search (Tìm Kiếm AI)

### 📍 Truy cập: `/search`

### Mô tả
Tìm kiếm thông minh bằng ngôn ngữ tự nhiên, AI sẽ phân tích và trả lời.

### Thành Phần Giao Diện

#### 🔹 Search Header
- Tiêu đề "AI-Powered Search"
- Ô input lớn cho câu hỏi
- Nút Search

#### 🔹 Kết Quả Tìm Kiếm

**AI Answer Box** (khi có kết quả)
- Icon robot AI
- Câu trả lời tổng hợp từ AI

**Related Videos Grid**
- Danh sách video liên quan
- Mỗi card hiển thị:
  - Thumbnail
  - **Score**: Độ phù hợp (%)
  - Title
  - Trích đoạn transcript
  - Category

#### 🔹 Empty State (khi chưa tìm)
Gợi ý các câu hỏi mẫu:
- "Cách làm bánh"
- "Review điện thoại"
- "Video ẩm thực"

### Cách Sử Dụng

1. **Nhập câu hỏi bằng tiếng Việt tự nhiên**
   - Ví dụ: "Cách nấu phở ngon"
   - Ví dụ: "Video nào có địa điểm du lịch?"

2. **Xem AI Answer**
   - AI tổng hợp câu trả lời từ nội dung các video

3. **Duyệt Related Videos**
   - Click vào video card để xem chi tiết
   - Score % cho biết độ liên quan

---

## 6. Tính Năng Chung

### 🎨 Giao Diện
- **Dark Theme**: Nền tối (#0f172a), chữ sáng
- **Glassmorphism**: Hiệu ứng kính mờ
- **Responsive**: Tương thích nhiều kích thước màn hình
- **Smooth Animations**: Hover effects, transitions

### ⌨️ Phím Tắt & Thao Tác

| Phím/Thao tác | Chức năng |
|---------------|-----------|
| `ESC` | Đóng modal đang mở |
| Click ngoài modal | Đóng modal |
| `Enter` trong ô search | Thực hiện tìm kiếm |

### 📝 Các Loại Video Hỗ Trợ

| Loại | Biểu tượng | Mô tả |
|------|------------|-------|
| Video | ▶️ | Video TikTok thông thường |
| Slideshow | 📷 | Ảnh carousel với nhạc nền |

### 🔔 Thông Báo
- **Toast notifications**: Góc dưới phải (copy thành công, v.v.)
- **Alert confirmations**: Cho các hành động quan trọng (delete, reset)

### ⚠️ Lưu Ý Quan Trọng

> **Reset Database**: Hành động này XÓA TOÀN BỘ dữ liệu và KHÔNG THỂ hoàn tác!
> Cần xác nhận 2 lần trước khi thực hiện.

> **Import Video**: Quá trình có thể mất 30-60 giây tùy độ dài video do cần:
> 1. Tải video từ TikTok
> 2. Chuyển audio thành text (transcript)
> 3. AI phân tích nội dung
> 4. Lưu vào database

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra URL TikTok có hợp lệ không
2. Đảm bảo kết nối internet ổn định
3. Thử refresh trang (F5)

---

*© 2026 TikVault Inc. - Version 1.0*
