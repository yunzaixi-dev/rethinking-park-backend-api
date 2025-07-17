"""
Test configuration settings.
Centralized configuration for test environment.
"""

import os
from typing import Any, Dict


class TestConfig:
    """Test configuration class."""

    # Test environment settings
    TESTING = True
    DEBUG = True
    LOG_LEVEL = "DEBUG"

    # Test database settings
    TEST_DATABASE_URL = "sqlite:///test.db"

    # Test cache settings
    CACHE_ENABLED = False
    TEST_CACHE_TTL = 60  # seconds

    # Test API settings
    API_BASE_URL = "http://testserver"
    API_TIMEOUT = 30  # seconds

    # Test image settings
    TEST_IMAGE_WIDTH = 100
    TEST_IMAGE_HEIGHT = 100
    TEST_IMAGE_FORMAT = "JPEG"
    MAX_TEST_IMAGE_SIZE = 1024 * 1024  # 1MB

    # Test batch processing settings
    MAX_BATCH_SIZE = 10
    BATCH_TIMEOUT = 300  # seconds

    # Test performance settings
    PERFORMANCE_TEST_TIMEOUT = 60  # seconds
    MAX_RESPONSE_TIME = 5.0  # seconds

    # Mock service settings
    MOCK_VISION_API = True
    MOCK_GCS_SERVICE = True
    MOCK_CACHE_SERVICE = True

    # Test data paths
    TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    TEST_IMAGES_DIR = os.path.join(TEST_DATA_DIR, "images")
    TEST_FIXTURES_DIR = os.path.join(TEST_DATA_DIR, "fixtures")

    # Coverage settings
    MIN_COVERAGE_THRESHOLD = 70  # percentage

    @classmethod
    def get_test_env_vars(cls) -> Dict[str, str]:
        """Get environment variables for testing."""
        return {
            "TESTING": str(cls.TESTING),
            "DEBUG": str(cls.DEBUG),
            "LOG_LEVEL": cls.LOG_LEVEL,
            "CACHE_ENABLED": str(cls.CACHE_ENABLED),
            "API_BASE_URL": cls.API_BASE_URL,
        }

    @classmethod
    def setup_test_environment(cls):
        """Set up test environment variables."""
        for key, value in cls.get_test_env_vars().items():
            os.environ[key] = value

    @classmethod
    def cleanup_test_environment(cls):
        """Clean up test environment variables."""
        for key in cls.get_test_env_vars().keys():
            os.environ.pop(key, None)


class TestMarkers:
    """Test marker definitions."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SLOW = "slow"
    API = "api"
    SERVICES = "services"
    MODELS = "models"
    CACHE = "cache"
    VISION = "vision"
    BATCH = "batch"
    PERFORMANCE = "performance"


class TestCategories:
    """Test category definitions."""

    # Unit test categories
    UNIT_MODELS = "unit/models"
    UNIT_SERVICES = "unit/services"
    UNIT_UTILS = "unit/utils"

    # Integration test categories
    INTEGRATION_API = "integration/api"
    INTEGRATION_SERVICES = "integration/services"

    # E2E test categories
    E2E_WORKFLOWS = "e2e/workflows"
    E2E_DEPLOYMENT = "e2e/deployment"


class TestDataSamples:
    """Sample test data."""

    SAMPLE_IMAGE_HASH = "test_hash_12345678"

    SAMPLE_DETECTION_REQUEST = {
        "image_hash": SAMPLE_IMAGE_HASH,
        "include_faces": True,
        "include_labels": True,
        "confidence_threshold": 0.5,
        "max_results": 50,
    }

    SAMPLE_BATCH_REQUEST = {
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
        "callback_url": "http://test.example.com/callback",
    }

    SAMPLE_VISION_RESPONSE = {
        "objects": [
            {
                "name": "person",
                "confidence": 0.95,
                "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.5},
            }
        ],
        "faces": [
            {
                "confidence": 0.9,
                "bounding_box": {"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
            }
        ],
        "labels": [
            {"description": "park", "score": 0.9},
            {"description": "outdoor", "score": 0.8},
        ],
    }

    SAMPLE_NATURAL_ELEMENTS = {
        "natural_elements": [
            {
                "type": "vegetation",
                "confidence": 0.9,
                "coverage": 0.45,
                "description": "Dense tree coverage",
            }
        ],
        "overall_naturalness": 0.8,
        "dominant_colors": ["green", "brown"],
    }
