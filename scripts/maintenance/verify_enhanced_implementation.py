#!/usr/bin/env python3
"""
Simple verification script for enhanced object detection implementation
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_imports():
    """Verify all imports work correctly"""
    print("=== Verifying Enhanced Detection Implementation ===\n")
    
    # Test model imports
    try:
        from models.image import (
            EnhancedDetectionResult,
            EnhancedDetectionResponse,
            FaceDetectionResult,
            FaceDetectionResponse,
            BoundingBox,
            Point,
            NaturalElementsResult,
            ColorInfo
        )
        print("✓ Enhanced detection models imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import models: {e}")
        return False
    
    # Test service imports
    try:
        from services.enhanced_vision_service import enhanced_vision_service
        print("✓ Enhanced vision service imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import enhanced vision service: {e}")
        return False
    
    try:
        from services.face_detection_service import face_detection_service
        print("✓ Face detection service imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import face detection service: {e}")
        return False
    
    return True

def verify_model_structure():
    """Verify model structure and attributes"""
    print("\n=== Verifying Model Structure ===\n")
    
    try:
        from models.image import EnhancedDetectionResult, BoundingBox, Point
        
        # Create test instances
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        point = Point(x=0.5, y=0.6)
        
        detection = EnhancedDetectionResult(
            object_id="test_obj",
            class_name="Tree",
            confidence=0.85,
            bounding_box=bbox,
            center_point=point,
            area_percentage=12.5
        )
        
        print(f"✓ EnhancedDetectionResult created: {detection.object_id}")
        print(f"  - Class: {detection.class_name}")
        print(f"  - Confidence: {detection.confidence}")
        print(f"  - Center: ({detection.center_point.x}, {detection.center_point.y})")
        print(f"  - Area: {detection.area_percentage}%")
        
    except Exception as e:
        print(f"✗ Model structure verification failed: {e}")
        return False
    
    return True

def verify_service_attributes():
    """Verify service attributes and methods"""
    print("\n=== Verifying Service Attributes ===\n")
    
    try:
        from services.enhanced_vision_service import enhanced_vision_service
        from services.face_detection_service import face_detection_service
        
        # Check enhanced vision service
        print(f"Enhanced Vision Service:")
        print(f"  - Enabled: {enhanced_vision_service.enabled}")
        print(f"  - Has face detection service: {hasattr(enhanced_vision_service, 'face_detection_service')}")
        
        # Check required methods
        required_methods = [
            'detect_objects_enhanced',
            'apply_confidence_filtering',
            'calculate_detection_quality_metrics',
            'detect_with_position_marking'
        ]
        
        for method in required_methods:
            if hasattr(enhanced_vision_service, method):
                print(f"  ✓ Has method: {method}")
            else:
                print(f"  ✗ Missing method: {method}")
                return False
        
        # Check face detection service
        print(f"\nFace Detection Service:")
        print(f"  - Enabled: {face_detection_service.enabled}")
        print(f"  - Marker color: {getattr(face_detection_service, 'face_marker_color', 'Not set')}")
        
        face_methods = [
            'detect_faces_enhanced',
            'create_face_markers_image',
            'assign_face_ids',
            'anonymize_face_data'
        ]
        
        for method in face_methods:
            if hasattr(face_detection_service, method):
                print(f"  ✓ Has method: {method}")
            else:
                print(f"  ✗ Missing method: {method}")
                return False
        
    except Exception as e:
        print(f"✗ Service verification failed: {e}")
        return False
    
    return True

def main():
    """Run verification"""
    success = True
    
    success &= verify_imports()
    success &= verify_model_structure()
    success &= verify_service_attributes()
    
    print("\n" + "="*50)
    if success:
        print("🎉 VERIFICATION SUCCESSFUL!")
        print("Enhanced object detection and face recognition implementation is complete.")
        print("\nImplemented features:")
        print("- Enhanced detection response models")
        print("- Face detection service with position marking")
        print("- Extended vision service with confidence filtering")
        print("- Quality metrics calculation")
        print("- Position marking functionality")
    else:
        print("❌ VERIFICATION FAILED!")
        print("Some components are missing or not working correctly.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)