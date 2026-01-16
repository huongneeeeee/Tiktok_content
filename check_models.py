
import os
import sys

try:
    from google import genai
    from dotenv import load_dotenv
except ImportError:
    print("❌ Missing dependencies. Run: pip install google-genai python-dotenv")
    sys.exit(1)

# Load env
load_dotenv(".env")
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ No API Key found in .env")
    sys.exit(1)

print(f"🔑 Checking models for API Key: {api_key[:5]}...{api_key[-4:]}")

try:
    client = genai.Client(api_key=api_key)
    
    print("\n📋 Available Models:")
    print("-" * 50)
    
    # List models
    models = list(client.models.list())
    
    found_any = False
    for m in models:
        # Filter for Gemini models that support content generation
        if "gemini" in m.name and "generateContent" in m.supported_generation_methods:
            print(f"✅ {m.name}")
            print(f"   Display: {m.display_name}")
            print(f"   Capabilities: {m.supported_generation_methods}")
            print("-" * 50)
            found_any = True
            
    if not found_any:
        print("⚠️ No Gemini generation models found for this key. Key might be invalid or has no access.")
        
except Exception as e:
    print(f"\n❌ Error checking models: {e}")
    if "403" in str(e):
        print("   -> Permission Denied. Check your API Key scopes/billing.")
    if "400" in str(e):
        print("   -> Bad Request. Key format might be wrong.")
    if "429" in str(e):
        print("   -> Quota Exceeded. You're rate limited.")
