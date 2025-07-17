"""
Test helper functions and utilities.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock

from PIL import Image


def create_mock_image_response(width: int = 800, height: int = 600) -> Dict[str, Any]:
    """Create a mock image analysis response."""
    return {
        "status": "success",
        "image_info": {
            "width": width,
            "height": height,
            "format": "JPEG",
            "mode": "RGB",
        },
        "analysis_results": {
            "labels": [
                {"name": "tree", "confidence": 0.95},
                {"name": "grass", "confidence": 0.87},
            ],
            "objects": [],
            "faces": [],
        },
    }


def create_test_image(width: int = 100, height: int = 100, color: str = "red") -> str:
    """Create a temporary test image file."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new("RGB", (width, height), color=color)
        img.save(tmp.name)
        return tmp.name


def mock_vision_service_response(labels: list = None, objects: list = None):
    """Create a mock vision service response."""
    return {
        "labels": labels
        or [
            {"description": "Tree", "score": 0.95},
            {"description": "Grass", "score": 0.87},
        ],
        "objects": objects or [],
        "safe_search": {
            "adult": "VERY_UNLIKELY",
            "spoof": "UNLIKELY",
            "medical": "UNLIKELY",
            "violence": "UNLIKELY",
            "racy": "UNLIKELY",
        },
    }


def assert_valid_response_structure(response: Dict[str, Any], required_fields: list):
    """Assert that a response has the required structure."""
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"


def cleanup_test_files(*file_paths: str):
    """Clean up test files."""
    for file_path in file_paths:
        try:
            Path(file_path).unlink()
        except FileNotFoundError:
            pass
