#!/usr/bin/env python3
"""
Test script for enhanced object detection and face recognition functionality
"""

import sys
import os
import asyncio
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from models.image import (
        EnhancedDetectionRequest,
        EnhancedDetectionResponse,
        FaceDetectionRequest,
        FaceDetectionResponse,
        EnhancedDetectionResult,
        FaceDetectionResult,
        BoundingBox,
        Point
    )
    print("✓ Successfully imported enhanced detection models")
except ImportError as e:
    print(f"✗ Failed to import models: {e}")
    sys.exit(1)

try:
    from services.enhanced_vision_service import enhanced_vision_service
    from services.face_detection_service import face_detection_service
    print("✓ Successfully imported enhanced services")
except ImportError as e:
    print(f"✗ Failed to import services: {e}")
    sys.exit(1)

def test_model_creation():
    """Test creating model instances"""
    print("\n=== Testing Model Creation ===")
    
    try:
        # Test BoundingBox creation
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        print(f"✓ BoundingBox created: {bbox.x}, {bbox.y}, {bbox.width}, {bbox.height}")
        
        # Test Point creation
        point = Point(x=0.5, y=0.6)
        print(f"✓ Point created: {point.x}, {point.y}")
        
        # Test EnhancedDetectionResult creation
        detection = EnhancedDetectionResult(
            object_id="test_obj_1",
            class_name="Tree",
            confidence=0.85,
            bounding_box=bbox,
            center_point=point,
            area_percentage=12.5
        )
        print(f"✓ EnhancedDetectionResult created: {detection.object_id}, {detection.class_name}")
        
        # Test FaceDetectionResult creation
        face = FaceDetectionResult(
            face_id="test_face_1",
            bounding_box=bbox,
            center_point=point,
            confidence=0.92,
            anonymized=True
        )
        print(f"✓ FaceDetectionResult created: {face.face_id}, confidence: {face.confidence}")
        
        # Test Request models
        request = EnhancedDetectionRequest(
            image_hash="test_hash_123",
            include_faces=True,
            include_labels=True,
            confidence_threshold=0.5,
            max_results=50
        )
        print(f"✓ EnhancedDetectionRequest created: {request.image_hash}")
        
        # Test Response models
        response = EnhancedDetectionResponse(
            image_hash="test_hash_123",
            objects=[detection],
            faces=[face],
            labels=[],
            detection_time=datetime.now(),
            success=True,
            enabled=True
        )
        print(f"✓ EnhancedDetectionResponse created with {len(response.objects)} objects and {len(response.faces)} faces")
        
    except Exception as e:
        print(f"✗ Model creation failed: {e}")
        return False
    
    return True

def test_service_initialization():
    """Test service initialization"""
    print("\n=== Testing Service Initialization ===")
    
    try:
        print(f"Enhanced Vision Service enabled: {enhanced_vision_service.enabled}")
        print(f"Face Detection Service enabled: {face_detection_service.enabled}")
        
        # Test service attributes
        if hasattr(enhanced_vision_service, 'face_detection_service'):
            print("✓ Enhanced Vision Service has face detection service integration")
        else:
            print("✗ Enhanced Vision Service missing face detection service integration")
            
        if hasattr(face_detection_service, 'face_marker_color'):
            print(f"✓ Face Detection Service marker color: {face_detection_service.face_marker_color}")
        else:
            print("✗ Face Detection Service missing marker color configuration")
            
    except Exception as e:
        print(f"✗ Service initialization test failed: {e}")
        return False
    
    return True

async def test_confidence_filtering():
    """Test confidence filtering functionality"""
    print("\n=== Testing Confidence Filtering ===")
    
    try:
        # Create test objects with different confidence levels
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        point = Point(x=0.5, y=0.6)
        
        objects = [
            EnhancedDetectionResult(
                object_id="obj_1", class_name="Tree", confidence=0.9,
                bounding_box=bbox, center_point=point, area_percentage=10.0
            ),
            EnhancedDetectionResult(
                object_id="obj_2", class_name="Bench", confidence=0.3,
                bounding_box=bbox, center_point=point, area_percentage=5.0
            ),
            EnhancedDetectionResult(
                object_id="obj_3", class_name="Person", confidence=0.7,
                bounding_box=bbox, center_point=point, area_percentage=8.0
            )
        ]
        
        faces = [
            FaceDetectionResult(
                face_id="face_1", bounding_box=bbox, center_point=point,
                confidence=0.95, anonymized=True
            ),
            FaceDetectionResult(
                face_id="face_2", bounding_box=bbox, center_point=point,
                confidence=0.4, anonymized=True
            )
        ]
        
        labels = [
            {"name": "Nature", "confidence": 0.8},
            {"name": "Outdoor", "confidence": 0.2},
            {"name": "Park", "confidence": 0.6}
        ]
        
        # Test confidence filtering
        filtered_objects, filtered_faces, filtered_labels = enhanced_vision_service.apply_confidence_filtering(
            objects, faces, labels, confidence_threshold=0.5
        )
        
        print(f"✓ Objects filtered: {len(objects)} -> {len(filtered_objects)}")
        print(f"✓ Faces filtered: {len(faces)} -> {len(filtered_faces)}")
        print(f"✓ Labels filtered: {len(labels)} -> {len(filtered_labels)}")
        
        # Verify filtering worked correctly
        assert len(filtered_objects) == 2  # Tree (0.9) and Person (0.7)
        assert len(filtered_faces) == 1   # face_1 (0.95)
        assert len(filtered_labels) == 2  # Nature (0.8) and Park (0.6)
        
        print("✓ Confidence filtering working correctly")
        
    except Exception as e:
        print(f"✗ Confidence filtering test failed: {e}")
        return False
    
    return True

async def test_quality_metrics():
    """Test quality metrics calculation"""
    print("\n=== Testing Quality Metrics ===")
    
    try:
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        point = Point(x=0.5, y=0.6)
        
        objects = [
            EnhancedDetectionResult(
                object_id="obj_1", class_name="Tree", confidence=0.9,
                bounding_box=bbox, center_point=point, area_percentage=10.0
            ),
            EnhancedDetectionResult(
                object_id="obj_2", class_name="Bench", confidence=0.7,
                bounding_box=bbox, center_point=point, area_percentage=5.0
            )
        ]
        
        faces = [
            FaceDetectionResult(
                face_id="face_1", bounding_box=bbox, center_point=point,
                confidence=0.95, anonymized=True
            )
        ]
        
        metrics = enhanced_vision_service.calculate_detection_quality_metrics(objects, faces)
        
        print(f"✓ Quality metrics calculated:")
        print(f"  - Total objects: {metrics['total_objects']}")
        print(f"  - Total faces: {metrics['total_faces']}")
        print(f"  - Detection quality score: {metrics['detection_quality_score']:.2f}")
        
        # Verify metrics
        assert metrics['total_objects'] == 2
        assert metrics['total_faces'] == 1
        assert metrics['detection_quality_score'] > 0
        
        print("✓ Quality metrics calculation working correctly")
        
    except Exception as e:
        print(f"✗ Quality metrics test failed: {e}")
        return False
    
    return True

async def main():
    """Run all tests"""
    print("=== Enhanced Object Detection and Face Recognition Tests ===")
    
    tests = [
        ("Model Creation", test_model_creation),
        ("Service Initialization", test_service_initialization),
        ("Confidence Filtering", test_confidence_filtering),
        ("Quality Metrics", test_quality_metrics)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced detection implementation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)