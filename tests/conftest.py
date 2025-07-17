"""
Pytest configuration and shared fixtures for the test suite.
This file contains common test fixtures, configuration, and utilities
used across all test modules.
"""

import asyncio
import io
import os

# Import the main application
import sys
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as async_test_client:
        yield async_test_client


@pytest.fixture
def sample_image() -> io.BytesIO:
    """Create a sample test image."""
    image = Image.new("RGB", (100, 100), color="red")
    img_buffer = io.BytesIO()
    image.save(img_buffer, format="JPEG")
    img_buffer.seek(0)
    return img_buffer


@pytest.fixture
def sample_image_file():
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        image = Image.new("RGB", (100, 100), color="blue")
        image.save(tmp_file.name, format="JPEG")
        yield tmp_file.name
    os.unlink(tmp_file.name)


@pytest.fixture
def mock_vision_service():
    """Mock the Google Vision service."""
    with patch("services.enhanced_vision_service.EnhancedVisionService") as mock:
        mock_instance = Mock()
        mock_instance.detect_objects = AsyncMock(
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
        mock_instance.detect_faces = AsyncMock(
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
        mock_instance.analyze_labels = AsyncMock(
            return_value={
                "labels": [
                    {"description": "tree", "score": 0.8},
                    {"description": "park", "score": 0.7},
                ]
            }
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_cache_service():
    """Mock the cache service."""
    with patch("services.cache_service.CacheService") as mock:
        mock_instance = Mock()
        mock_instance.get = AsyncMock(return_value=None)
        mock_instance.set = AsyncMock(return_value=True)
        mock_instance.delete = AsyncMock(return_value=True)
        mock_instance.exists = AsyncMock(return_value=False)
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_gcs_service():
    """Mock the Google Cloud Storage service."""
    with patch("services.gcs_service.GCSService") as mock:
        mock_instance = Mock()
        mock_instance.upload_image = AsyncMock(return_value="gs://bucket/image.jpg")
        mock_instance.download_image = AsyncMock(return_value=b"fake_image_data")
        mock_instance.delete_image = AsyncMock(return_value=True)
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def test_image_hash():
    """Provide a consistent test image hash."""
    return "test_hash_12345"


@pytest.fixture
def test_batch_request():
    """Provide a sample batch processing request."""
    return {
        "operations": [
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
        ],
        "callback_url": "http://example.com/callback",
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {"TESTING": "true", "CACHE_ENABLED": "false", "LOG_LEVEL": "DEBUG"}

    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# Test data fixtures
@pytest.fixture
def test_detection_results():
    """Provide sample detection results for testing."""
    return {
        "objects": [
            {
                "name": "person",
                "confidence": 0.95,
                "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.5},
            },
            {
                "name": "tree",
                "confidence": 0.87,
                "bounding_box": {"x": 0.6, "y": 0.2, "width": 0.3, "height": 0.7},
            },
        ],
        "faces": [
            {
                "confidence": 0.92,
                "bounding_box": {"x": 0.15, "y": 0.15, "width": 0.1, "height": 0.15},
            }
        ],
        "labels": [
            {"description": "park", "score": 0.9},
            {"description": "outdoor", "score": 0.85},
            {"description": "nature", "score": 0.8},
        ],
    }


@pytest.fixture
def test_natural_elements():
    """Provide sample natural elements analysis results."""
    return {
        "natural_elements": [
            {
                "type": "vegetation",
                "confidence": 0.9,
                "coverage": 0.45,
                "description": "Dense tree coverage",
            },
            {
                "type": "water",
                "confidence": 0.7,
                "coverage": 0.1,
                "description": "Small pond visible",
            },
        ],
        "overall_naturalness": 0.8,
        "dominant_colors": ["green", "brown", "blue"],
    }


@pytest.fixture
def test_batch_operations():
    """Provide sample batch operations for testing."""
    return [
        {
            "type": "detect_objects",
            "image_hash": "hash_001",
            "parameters": {"confidence_threshold": 0.5},
        },
        {
            "type": "detect_faces",
            "image_hash": "hash_002",
            "parameters": {"min_confidence": 0.7},
        },
        {
            "type": "analyze_labels",
            "image_hash": "hash_003",
            "parameters": {"max_results": 10},
        },
    ]


# Test utilities
class TestDataManager:
    """Utility class for managing test data."""

    @staticmethod
    def create_test_image(width=100, height=100, color="red", format="JPEG"):
        """Create a test image with specified parameters."""
        image = Image.new("RGB", (width, height), color=color)
        img_buffer = io.BytesIO()
        image.save(img_buffer, format=format)
        img_buffer.seek(0)
        return img_buffer

    @staticmethod
    def create_test_image_hash(prefix="test"):
        """Create a consistent test image hash."""
        import hashlib
        import time

        content = f"{prefix}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()

    @staticmethod
    def mock_api_response(status_code=200, data=None):
        """Create a mock API response."""
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data or {}
        return response


@pytest.fixture
def test_data_manager():
    """Provide test data manager utility."""
    return TestDataManager()


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Monitor test performance."""
    import time

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return PerformanceMonitor()


# Database and cache test utilities
@pytest.fixture
def clean_cache():
    """Ensure clean cache state for tests."""
    # Mock cache cleanup
    yield
    # Cleanup after test


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow
pytest.mark.api = pytest.mark.api
pytest.mark.services = pytest.mark.services
pytest.mark.models = pytest.mark.models


# Additional test utilities for better test organization


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing."""
    import tempfile

    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        # Create a simple test image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(tmp.name)
        yield tmp.name

    # Cleanup
    try:
        os.unlink(tmp.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_image_data():
    """Sample image data for testing."""
    return {
        "filename": "test_image.jpg",
        "size": (800, 600),
        "format": "JPEG",
        "mode": "RGB",
    }
