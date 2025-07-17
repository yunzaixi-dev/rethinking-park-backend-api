"""
Vision services package.

This package contains all vision-related services including:
- Google Cloud Vision API integration
- Face detection
- Object recognition
- Text extraction
- Natural elements analysis
"""

from .google_vision import GoogleVisionService

__all__ = ["GoogleVisionService"]
