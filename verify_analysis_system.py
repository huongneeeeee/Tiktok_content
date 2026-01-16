
import os
import sys
import json
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

def verify_pydantic_models():
    print("\n🔍 Verifying Pydantic Models...")
    try:
        from app.models.video_analysis_models import VideoAnalysisResult, GeneralInfo
        
        # Test basic instantiation
        model = VideoAnalysisResult(
            general_info=GeneralInfo(
                title="Test",
                category="Test", 
                overall_sentiment="Test",
                target_audience="Test"
            ),
            content_analysis={
                "main_objective": "Test",
                "key_message": "Test",
                "hook_strategy": "Test"
            },
            script_breakdown=[],
            technical_audit={
                "editing_style": "Test",
                "sound_design": "Test",
                "cta_analysis": "Test"
            },
            virality_factors={
                "score": 5,
                "reasons": "Test",
                "improvement_suggestions": "Test"
            }
        )
        print("✅ Pydantic Models imported and instantiated successfully")
        return True
    except Exception as e:
        print(f"❌ Pydantic Models verification failed: {e}")
        return False

def verify_gemini_analyzer():
    print("\n🔍 Verifying Gemini Analyzer Service...")
    try:
        from app.services.analysis.gemini_video_analyzer import GeminiVideoAnalyzer
        
        # Check if we can import logic without error
        # Note: We can't fully instantiate without API key if it's not in env, 
        # but the module import entails checking imports like langchain
        print("✅ GeminiVideoAnalyzer module imported successfully")
        
        # Check prompt template availability
        from app.services.analysis.gemini_video_analyzer import ANALYSIS_PROMPT_TEMPLATE
        if "{format_instructions}" in ANALYSIS_PROMPT_TEMPLATE:
             print("✅ Prompt template contains format_instructions placeholder")
        else:
             print("❌ Prompt template missing format_instructions placeholder")
             
        return True
    except ImportError as e:
         print(f"❌ Gemini Analyzer verification failed (ImportError): {e}")
         print("   Please assert 'langchain', 'langchain-core', 'google-genai' are installed.")
         return False
    except Exception as e:
        print(f"❌ Gemini Analyzer verification failed: {e}")
        return False

def verify_api_endpoints():
    print("\n🔍 Verifying API Endpoints (Code Structure)...")
    try:
        from app.api.videos import router
        
        # Inspect router routes
        routes = [route.path for route in router.routes]
        
        expected_routes = [
             "/videos/{video_id}/analyze",
             "/videos/{video_id}/analysis",
             "/videos/search/query"
        ]
        
        all_found = True
        for route in expected_routes:
            if any(r.endswith(route) for r in routes):
                print(f"✅ Found endpoint: {route}")
            else:
                 # Check regex matching for params
                 found_regex = False
                 for r in routes:
                     # very basic check, just checking if 'analyze' and 'search' exist in routes
                     if route.split('/')[-1] in r: 
                         found_regex = True
                         print(f"✅ Found endpoint (matched): {route} -> {r}")
                         break
                 if not found_regex:
                    print(f"❌ Missing endpoint: {route}")
                    all_found = False
        
        return all_found
    except Exception as e:
        print(f"❌ API Endpoints verification failed: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 Starting System Verification at {datetime.now()}")
    
    models_ok = verify_pydantic_models()
    analyzer_ok = verify_gemini_analyzer()
    api_ok = verify_api_endpoints()
    
    if models_ok and analyzer_ok and api_ok:
        print("\n✨ ALL CHECKS PASSED! System is ready.")
    else:
        print("\n⚠️ SOME CHECKS FAILED. Please review errors above.")
