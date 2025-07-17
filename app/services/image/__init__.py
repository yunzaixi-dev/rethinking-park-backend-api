"""
Image processing services package.

This package contains all image-related services including:
- Image processing and manipulation
- Object extraction
- Image enhancement
- Storage and retrieval
"""

from .processing import ImageProcessingService, SimpleExtractionResult

__all__ = ["ImageProcessingService", "SimpleExtractionResult"]
