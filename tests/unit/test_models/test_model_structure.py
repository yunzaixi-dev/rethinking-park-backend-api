#!/usr/bin/env python3
"""
Test script to validate the new model structure.
"""

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


def test_model_imports():
    """Test that all model imports work correctly."""
    try:
        # Test base model imports
        from app.models.base import (
            AuditMixin,
            BaseModel,
            BaseRequest,
            BaseResponse,
            DomainModel,
            ErrorResponse,
            PaginatedRequest,
            PaginatedResponse,
            SoftDeleteMixin,
            TimestampMixin,
            ValidationErrorResponse,
        )

        print("✓ Base models imported successfully")

        # Test image model imports
        from app.models.image import (
            BoundingBox,
            DuplicateCheckRequest,
            DuplicateCheckResponse,
            ImageInfo,
            ImageMetadata,
            ImageModel,
            ImageProcessingOptions,
            ImageSize,
            ImageTransformation,
            ImageUploadRequest,
            ImageUploadResponse,
            Point,
        )

        print("✓ Image models imported successfully")

        # Test analysis model imports
        from app.models.analysis import (
            AnalysisModel,
            AnalysisStatus,
            AnalysisType,
            BatchOperationRequest,
            BatchOperationResult,
            ColorInfo,
            EnhancedDetectionRequest,
            EnhancedDetectionResponse,
            EnhancedDetectionResult,
            FaceDetectionResult,
            ImageAnalysisRequest,
            ImageAnalysisResponse,
            LabelAnalysisRequest,
            LabelAnalysisResponse,
            LabelAnalysisResult,
            NaturalElementsRequest,
            NaturalElementsResponse,
            NaturalElementsResult,
            SeasonalAnalysis,
            VegetationHealthMetrics,
        )

        print("✓ Analysis models imported successfully")

        # Test package-level imports
        from app.models import (
            AnalysisModel,
            BaseModel,
            BoundingBox,
            ImageModel,
            ImageSize,
            Point,
        )

        print("✓ Package-level imports work correctly")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_model_instantiation():
    """Test that models can be instantiated correctly."""
    try:
        from datetime import datetime

        from app.models import BoundingBox, ImageSize, Point

        # Test Point model
        point = Point(x=0.5, y=0.3)
        print(f"✓ Point created: {point}")

        # Test BoundingBox model
        bbox = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        print(f"✓ BoundingBox created: {bbox}")
        print(f"  - Center: {bbox.center}")
        print(f"  - Area: {bbox.area}")

        # Test ImageSize model
        size = ImageSize(width=1920, height=1080)
        print(f"✓ ImageSize created: {size}")
        print(f"  - Aspect ratio: {size.aspect_ratio}")
        print(f"  - Is landscape: {size.is_landscape()}")

        return True

    except Exception as e:
        print(f"✗ Model instantiation error: {e}")
        return False


def test_model_hierarchy():
    """Test that model hierarchy works correctly."""
    try:
        from app.models.analysis import AnalysisModel
        from app.models.base import DomainModel, TimestampMixin
        from app.models.image import ImageModel

        # Check inheritance
        assert issubclass(
            ImageModel, DomainModel
        ), "ImageModel should inherit from DomainModel"
        assert issubclass(
            AnalysisModel, DomainModel
        ), "AnalysisModel should inherit from DomainModel"
        assert issubclass(
            DomainModel, TimestampMixin
        ), "DomainModel should inherit from TimestampMixin"

        print("✓ Model hierarchy is correct")
        return True

    except Exception as e:
        print(f"✗ Model hierarchy error: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing new model structure...")
    print("=" * 50)

    tests = [test_model_imports, test_model_instantiation, test_model_hierarchy]

    passed = 0
    total = len(tests)

    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
        print("-" * 30)

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Model structure is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
