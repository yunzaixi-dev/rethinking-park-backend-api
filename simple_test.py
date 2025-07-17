#!/usr/bin/env python3
"""Simple test to verify basic functionality."""

import sys
import traceback

def test_imports():
    """Test basic imports."""
    print("Testing imports...")
    
    try:
        import config
        print("✅ config imported")
    except Exception as e:
        print(f"❌ config import failed: {e}")
        return False
    
    try:
        from models.image import ImageUploadResponse
        print("✅ models.image imported")
    except Exception as e:
        print(f"❌ models.image import failed: {e}")
        return False
    
    try:
        from services.cache_service import cache_service
        print("✅ services.cache_service imported")
    except Exception as e:
        print(f"❌ services.cache_service import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test FastAPI app creation."""
    print("\nTesting FastAPI app creation...")
    
    try:
        from main import app
        print(f"✅ FastAPI app created with {len(app.routes)} routes")
        return True
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🧪 Simple Backend Validation Test")
    print("=" * 40)
    
    results = []
    
    # Test imports
    results.append(test_imports())
    
    # Test app creation
    results.append(test_app_creation())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())