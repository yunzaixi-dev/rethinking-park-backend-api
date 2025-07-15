#!/usr/bin/env python3
"""
Test script to verify Task 3 implementation:
- ImageAnnotationService for rendering
- Simple object extraction functionality  
- Label-based analysis capabilities
"""

import sys
import os
import asyncio
from PIL import Image
import io
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.image_annotation_service import image_annotation_service
from services.image_processing_service import image_processing_service
from services.label_analysis_service import label_analysis_service
from models.image import (
    EnhancedDetectionResult, 
    FaceDetectionResult, 
    BoundingBox, 
    Point, 
    ImageSize
)

def create_test_image() -> bytes:
    """Create a simple test image"""
    # Create a 400x300 test image with colored regions
    img = Image.new('RGB', (400, 300), color='lightblue')  # Sky background
    
    # Add some colored regions to simulate objects
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    
    # Green rectangle (vegetation)
    draw.rectangle([50, 200, 150, 280], fill='green')
    
    # Brown rectangle (terrain)
    draw.rectangle([200, 220, 350, 290], fill='brown')
    
    # Blue rectangle (water)
    draw.rectangle([100, 100, 200, 150], fill='blue')
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

def create_test_detection_results():
    """Create test detection results"""
    objects = [
        EnhancedDetectionResult(
            object_id="test_obj_1",
            class_name="Tree",
            confidence=0.85,
            bounding_box=BoundingBox(x=0.125, y=0.667, width=0.25, height=0.267),  # Green rectangle
            center_point=Point(x=0.25, y=0.8),
            area_percentage=6.67
        ),
        EnhancedDetectionResult(
            object_id="test_obj_2", 
            class_name="Ground",
            confidence=0.75,
            bounding_box=BoundingBox(x=0.5, y=0.733, width=0.375, height=0.233),  # Brown rectangle
            center_point=Point(x=0.6875, y=0.85),
            area_percentage=8.75
        )
    ]
    
    faces = [
        FaceDetectionResult(
            face_id="test_face_1",
            bounding_box=BoundingBox(x=0.3, y=0.2, width=0.1, height=0.15),
            center_point=Point(x=0.35, y=0.275),
            confidence=0.9,
            anonymized=True
        )
    ]
    
    return objects, faces

def create_test_labels():
    """Create test Google Vision labels"""
    return [
        {"name": "Tree", "confidence": 0.85, "topicality": 0.9},
        {"name": "Grass", "confidence": 0.78, "topicality": 0.8},
        {"name": "Sky", "confidence": 0.92, "topicality": 0.95},
        {"name": "Water", "confidence": 0.65, "topicality": 0.7},
        {"name": "Ground", "confidence": 0.75, "topicality": 0.8},
        {"name": "Nature", "confidence": 0.88, "topicality": 0.9},
        {"name": "Plant", "confidence": 0.72, "topicality": 0.75}
    ]

def test_image_annotation_service():
    """Test ImageAnnotationService functionality"""
    print("Testing ImageAnnotationService...")
    
    try:
        # Create test data
        image_content = create_test_image()
        objects, faces = create_test_detection_results()
        labels = create_test_labels()
        
        # Test complete annotation rendering
        print("  - Testing complete annotation rendering...")
        annotated_image = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=objects,
            faces=faces,
            labels=labels,
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=True
        )
        
        assert len(annotated_image) > len(image_content), "Annotated image should be larger"
        print("    ✓ Complete annotation rendering works")
        
        # Test bounding boxes only
        print("  - Testing bounding boxes only...")
        boxes_only = image_annotation_service.render_bounding_boxes_only(
            image_content=image_content,
            objects=objects
        )
        assert len(boxes_only) > 0, "Bounding boxes rendering failed"
        print("    ✓ Bounding boxes only rendering works")
        
        # Test face markers only
        print("  - Testing face markers only...")
        faces_only = image_annotation_service.render_face_markers_only(
            image_content=image_content,
            faces=faces
        )
        assert len(faces_only) > 0, "Face markers rendering failed"
        print("    ✓ Face markers only rendering works")
        
        # Test annotation statistics
        print("  - Testing annotation statistics...")
        stats = image_annotation_service.get_annotation_statistics(objects, faces)
        assert stats["total_objects"] == 2, f"Expected 2 objects, got {stats['total_objects']}"
        assert stats["total_faces"] == 1, f"Expected 1 face, got {stats['total_faces']}"
        print("    ✓ Annotation statistics work")
        
        # Test validation
        print("  - Testing annotation validation...")
        validation = image_annotation_service.validate_annotation_request(
            image_content=image_content,
            objects=objects,
            faces=faces
        )
        assert validation["valid"] == True, "Validation should pass for valid data"
        print("    ✓ Annotation validation works")
        
        print("✓ ImageAnnotationService tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ ImageAnnotationService test failed: {e}")
        return False

def test_image_processing_service():
    """Test ImageProcessingService functionality"""
    print("Testing ImageProcessingService...")
    
    try:
        # Create test data
        image_content = create_test_image()
        objects, _ = create_test_detection_results()
        
        # Test bounding box extraction
        print("  - Testing bounding box extraction...")
        extraction_result = image_processing_service.extract_by_bounding_box(
            image_content=image_content,
            bounding_box=objects[0].bounding_box,
            padding=10,
            output_format="PNG"
        )
        
        assert len(extraction_result.extracted_image_bytes) > 0, "Extraction failed"
        assert extraction_result.extraction_id is not None, "Extraction ID missing"
        print("    ✓ Bounding box extraction works")
        
        # Test batch extraction
        print("  - Testing batch extraction...")
        batch_results = image_processing_service.batch_extract_objects(
            image_content=image_content,
            objects=objects,
            padding=5,
            output_format="PNG"
        )
        
        assert len(batch_results) == 2, f"Expected 2 extractions, got {len(batch_results)}"
        print("    ✓ Batch extraction works")
        
        # Test custom region extraction
        print("  - Testing custom region extraction...")
        custom_result = image_processing_service.extract_with_custom_region(
            image_content=image_content,
            x=0.25, y=0.33, width=0.5, height=0.34,
            padding=0,
            output_format="PNG"
        )
        
        assert len(custom_result.extracted_image_bytes) > 0, "Custom extraction failed"
        print("    ✓ Custom region extraction works")
        
        # Test extraction statistics
        print("  - Testing extraction statistics...")
        stats = image_processing_service.get_extraction_statistics(
            original_size=ImageSize(width=400, height=300),
            extracted_size=extraction_result.extracted_size,
            bounding_box=objects[0].bounding_box
        )
        
        assert "area_ratio" in stats, "Statistics missing area_ratio"
        assert stats["area_ratio"] > 0, "Area ratio should be positive"
        print("    ✓ Extraction statistics work")
        
        # Test validation
        print("  - Testing extraction validation...")
        validation = image_processing_service.validate_extraction_request(
            image_content=image_content,
            bounding_box=objects[0].bounding_box,
            padding=10
        )
        
        assert validation["valid"] == True, "Validation should pass for valid data"
        print("    ✓ Extraction validation works")
        
        print("✓ ImageProcessingService tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ ImageProcessingService test failed: {e}")
        return False

def test_label_analysis_service():
    """Test LabelAnalysisService functionality"""
    print("Testing LabelAnalysisService...")
    
    try:
        # Create test data
        labels = create_test_labels()
        image_content = create_test_image()
        
        # Test basic label analysis
        print("  - Testing basic label analysis...")
        basic_analysis = label_analysis_service.analyze_by_labels(
            labels=labels,
            analysis_depth="basic",
            include_confidence=True
        )
        
        assert "categorized_elements" in basic_analysis, "Missing categorized_elements"
        assert "coverage_statistics" in basic_analysis, "Missing coverage_statistics"
        assert basic_analysis["analysis_metadata"]["total_labels"] == len(labels)
        print("    ✓ Basic label analysis works")
        
        # Test comprehensive analysis with image
        print("  - Testing comprehensive analysis...")
        comprehensive_analysis = label_analysis_service.analyze_by_labels(
            labels=labels,
            image_content=image_content,
            analysis_depth="comprehensive",
            include_confidence=True
        )
        
        assert "color_analysis" in comprehensive_analysis, "Missing color_analysis"
        assert "natural_element_insights" in comprehensive_analysis, "Missing insights"
        print("    ✓ Comprehensive analysis works")
        
        # Test coverage estimation
        print("  - Testing coverage estimation...")
        coverage_stats = comprehensive_analysis["coverage_statistics"]
        
        # Should have some vegetation coverage due to "Tree", "Grass", "Plant" labels
        assert coverage_stats["vegetation_coverage"] > 0, "Should detect vegetation"
        
        # Should have sky coverage due to "Sky" label
        assert coverage_stats["sky_coverage"] > 0, "Should detect sky"
        
        print("    ✓ Coverage estimation works")
        
        # Test natural elements result creation
        print("  - Testing natural elements result creation...")
        natural_result = label_analysis_service.create_natural_elements_result(
            coverage_stats=coverage_stats,
            color_analysis=comprehensive_analysis.get("color_analysis"),
            insights=comprehensive_analysis.get("natural_element_insights")
        )
        
        assert natural_result.vegetation_coverage >= 0, "Vegetation coverage should be non-negative"
        assert natural_result.sky_coverage >= 0, "Sky coverage should be non-negative"
        print("    ✓ Natural elements result creation works")
        
        # Test confidence analysis
        print("  - Testing confidence analysis...")
        confidence_analysis = comprehensive_analysis.get("confidence_analysis", {})
        
        assert "confidence_distribution" in confidence_analysis, "Missing confidence distribution"
        assert "reliability_score" in confidence_analysis, "Missing reliability score"
        print("    ✓ Confidence analysis works")
        
        print("✓ LabelAnalysisService tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ LabelAnalysisService test failed: {e}")
        return False

def test_integration():
    """Test integration between all three services"""
    print("Testing service integration...")
    
    try:
        # Create test data
        image_content = create_test_image()
        objects, faces = create_test_detection_results()
        labels = create_test_labels()
        
        # Step 1: Analyze labels
        print("  - Step 1: Analyzing labels...")
        label_analysis = label_analysis_service.analyze_by_labels(
            labels=labels,
            image_content=image_content,
            analysis_depth="comprehensive"
        )
        
        # Step 2: Extract objects
        print("  - Step 2: Extracting objects...")
        extractions = image_processing_service.batch_extract_objects(
            image_content=image_content,
            objects=objects,
            padding=10
        )
        
        # Step 3: Create annotated image
        print("  - Step 3: Creating annotated image...")
        annotated_image = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=objects,
            faces=faces,
            labels=labels
        )
        
        # Verify integration results
        assert len(extractions) == len(objects), "Extraction count mismatch"
        assert len(annotated_image) > len(image_content), "Annotation failed"
        # Check if analysis was successful (no error field means success)
        assert "error" not in label_analysis, "Label analysis failed"
        
        print("    ✓ All services integrate successfully")
        
        # Create summary report
        summary = {
            "label_analysis_summary": {
                "total_labels": label_analysis["analysis_metadata"]["total_labels"],
                "vegetation_coverage": label_analysis["coverage_statistics"]["vegetation_coverage"],
                "sky_coverage": label_analysis["coverage_statistics"]["sky_coverage"]
            },
            "extraction_summary": {
                "total_extractions": len(extractions),
                "extraction_ids": [r.extraction_id for r in extractions]
            },
            "annotation_summary": {
                "annotated_image_size": len(annotated_image),
                "objects_annotated": len(objects),
                "faces_annotated": len(faces)
            }
        }
        
        print("  - Integration Summary:")
        print(f"    • Labels analyzed: {summary['label_analysis_summary']['total_labels']}")
        print(f"    • Vegetation coverage: {summary['label_analysis_summary']['vegetation_coverage']:.1f}%")
        print(f"    • Objects extracted: {summary['extraction_summary']['total_extractions']}")
        print(f"    • Annotated image size: {summary['annotation_summary']['annotated_image_size']} bytes")
        
        print("✓ Service integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Service integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("TESTING TASK 3 IMPLEMENTATION")
    print("Build image annotation and simple extraction system")
    print("=" * 60)
    
    test_results = []
    
    # Test individual services
    test_results.append(test_image_annotation_service())
    print()
    
    test_results.append(test_image_processing_service())
    print()
    
    test_results.append(test_label_analysis_service())
    print()
    
    # Test integration
    test_results.append(test_integration())
    print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Task 3 implementation is working correctly.")
        print("\nImplemented components:")
        print("✓ ImageAnnotationService - Renders bounding boxes, face markers, and labels")
        print("✓ ImageProcessingService - Extracts objects using bounding boxes")
        print("✓ LabelAnalysisService - Analyzes natural elements from Google Vision labels")
        print("✓ Service Integration - All services work together seamlessly")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())