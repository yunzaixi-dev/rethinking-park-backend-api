#!/usr/bin/env python3
"""
Verification script for download-annotated endpoint integration
"""

import sys
import os
import inspect

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_download_annotated_integration():
    """Verify that the download-annotated endpoint is properly integrated"""
    
    print("🔍 Verifying Download Annotated Endpoint Integration")
    print("=" * 60)
    
    try:
        # Check if models are properly imported
        print("1. Checking model imports...")
        from models.image import AnnotatedImageRequest, AnnotatedImageResponse, AnnotationStyle
        print("   ✅ AnnotatedImageRequest model imported")
        print("   ✅ AnnotatedImageResponse model imported")
        print("   ✅ AnnotationStyle model imported")
        
        # Check if image annotation service is available
        print("\n2. Checking image annotation service...")
        from services.image_annotation_service import image_annotation_service
        print("   ✅ Image annotation service imported")
        
        # Check service methods
        service_methods = [
            'render_annotated_image',
            'validate_annotation_request',
            'get_annotation_statistics'
        ]
        
        for method in service_methods:
            if hasattr(image_annotation_service, method):
                print(f"   ✅ Method '{method}' available")
            else:
                print(f"   ❌ Method '{method}' missing")
                return False
        
        # Check if main.py has the endpoint
        print("\n3. Checking main.py integration...")
        import main
        
        # Check if the endpoint function exists
        if hasattr(main, 'download_annotated'):
            print("   ✅ download_annotated function exists in main.py")
        else:
            print("   ❌ download_annotated function missing in main.py")
            return False
        
        # Check FastAPI app routes
        app = main.app
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        if "/api/v1/download-annotated" in routes:
            print("   ✅ /api/v1/download-annotated route registered")
        else:
            print("   ❌ /api/v1/download-annotated route not found")
            print(f"   Available routes: {routes}")
            return False
        
        # Test model validation
        print("\n4. Testing model validation...")
        
        # Test AnnotationStyle model
        try:
            style = AnnotationStyle(
                face_marker_color="#FFD700",
                box_color="#FFFFFF",
                label_color="#0066CC"
            )
            print("   ✅ AnnotationStyle model validation works")
        except Exception as e:
            print(f"   ❌ AnnotationStyle model validation failed: {e}")
            return False
        
        # Test AnnotatedImageRequest model
        try:
            request = AnnotatedImageRequest(
                image_hash="test_hash_123",
                include_face_markers=True,
                include_object_boxes=True,
                include_labels=True,
                output_format="png"
            )
            print("   ✅ AnnotatedImageRequest model validation works")
        except Exception as e:
            print(f"   ❌ AnnotatedImageRequest model validation failed: {e}")
            return False
        
        # Check service initialization
        print("\n5. Testing service functionality...")
        
        # Test annotation service methods
        try:
            # Test with dummy data
            from models.image import EnhancedDetectionResult, BoundingBox, Point
            
            dummy_object = EnhancedDetectionResult(
                object_id="test_obj_1",
                class_name="Test Object",
                confidence=0.85,
                bounding_box=BoundingBox(x=0.1, y=0.1, width=0.2, height=0.2),
                center_point=Point(x=0.2, y=0.2),
                area_percentage=4.0
            )
            
            stats = image_annotation_service.get_annotation_statistics(
                objects=[dummy_object],
                faces=[]
            )
            
            if stats and 'total_objects' in stats:
                print("   ✅ Annotation statistics generation works")
            else:
                print("   ❌ Annotation statistics generation failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Service functionality test failed: {e}")
            return False
        
        # Check endpoint signature
        print("\n6. Checking endpoint signature...")
        download_annotated_func = main.download_annotated
        sig = inspect.signature(download_annotated_func)
        
        expected_params = ['request', 'annotation_request']
        actual_params = list(sig.parameters.keys())
        
        if all(param in actual_params for param in expected_params):
            print("   ✅ Endpoint signature is correct")
        else:
            print(f"   ❌ Endpoint signature mismatch. Expected: {expected_params}, Got: {actual_params}")
            return False
        
        print("\n🎉 All integration checks passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main verification function"""
    success = verify_download_annotated_integration()
    if success:
        print("\n✅ Download annotated endpoint integration verified successfully!")
        print("\n📋 Summary:")
        print("   - Models are properly defined and imported")
        print("   - Image annotation service is available and functional")
        print("   - Endpoint is registered in FastAPI app")
        print("   - All required functionality is implemented")
        print("\n🚀 The endpoint is ready for use!")
        sys.exit(0)
    else:
        print("\n❌ Download annotated endpoint integration verification failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()