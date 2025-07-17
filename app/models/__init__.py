"""
Models package for the application.

This package contains all data models organized by functionality:
- base: Base model classes and common functionality
- image: Image-related models
- analysis: Analysis-related models
"""

# Analysis models
from .analysis import (
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

# Base models
from .base import (
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

# Image models
from .image import (
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

__all__ = [
    # Base models
    "BaseModel",
    "BaseRequest",
    "BaseResponse",
    "TimestampMixin",
    "PaginatedRequest",
    "PaginatedResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "DomainModel",
    "AuditMixin",
    "SoftDeleteMixin",
    # Image models
    "ImageModel",
    "ImageInfo",
    "ImageUploadRequest",
    "ImageUploadResponse",
    "DuplicateCheckRequest",
    "DuplicateCheckResponse",
    "Point",
    "BoundingBox",
    "ImageSize",
    "ImageMetadata",
    "ImageProcessingOptions",
    "ImageTransformation",
    # Analysis models
    "AnalysisModel",
    "AnalysisType",
    "AnalysisStatus",
    "ImageAnalysisRequest",
    "ImageAnalysisResponse",
    "EnhancedDetectionRequest",
    "EnhancedDetectionResponse",
    "EnhancedDetectionResult",
    "FaceDetectionResult",
    "NaturalElementsRequest",
    "NaturalElementsResponse",
    "NaturalElementsResult",
    "LabelAnalysisRequest",
    "LabelAnalysisResponse",
    "LabelAnalysisResult",
    "ColorInfo",
    "VegetationHealthMetrics",
    "SeasonalAnalysis",
    "BatchOperationRequest",
    "BatchOperationResult",
]
