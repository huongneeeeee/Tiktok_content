import os
import mimetypes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Phạm vi quyền truy cập (Giữ nguyên)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- BIẾN TOÀN CỤC ĐỂ CACHE KẾT NỐI ---
_cached_service = None

def get_drive_service():
    """
    Kết nối Google Drive với cơ chế Caching.
    Chỉ xác thực 1 lần duy nhất trong suốt vòng đời ứng dụng.
    """
    global _cached_service
    
    # Nếu đã có kết nối rồi thì dùng lại ngay, không load lại token
    if _cached_service:
        return _cached_service

    creds = None
    # 1. Load Token cũ
    if os.path.exists('secrets/token.json'):
        try:
            creds = Credentials.from_authorized_user_file('secrets/token.json', SCOPES)
        except Exception:
            print("⚠️ Token lỗi, sẽ tạo mới...")
            creds = None
    
    # 2. Nếu không có hoặc hết hạn thì refresh/login mới
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Nếu refresh lỗi (do hết hạn hẳn) thì buộc login lại
                creds = None
        
        if not creds:
            if not os.path.exists('secrets/credentials.json'):
                print("❌ LỖI: Thiếu file credentials.json")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file('secrets/credentials.json', SCOPES)
            # Run local server để login trên trình duyệt
            creds = flow.run_local_server(port=0)
            
        # Lưu token mới
        with open('secrets/token.json', 'w') as token:
            token.write(creds.to_json())

    # 3. Build service và Cache lại vào biến toàn cục
    try:
        service = build('drive', 'v3', credentials=creds)
        _cached_service = service
        print("✅ Đã kết nối Google Drive API")
        return service
    except Exception as e:
        print(f"❌ Lỗi build service: {e}")
        return None

def upload_to_gdrive(file_path, folder_id):
    """
    Upload file lên Drive với tính năng tự động nhận diện loại file.
    """
    if not os.path.exists(file_path):
        print(f"❌ File không tồn tại: {file_path}")
        return None

    try:
        service = get_drive_service()
        if not service: return None

        file_name = os.path.basename(file_path)
        
        # --- TỰ ĐỘNG NHẬN DIỆN MIME TYPE ---
        # Giúp Drive phân biệt đâu là Video, đâu là JSON, đâu là Nhạc
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream' # Mặc định nếu không nhận ra
            
        print(f"☁️ Đang upload: {file_name} ({mime_type})...")
        
        file_metadata = {
            'name': file_name, 
            'parents': [folder_id]
        }
        
        # resumable=True giúp upload file lớn ổn định hơn
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        link = file.get('webViewLink')
        print(f"   ✅ Upload xong! Link: {link}")
        return link
        
    except Exception as e:
        print(f"   ❌ Lỗi Upload Drive: {e}")
        # Nếu lỗi connection, reset cache để lần sau thử kết nối lại
        global _cached_service
        _cached_service = None
        return None