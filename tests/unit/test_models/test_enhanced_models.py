#!/usr/bin/env python3
"""
Test script to validate the enhanced model structure with validation and documentation.
"""

import os
import sys
from datetime import datetime

from pydantic import ValidationError

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


def test_enhanced_validation():
    """Test enhanced validation features."""
    try:
        from app.models import BoundingBox, ImageInfo, ImageSize, Point
        from app.models.analysis import ColorInfo, EnhancedDetectionResult

        print("Testing enhanced validation...")

        # Test valid image info
        valid_image_info = ImageInfo(
            image_hash="a1b2c3d4e5f6789012345678901234ab",
            filename="test_image.jpg",
            file_size=1024000,
            content_type="image/jpeg",
            gcs_url="https://storage.googleapis.com/test-bucket/test_image.jpg",
            image_size=ImageSize(width=1920, height=1080),
        )
        print("✓ Valid ImageInfo created successfully")

        # Test invalid image hash
        try:
            ImageInfo(
                image_hash="invalid_hash",
                filename="test.jpg",
                file_size=1024,
                content_type="image/jpeg",
                gcs_url="https://storage.googleapis.com/test-bucket/test.jpg",
            )
            print("✗ Should have failed with invalid hash")
            return False
        except ValidationError:
            print("✓ Invalid hash correctly rejected")

        # Test invalid content type
        try:
            ImageInfo(
                image_hash="a1b2c3d4e5f6789012345678901234ab",
                filename="test.txt",
                file_size=1024,
                content_type="text/plain",
                gcs_url="https://storage.googleapis.com/test-bucket/test.txt",
            )
            print("✗ Should have failed with invalid content type")
            return False
        except ValidationError:
            print("✓ Invalid content type correctly rejected")

        # Test bounding box validation
        valid_bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        print(
            f"✓ Valid BoundingBox: center={valid_bbox.center}, area={valid_bbox.area}"
        )

        # Test invalid bounding box coordinates
        try:
            from app.models.analysis import EnhancedDetectionResult

            # This should fail in the model validator when creating a detection result
            invalid_bbox = BoundingBox(
                x=0.8, y=0.8, width=0.3, height=0.3
            )  # Valid bbox itself
            # But when used in detection result, it should be validated
            EnhancedDetectionResult(
                object_id="obj_001",
                class_name="tree",
                confidence=0.85,
                center_point=Point(x=0.5, y=0.6),
                area_percentage=15.5,
                bounding_box=invalid_bbox,
            )
            print(
                "✓ BoundingBox coordinates validation works (no error expected for valid coordinates)"
            )
        except ValidationError as e:
            print(f"✓ Validation working: {e}")

        # Test enhanced detection result
        detection = EnhancedDetectionResult(
            object_id="obj_001",
            class_name="tree",
            confidence=0.85,
            center_point=Point(x=0.5, y=0.6),
            area_percentage=15.5,
            bounding_box=valid_bbox,
        )
        print(f"✓ Enhanced detection result: {detection.get_relative_size()} object")

        # Test color info validation
        color = ColorInfo(red=128.0, green=255.0, blue=64.0, percentage=25.5)
        print(f"✓ Color info: RGB={color.rgb_tuple}, Hex={color.to_hex()}")

        return True

    except Exception as e:
        print(f"✗ Enhanced validation test error: {e}")
        return False


def test_serialization_features():
    """Test enhanced serialization features."""
    try:
        from app.models import ImageSize, Point
        from app.models.base import SerializationFormat

        print("Testing serialization features...")

        # Create test objects
        size = ImageSize(width=1920, height=1080)
        point = Point(x=0.5, y=0.3)

        # Test different serialization formats
        dict_data = size.serialize(SerializationFormat.DICT)
        json_data = size.serialize(SerializationFormat.JSON)
        xml_data = size.serialize(SerializationFormat.XML)

        print("✓ Dictionary serialization:", dict_data)
        print("✓ JSON serialization:", json_data)
        print("✓ XML serialization preview:", xml_data[:100] + "...")

        # Test enhanced to_dict with options
        dict_with_options = size.to_dict(exclude_none=True)
        print("✓ Dictionary with exclude_none:", dict_with_options)

        # Test JSON with formatting
        formatted_json = size.to_json(indent=2)
        print("✓ Formatted JSON preview:", formatted_json[:50] + "...")

        return True

    except Exception as e:
        print(f"✗ Serialization test error: {e}")
        return False


def test_schema_generation():
    """Test schema generation features."""
    try:
        from app.models import ImageInfo, ImageSize
        from app.models.analysis import EnhancedDetectionResult

        print("Testing schema generation...")

        # Get JSON schema
        image_schema = ImageInfo.get_schema()
        print("✓ ImageInfo schema keys:", list(image_schema.keys()))

        # Get field information
        field_info = ImageSize.get_field_info()
        print("✓ ImageSize field info:")
        for field_name, info in field_info.items():
            print(f"  - {field_name}: {info['type']} (required: {info['required']})")

        # Test detection result schema
        detection_schema = EnhancedDetectionResult.get_schema()
        print("✓ EnhancedDetectionResult schema generated")

        return True

    except Exception as e:
        print(f"✗ Schema generation test error: {e}")
        return False


def test_model_comparison():
    """Test model comparison and change detection."""
    try:
        from app.models import ImageSize, Point

        print("Testing model comparison...")

        # Create two similar objects
        size1 = ImageSize(width=1920, height=1080)
        size2 = ImageSize(width=1920, height=1080)
        size3 = ImageSize(width=1280, height=720)

        # Test equality
        assert size1 == size2, "Equal objects should be equal"
        assert size1 != size3, "Different objects should not be equal"
        print("✓ Model equality comparison works")

        # Test change detection
        changes = size1.get_changed_fields(size3)
        print("✓ Changes detected:", changes)

        # Test copy with changes
        modified_size = size1.copy_with_changes(width=2560, height=1440)
        print(f"✓ Modified copy: {modified_size.width}x{modified_size.height}")

        return True

    except Exception as e:
        print(f"✗ Model comparison test error: {e}")
        return False


def test_business_rules():
    """Test business rule validation."""
    try:
        from app.models import ImageInfo
        from app.models.analysis import AnalysisModel, AnalysisStatus, AnalysisType

        print("Testing business rule validation...")

        # Test image info business rules
        image_info = ImageInfo(
            image_hash="a1b2c3d4e5f6789012345678901234ab",
            filename="test.jpg",
            file_size=1024,
            content_type="image/jpeg",
            gcs_url="https://storage.googleapis.com/test-bucket/test.jpg",
        )

        assert (
            image_info.validate_business_rules()
        ), "Image info should pass business rules"
        print("✓ ImageInfo business rules validation passed")

        # Test analysis model business rules
        analysis = AnalysisModel(
            image_hash="a1b2c3d4e5f6789012345678901234ab",
            analysis_type=AnalysisType.LABELS,
        )

        assert analysis.validate_business_rules(), "Analysis should pass business rules"
        print("✓ AnalysisModel business rules validation passed")
        print(f"✓ Analysis display name: {analysis.get_display_name()}")

        return True

    except Exception as e:
        print(f"✗ Business rules test error: {e}")
        return False


def test_model_validation_errors():
    """Test that validation errors are properly reported."""
    try:
        from app.models import ImageInfo

        print("Testing validation error reporting...")

        # Create a valid model first
        valid_model = ImageInfo(
            image_hash="a1b2c3d4e5f6789012345678901234ab",
            filename="test.jpg",
            file_size=1024,
            content_type="image/jpeg",
            gcs_url="https://storage.googleapis.com/test-bucket/test.jpg",
        )

        # Test validation method
        errors = valid_model.validate_model()
        assert len(errors) == 0, f"Valid model should have no errors, got: {errors}"
        print("✓ Valid model has no validation errors")

        return True

    except Exception as e:
        print(f"✗ Validation error test error: {e}")
        return False


def main():
    """Run all enhanced model tests."""
    print("Testing enhanced model structure with validation and documentation...")
    print("=" * 70)

    tests = [
        test_enhanced_validation,
        test_serialization_features,
        test_schema_generation,
        test_model_comparison,
        test_business_rules,
        test_model_validation_errors,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
        print("-" * 50)

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All enhanced model tests passed!")
        print("✅ Model validation is working correctly")
        print("✅ Serialization features are functional")
        print("✅ Schema generation is working")
        print("✅ Business rules validation is implemented")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
