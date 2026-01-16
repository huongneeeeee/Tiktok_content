
import os
from dotenv import load_dotenv

print(f"CWD: {os.getcwd()}")
env_path = os.path.abspath(".env")
print(f"Looking for .env at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    print("--- File Content Preview (First 50 chars) ---")
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(repr(content[:50]))
    except Exception as e:
        print(f"Error reading file: {e}")
    print("---------------------------------------------")

load_dotenv(env_path)
api_key = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY present: {bool(api_key)}")
if api_key:
    print(f"GEMINI_API_KEY length: {len(api_key)}")
    print(f"First 4 chars: {api_key[:4]}")
    print(f"Last 4 chars: {api_key[-4:]}")
else:
    # Check if GOOGLE_API_KEY exists as fallback
    google_key = os.getenv("GOOGLE_API_KEY")
    print(f"GOOGLE_API_KEY present: {bool(google_key)}")
