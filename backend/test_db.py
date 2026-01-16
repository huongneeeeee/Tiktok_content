"""
Test MongoDB Database Connection
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Database, get_video_document_template

async def test_database():
    print("=" * 50)
    print("🧪 Testing MongoDB Connection")
    print("=" * 50)
    
    try:
        # Connect
        db = await Database.connect()
        print(f"✅ Connected to database")
        
        # Get collection
        videos = db["videos"]
        
        # Create test document
        doc = get_video_document_template()
        doc["video_id"] = "test_db_connection"
        doc["title"] = "Test Video - Database Check"
        doc["status"] = "test"
        
        # Test Insert
        result = await videos.insert_one(doc)
        print(f"✅ Insert OK: {result.inserted_id}")
        
        # Test Find
        found = await videos.find_one({"video_id": "test_db_connection"})
        print(f"✅ Find OK: {found is not None}")
        
        # Test Update
        update_result = await videos.update_one(
            {"video_id": "test_db_connection"},
            {"$set": {"title": "Updated Title"}}
        )
        print(f"✅ Update OK: {update_result.modified_count}")
        
        # Test Indexes
        indexes = await videos.index_information()
        print(f"✅ Indexes: {list(indexes.keys())}")
        
        # Cleanup
        await videos.delete_one({"video_id": "test_db_connection"})
        print(f"✅ Delete OK")
        
        # Disconnect
        await Database.disconnect()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_database())
    sys.exit(0 if result else 1)
