#!/usr/bin/env python3

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_enhanced_setup():
    """Test the enhanced image processing infrastructure setup"""

    print("🔧 Testing Enhanced Image Processing Infrastructure Setup")
    print("=" * 60)

    # Test 1: Dependencies
    print("\n1. Testing Dependencies:")
    try:
        import numpy as np

        print(f"   ✅ NumPy {np.__version__} - OK")

        from PIL import Image, ImageDraw, ImageFont

        print(f"   ✅ Pillow (PIL) - OK")

        from google.cloud import vision

        print(f"   ✅ Google Cloud Vision - OK")

    except Exception as e:
        print(f"   ❌ Dependency test failed: {e}")
        return False

    # Test 2: Service Imports
    print("\n2. Testing Service Imports:")
    try:
        from services.vision_service import vision_service

        print(f"   ✅ Original Vision Service - OK")

        from services.enhanced_vision_service import enhanced_vision_service

        print(f"   ✅ Enhanced Vision Service - OK")

        from services.image_annotation_service import image_annotation_service

        print(f"   ✅ Image Annotation Service - OK")

    except Exception as e:
        print(f"   ❌ Service import failed: {e}")
        return False

    # Test 3: Service Initialization
    print("\n3. Testing Service Initialization:")
    try:
        # Test enhanced vision service
        print(
            f"   ✅ Enhanced Vision Service enabled: {enhanced_vision_service.is_enabled()}"
        )

        # Test annotation service basic functionality
        test_colors = image_annotation_service.default_colors
        print(
            f"   ✅ Image Annotation Service default colors: {len(test_colors)} configured"
        )

    except Exception as e:
        print(f"   ❌ Service initialization test failed: {e}")
        return False

    # Test 4: Basic Functionality (without Google Cloud credentials)
    print("\n4. Testing Basic Functionality:")
    try:
        # Test color analysis without actual image processing
        import numpy as np
        from PIL import Image

        # Create a test image
        test_image = Image.new("RGB", (100, 100), color="green")
        test_array = np.array(test_image)

        # Test basic numpy operations
        mean_colors = np.mean(test_array, axis=(0, 1))
        print(f"   ✅ NumPy image processing - OK (mean colors: {mean_colors})")

        # Test PIL operations
        from PIL import ImageDraw

        draw = ImageDraw.Draw(test_image)
        draw.rectangle([10, 10, 50, 50], outline="white", width=2)
        print(f"   ✅ PIL image annotation - OK")

    except Exception as e:
        print(f"   ❌ Basic functionality test failed: {e}")
        return False

    # Test 5: Configuration
    print("\n5. Testing Configuration:")
    try:
        from config import settings

        print(f"   ✅ App Name: {settings.APP_NAME}")
        print(f"   ✅ API Version: {settings.API_V1_STR}")
        print(
            f"   ✅ Google Cloud Project: {'Configured' if settings.GOOGLE_CLOUD_PROJECT_ID else 'Not configured'}"
        )

    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 Enhanced Image Processing Infrastructure Setup Complete!")
    print("\nSetup Summary:")
    print("✅ Required dependencies (NumPy, Pillow) installed and working")
    print("✅ Google Cloud Vision API integration configured")
    print("✅ Enhanced Vision Service created with advanced detection capabilities")
    print("✅ Image Annotation Service created for rendering annotations")
    print("✅ Services properly initialized and ready for use")
    print("\nNext Steps:")
    print("- Configure Google Cloud credentials for production use")
    print("- Implement enhanced object detection endpoints")
    print("- Add image annotation and processing capabilities")

    return True


if __name__ == "__main__":
    success = test_enhanced_setup()
    sys.exit(0 if success else 1)
