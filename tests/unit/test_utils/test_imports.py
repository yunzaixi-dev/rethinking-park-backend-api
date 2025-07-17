#!/usr/bin/env python3

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    try:
        # Test basic imports
        import numpy as np

        print(f"✅ NumPy {np.__version__} imported successfully")

        from PIL import Image

        print(f"✅ Pillow imported successfully")

        # Test Google Cloud Vision
        from google.cloud import vision

        print("✅ Google Cloud Vision imported successfully")

        # Test existing services
        from services.vision_service import vision_service

        print(f"✅ Vision Service imported, enabled: {vision_service.is_enabled()}")

        # Test new enhanced services
        from services.enhanced_vision_service import enhanced_vision_service

        print(
            f"✅ Enhanced Vision Service imported, enabled: {enhanced_vision_service.is_enabled()}"
        )

        from services.image_annotation_service import image_annotation_service

        print("✅ Image Annotation Service imported successfully")

        print("\n🎉 All imports successful! Infrastructure setup complete.")
        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_imports()
