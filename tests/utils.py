"""
Test utilities and helper functions.
Common utilities used across different test modules.
"""

import asyncio
import hashlib
import io
import json
import os
import tempfile
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

from PIL import Image


class TestImageGenerator:
    """Utility class for generating test images."""

    @staticmethod
    def create_solid_color_image(
        width: int = 100, height: int = 100, color: str = "red", format: str = "JPEG"
    ) -> io.BytesIO:
        """Create a solid color test image."""
        image = Image.new("RGB", (width, height), color=color)
        img_buffer = io.BytesIO()
        image.save(img_buffer, format=format)
        img_buffer.seek(0)
        return img_buffer

    @staticmethod
    def create_gradient_image(width: int = 100, height: int = 100) -> io.BytesIO:
        """Create a gradient test image."""
        image = Image.new("RGB", (width, height))
        pixels = []
        for y in range(height):
            for x in range(width):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = 128
                pixels.append((r, g, b))
        image.putdata(pixels)

        img_buffer = io.BytesIO()
        image.save(img_buffer, format="JPEG")
        img_buffer.seek(0)
        return img_buffer

    @staticmethod
    def create_test_image_with_shapes(
        width: int = 200, height: int = 200
    ) -> io.BytesIO:
        """Create a test image with geometric shapes."""
        from PIL import ImageDraw

        image = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(image)

        # Draw a rectangle
        draw.rectangle([20, 20, 80, 80], fill="red", outline="black")

        # Draw a circle
        draw.ellipse([120, 20, 180, 80], fill="blue", outline="black")

        # Draw a triangle (polygon)
        draw.polygon([100, 120, 80, 180, 120, 180], fill="green", outline="black")

        img_buffer = io.BytesIO()
        image.save(img_buffer, format="JPEG")
        img_buffer.seek(0)
        return img_buffer


class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_detection_request(
        image_hash: str = "test_hash",
        include_faces: bool = True,
        include_labels: bool = True,
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Create a test detection request."""
        return {
            "image_hash": image_hash,
            "include_faces": include_faces,
            "include_labels": include_labels,
            "confidence_threshold": confidence_threshold,
            "max_results": 50,
        }

    @staticmethod
    def create_batch_request(operations: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Create a test batch processing request."""
        if operations is None:
            operations = [
                {
                    "type": "detect_objects",
                    "image_hash": "test_hash_1",
                    "parameters": {"confidence_threshold": 0.5},
                },
                {
                    "type": "detect_faces",
                    "image_hash": "test_hash_2",
                    "parameters": {"min_confidence": 0.7},
                },
            ]

        return {
            "operations": operations,
            "callback_url": "http://test.example.com/callback",
        }

    @staticmethod
    def create_vision_response(
        objects: Optional[List] = None,
        faces: Optional[List] = None,
        labels: Optional[List] = None,
    ) -> Dict[str, Any]:
        """Create a mock vision API response."""
        if objects is None:
            objects = [
                {
                    "name": "person",
                    "confidence": 0.95,
                    "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.5},
                }
            ]

        if faces is None:
            faces = [
                {
                    "confidence": 0.9,
                    "bounding_box": {"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
                }
            ]

        if labels is None:
            labels = [
                {"description": "park", "score": 0.9},
                {"description": "outdoor", "score": 0.8},
            ]

        return {"objects": objects, "faces": faces, "labels": labels}


class MockServiceFactory:
    """Factory for creating mock services."""

    @staticmethod
    def create_mock_vision_service():
        """Create a mock vision service."""
        mock_service = Mock()
        mock_service.detect_objects = AsyncMock(
            return_value={
                "objects": [
                    {
                        "name": "person",
                        "confidence": 0.95,
                        "bounding_box": {
                            "x": 0.1,
                            "y": 0.1,
                            "width": 0.3,
                            "height": 0.5,
                        },
                    }
                ]
            }
        )
        mock_service.detect_faces = AsyncMock(
            return_value={
                "faces": [
                    {
                        "confidence": 0.9,
                        "bounding_box": {
                            "x": 0.2,
                            "y": 0.2,
                            "width": 0.2,
                            "height": 0.2,
                        },
                    }
                ]
            }
        )
        mock_service.analyze_labels = AsyncMock(
            return_value={
                "labels": [
                    {"description": "park", "score": 0.9},
                    {"description": "outdoor", "score": 0.8},
                ]
            }
        )
        return mock_service

    @staticmethod
    def create_mock_cache_service():
        """Create a mock cache service."""
        mock_service = Mock()
        mock_service.get = AsyncMock(return_value=None)
        mock_service.set = AsyncMock(return_value=True)
        mock_service.delete = AsyncMock(return_value=True)
        mock_service.exists = AsyncMock(return_value=False)
        mock_service.clear = AsyncMock(return_value=True)
        return mock_service

    @staticmethod
    def create_mock_gcs_service():
        """Create a mock Google Cloud Storage service."""
        mock_service = Mock()
        mock_service.upload_image = AsyncMock(return_value="gs://bucket/test_image.jpg")
        mock_service.download_image = AsyncMock(return_value=b"fake_image_data")
        mock_service.delete_image = AsyncMock(return_value=True)
        mock_service.list_images = AsyncMock(return_value=["image1.jpg", "image2.jpg"])
        return mock_service


class TestFileManager:
    """Utility for managing temporary test files."""

    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []

    def create_temp_image_file(self, suffix=".jpg", content=None):
        """Create a temporary image file."""
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)

        if content is None:
            # Create a simple test image
            image = Image.new("RGB", (100, 100), color="red")
            image.save(temp_file.name, format="JPEG")
        else:
            temp_file.write(content)

        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def create_temp_json_file(self, data: Dict[str, Any], suffix=".json"):
        """Create a temporary JSON file."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
        json.dump(data, temp_file, indent=2)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def cleanup(self):
        """Clean up all temporary files and directories."""
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass

        for dir_path in self.temp_dirs:
            try:
                os.rmdir(dir_path)
            except (FileNotFoundError, OSError):
                pass

        self.temp_files.clear()
        self.temp_dirs.clear()


class TestHashGenerator:
    """Utility for generating consistent test hashes."""

    @staticmethod
    def generate_image_hash(prefix: str = "test", suffix: str = "") -> str:
        """Generate a consistent test image hash."""
        content = f"{prefix}_{suffix}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
    def generate_batch_id(prefix: str = "batch") -> str:
        """Generate a test batch ID."""
        content = f"{prefix}_{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class AsyncTestHelper:
    """Helper utilities for async testing."""

    @staticmethod
    async def wait_for_condition(
        condition_func, timeout: float = 5.0, interval: float = 0.1
    ):
        """Wait for a condition to become true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if (
                await condition_func()
                if asyncio.iscoroutinefunction(condition_func)
                else condition_func()
            ):
                return True
            await asyncio.sleep(interval)
        return False

    @staticmethod
    async def run_with_timeout(coro, timeout: float = 10.0):
        """Run a coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=timeout)


class TestAssertions:
    """Custom assertion helpers for testing."""

    @staticmethod
    def assert_valid_image_hash(hash_value: str):
        """Assert that a value is a valid image hash."""
        assert isinstance(hash_value, str), "Hash must be a string"
        assert len(hash_value) > 0, "Hash cannot be empty"
        assert len(hash_value) <= 64, "Hash is too long"

    @staticmethod
    def assert_valid_bounding_box(bbox: Dict[str, float]):
        """Assert that a bounding box is valid."""
        required_keys = ["x", "y", "width", "height"]
        for key in required_keys:
            assert key in bbox, f"Bounding box missing key: {key}"
            assert isinstance(
                bbox[key], (int, float)
            ), f"Bounding box {key} must be numeric"
            assert 0 <= bbox[key] <= 1, f"Bounding box {key} must be between 0 and 1"

    @staticmethod
    def assert_valid_detection_result(result: Dict[str, Any]):
        """Assert that a detection result is valid."""
        assert isinstance(result, dict), "Detection result must be a dictionary"

        if "objects" in result:
            assert isinstance(result["objects"], list), "Objects must be a list"
            for obj in result["objects"]:
                assert "name" in obj, "Object must have a name"
                assert "confidence" in obj, "Object must have confidence"
                if "bounding_box" in obj:
                    TestAssertions.assert_valid_bounding_box(obj["bounding_box"])

        if "faces" in result:
            assert isinstance(result["faces"], list), "Faces must be a list"
            for face in result["faces"]:
                assert "confidence" in face, "Face must have confidence"
                if "bounding_box" in face:
                    TestAssertions.assert_valid_bounding_box(face["bounding_box"])

        if "labels" in result:
            assert isinstance(result["labels"], list), "Labels must be a list"
            for label in result["labels"]:
                assert "description" in label, "Label must have description"
                assert "score" in label, "Label must have score"
