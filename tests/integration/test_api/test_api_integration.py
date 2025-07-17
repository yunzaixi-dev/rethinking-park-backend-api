"""
Integration tests for enhanced image processing API endpoints
Tests complete processing workflows, caching system integration, and batch processing functionality
"""

import asyncio
import io
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Import the FastAPI app
from main import app

# Import models for testing
from models.image import (
    AnnotatedImageRequest,
    AnnotationStyle,
    BatchOperation,
    BatchProcessingRequest,
    BoundingBox,
    EnhancedDetectionRequest,
    LabelAnalysisRequest,
    NaturalElementsRequest,
    SimpleExtractionRequest,
)


class TestEnhancedDetectionEndpoint:
    """Test cases for enhanced object detection endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_image_hash(self):
        """Mock image hash for testing"""
        return "test_hash_12345678"

    @pytest.fixture
    def mock_image_content(self):
        """Create mock image content"""
        img = Image.new("RGB", (300, 200), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.fixture
    def detection_request_data(self, mock_image_hash):
        """Create detection request data"""
        return {
            "image_hash": mock_image_hash,
            "include_faces": True,
            "include_labels": True,
            "confidence_threshold": 0.5,
            "max_results": 50,
        }

    @patch("services.storage_service.get_image_info_by_hash")
    @patch("services.gcs_service.download_image")
    @patch("services.enhanced_vision_service.detect_objects_enhanced")
    @patch("services.cache_service.get_cached_data")
    @patch("services.cache_service.set_cached_data")
    def test_enhanced_detection_success(
        self,
        mock_cache_set,
        mock_cache_get,
        mock_enhanced_detection,
        mock_download_image,
        mock_get_image_info,
        client,
        detection_request_data,
        mock_image_content,
    ):
        """Test successful enhanced object detection"""
        # Setup mocks
        mock_cache_get.return_value = None  # No cached result
        mock_get_image_info.return_value = Mock(
            image_hash=detection_request_data["image_hash"],
            gcs_url="https://storage.googleapis.com/test/image.jpg",
        )
        mock_download_image.return_value = mock_image_content

        # Mock enhanced detection response
        from models.image import (
            BoundingBox,
            EnhancedDetectionResponse,
            EnhancedDetectionResult,
            Point,
        )

        mock_detection_response = EnhancedDetectionResponse(
            image_hash=detection_request_data["image_hash"],
            objects=[
                EnhancedDetectionResult(
                    object_id="obj_1",
                    class_name="Person",
                    confidence=0.9,
                    bounding_box=BoundingBox(x=0.1, y=0.1, width=0.3, height=0.5),
                    center_point=Point(x=0.25, y=0.35),
                    area_percentage=15.0,
                )
            ],
            faces=[],
            labels=[{"name": "Tree", "confidence": 0.8}],
            detection_time=datetime.now(),
            success=True,
            enabled=True,
        )
        mock_enhanced_detection.return_value = mock_detection_response

        # Make request
        response = client.post(
            "/api/v1/detect-objects-enhanced", json=detection_request_data
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["image_hash"] == detection_request_data["image_hash"]
        assert len(data["objects"]) == 1
        assert data["objects"][0]["class_name"] == "Person"
        assert data["objects"][0]["confidence"] == 0.9
        assert len(data["labels"]) == 1
        assert data["labels"][0]["name"] == "Tree"

        # Verify service calls
        mock_get_image_info.assert_called_once_with(
            detection_request_data["image_hash"]
        )
        mock_download_image.assert_called_once_with(
            detection_request_data["image_hash"]
        )
        mock_enhanced_detection.assert_called_once()
        mock_cache_set.assert_called_once()

    def test_enhanced_detection_image_not_found(self, client, detection_request_data):
        """Test enhanced detection with non-existent image"""
        with patch(
            "services.storage_service.get_image_info_by_hash"
        ) as mock_get_image_info:
            mock_get_image_info.return_value = None

            response = client.post(
                "/api/v1/detect-objects-enhanced", json=detection_request_data
            )

            assert response.status_code == 404
            assert "图像未找到" in response.json()["detail"]

    @patch("services.storage_service.get_image_info_by_hash")
    @patch("services.cache_service.get_cached_data")
    def test_enhanced_detection_cached_result(
        self, mock_cache_get, mock_get_image_info, client, detection_request_data
    ):
        """Test enhanced detection returning cached result"""
        # Setup cached result
        cached_result = {
            "image_hash": detection_request_data["image_hash"],
            "objects": [],
            "faces": [],
            "labels": [],
            "detection_time": datetime.now().isoformat(),
            "success": True,
            "enabled": True,
            "from_cache": False,
        }
        mock_cache_get.return_value = cached_result

        response = client.post(
            "/api/v1/detect-objects-enhanced", json=detection_request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["from_cache"] is True

        # Verify that image info was not fetched (cached result used)
        mock_get_image_info.assert_not_called()


class TestSimpleExtractionEndpoint:
    """Test cases for simple object extraction endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def extraction_request_data(self):
        """Create extraction request data"""
        return {
            "image_hash": "test_hash_12345678",
            "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.4},
            "output_format": "png",
            "add_padding": 10,
        }

    @patch("services.storage_service.get_image_info_by_hash")
    @patch("services.gcs_service.download_image")
    @patch("services.image_processing_service.validate_extraction_request")
    @patch("services.image_processing_service.extract_by_bounding_box")
    @patch("services.gcs_service.upload_image")
    @patch("services.cache_service.get_cached_data")
    @patch("services.cache_service.set_cached_data")
    def test_simple_extraction_success(
        self,
        mock_cache_set,
        mock_cache_get,
        mock_upload_image,
        mock_extract,
        mock_validate,
        mock_download_image,
        mock_get_image_info,
        client,
        extraction_request_data,
    ):
        """Test successful simple object extraction"""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_get_image_info.return_value = Mock(
            image_hash=extraction_request_data["image_hash"],
            gcs_url="https://storage.googleapis.com/test/image.jpg",
        )

        # Create mock image content
        img = Image.new("RGB", (300, 200), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        mock_image_content = buffer.getvalue()
        mock_download_image.return_value = mock_image_content

        # Mock validation
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}

        # Mock extraction result
        from models.image import ImageSize
        from services.image_processing_service import ExtractionResult

        mock_extraction_result = ExtractionResult(
            extracted_image_bytes=mock_image_content,
            original_size=ImageSize(width=300, height=200),
            extracted_size=ImageSize(width=90, height=80),
            processing_method="bounding_box",
        )
        mock_extract.return_value = mock_extraction_result

        # Mock GCS upload
        mock_upload_image.return_value = (
            "extracted_id",
            "extracted_hash",
            "https://storage.googleapis.com/test/extracted.png",
            {},
        )

        # Make request
        response = client.post(
            "/api/v1/extract-object-simple", json=extraction_request_data
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["image_hash"] == extraction_request_data["image_hash"]
        assert (
            data["result"]["extracted_image_url"]
            == "https://storage.googleapis.com/test/extracted.png"
        )
        assert data["result"]["processing_method"] == "bounding_box"
        assert data["processing_time_ms"] > 0

        # Verify service calls
        mock_validate.assert_called_once()
        mock_extract.assert_called_once()
        mock_upload_image.assert_called_once()

    def test_simple_extraction_invalid_bounding_box(self, client):
        """Test extraction with invalid bounding box coordinates"""
        invalid_request = {
            "image_hash": "test_hash_12345678",
            "bounding_box": {
                "x": -0.1,  # Invalid negative coordinate
                "y": 0.1,
                "width": 0.3,
                "height": 0.4,
            },
            "output_format": "png",
            "add_padding": 10,
        }

        with patch(
            "services.storage_service.get_image_info_by_hash"
        ) as mock_get_image_info:
            with patch("services.gcs_service.download_image") as mock_download_image:
                with patch(
                    "services.image_processing_service.validate_extraction_request"
                ) as mock_validate:
                    mock_get_image_info.return_value = Mock(
                        image_hash="test_hash_12345678"
                    )
                    mock_download_image.return_value = b"fake_image_content"
                    mock_validate.return_value = {
                        "valid": False,
                        "errors": ["Invalid bounding box coordinates"],
                        "warnings": [],
                    }

                    response = client.post(
                        "/api/v1/extract-object-simple", json=invalid_request
                    )

                    assert response.status_code == 400
                    assert "Invalid extraction request" in response.json()["detail"]


class TestLabelAnalysisEndpoint:
    """Test cases for label-based analysis endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def label_analysis_request_data(self):
        """Create label analysis request data"""
        return {
            "image_hash": "test_hash_12345678",
            "target_categories": ["Tree", "Grass", "Sky", "Building"],
            "confidence_threshold": 0.5,
            "max_labels": 20,
            "include_confidence": True,
        }

    @patch("services.storage_service.get_image_info_by_hash")
    @patch("services.gcs_service.download_image")
    @patch("services.vision_service.analyze_image")
    @patch("services.label_analysis_service.analyze_by_labels")
    @patch("services.cache_service.get_cached_data")
    @patch("services.cache_service.set_cached_data")
    def test_label_analysis_success(
        self,
        mock_cache_set,
        mock_cache_get,
        mock_analyze_by_labels,
        mock_vision_analyze,
        mock_download_image,
        mock_get_image_info,
        client,
        label_analysis_request_data,
    ):
        """Test successful label-based analysis"""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_get_image_info.return_value = Mock(
            image_hash=label_analysis_request_data["image_hash"],
            gcs_url="https://storage.googleapis.com/test/image.jpg",
        )

        # Create mock image content
        img = Image.new("RGB", (300, 200), color="green")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        mock_download_image.return_value = buffer.getvalue()

        # Mock Vision API response
        mock_vision_response = {
            "labels": [
                {"name": "Tree", "confidence": 0.9, "topicality": 0.8},
                {"name": "Grass", "confidence": 0.8, "topicality": 0.7},
                {"name": "Sky", "confidence": 0.7, "topicality": 0.9},
                {"name": "Building", "confidence": 0.6, "topicality": 0.5},
            ]
        }
        mock_vision_analyze.return_value = mock_vision_response

        # Mock label analysis service response
        mock_analysis_result = {
            "categorized_elements": {
                "vegetation": [
                    {"name": "Tree", "confidence": 0.9},
                    {"name": "Grass", "confidence": 0.8},
                ],
                "sky": [{"name": "Sky", "confidence": 0.7}],
                "built_environment": [{"name": "Building", "confidence": 0.6}],
            },
            "coverage_statistics": {
                "vegetation_coverage": 60.0,
                "sky_coverage": 25.0,
                "water_coverage": 0.0,
                "built_environment_coverage": 15.0,
            },
            "confidence_analysis": {
                "confidence_distribution": {
                    "high_confidence": 2,
                    "medium_confidence": 2,
                    "low_confidence": 0,
                }
            },
        }
        mock_analyze_by_labels.return_value = mock_analysis_result

        # Make request
        response = client.post(
            "/api/v1/analyze-by-labels", json=label_analysis_request_data
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["image_hash"] == label_analysis_request_data["image_hash"]
        assert "results" in data
        assert len(data["results"]["category_analysis"]) > 0
        assert data["results"]["natural_elements_summary"]["vegetation"] == 60.0
        assert len(data["results"]["top_categories"]) > 0

        # Verify service calls
        mock_vision_analyze.assert_called_once()
        mock_analyze_by_labels.assert_called_once()

    def test_label_analysis_vision_api_failure(
        self, client, label_analysis_request_data
    ):
        """Test label analysis when Vision API fails"""
        with patch(
            "services.storage_service.get_image_info_by_hash"
        ) as mock_get_image_info:
            with patch("services.gcs_service.download_image") as mock_download_image:
                with patch(
                    "services.vision_service.analyze_image"
                ) as mock_vision_analyze:
                    mock_get_image_info.return_value = Mock(
                        image_hash="test_hash_12345678"
                    )
                    mock_download_image.return_value = b"fake_image_content"
                    mock_vision_analyze.return_value = None  # Vision API failure

                    response = client.post(
                        "/api/v1/analyze-by-labels", json=label_analysis_request_data
                    )

                    assert response.status_code == 500
                    assert (
                        "Failed to get labels from Vision API"
                        in response.json()["detail"]
                    )


class TestNaturalElementsEndpoint:
    """Test cases for natural elements analysis endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def nature_analysis_request_data(self):
        """Create nature analysis request data"""
        return {
            "image_hash": "test_hash_12345678",
            "analysis_depth": "comprehensive",
            "include_health_assessment": True,
            "include_seasonal_analysis": True,
            "include_color_analysis": True,
            "confidence_threshold": 0.3,
        }

    @patch("services.storage_service.get_image_info_by_hash")
    @patch("services.gcs_service.download_image")
    @patch("services.vision_service.is_enabled")
    @patch("services.natural_element_analyzer.analyze_natural_elements")
    @patch("services.cache_service.get")
    @patch("services.cache_service.set")
    def test_nature_analysis_success(
        self,
        mock_cache_set,
        mock_cache_get,
        mock_analyze_natural_elements,
        mock_vision_enabled,
        mock_download_image,
        mock_get_image_info,
        client,
        nature_analysis_request_data,
    ):
        """Test successful natural elements analysis"""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_vision_enabled.return_value = True
        mock_get_image_info.return_value = Mock(
            image_hash=nature_analysis_request_data["image_hash"],
            gcs_url="https://storage.googleapis.com/test/image.jpg",
        )

        # Create mock image content
        img = Image.new("RGB", (300, 200), color="green")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        mock_download_image.return_value = buffer.getvalue()

        # Mock natural elements analysis result
        from models.image import (
            ColorInfo,
            ElementCategory,
            NaturalElementsResult,
            SeasonalAnalysis,
            VegetationHealthMetrics,
        )

        mock_analysis_result = NaturalElementsResult(
            element_categories=[
                ElementCategory(
                    category_name="vegetation",
                    confidence_score=0.85,
                    coverage_percentage=60.0,
                    detected_elements=["Tree", "Grass", "Plant"],
                )
            ],
            coverage_statistics={
                "vegetation": 60.0,
                "sky": 25.0,
                "water": 5.0,
                "built_environment": 10.0,
            },
            dominant_colors=[
                ColorInfo(color_name="Green", hex_code="#228B22", percentage=45.0),
                ColorInfo(color_name="Blue", hex_code="#87CEEB", percentage=25.0),
            ],
            vegetation_health_score=75.0,
            vegetation_health_metrics=VegetationHealthMetrics(
                greenness_index=0.7, color_diversity=0.6, coverage_density=0.8
            ),
            seasonal_indicators=["Spring", "Healthy Growth"],
            seasonal_analysis=SeasonalAnalysis(
                predicted_season="Spring",
                confidence=0.8,
                indicators=["Green foliage", "Active growth"],
            ),
            color_diversity_score=0.65,
            analysis_metadata={
                "processing_time": "2.5s",
                "vision_api_calls": 3,
                "analysis_depth": "comprehensive",
            },
        )
        mock_analyze_natural_elements.return_value = mock_analysis_result

        # Make request
        response = client.post(
            "/api/v1/analyze-nature", json=nature_analysis_request_data
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is True
        assert data["image_hash"] == nature_analysis_request_data["image_hash"]
        assert "results" in data
        assert data["results"]["vegetation_health_score"] == 75.0
        assert len(data["results"]["element_categories"]) > 0
        assert len(data["results"]["dominant_colors"]) > 0

        # Verify service calls
        mock_analyze_natural_elements.assert_called_once()

    def test_nature_analysis_vision_disabled(
        self, client, nature_analysis_request_data
    ):
        """Test nature analysis when Vision service is disabled"""
        with patch(
            "services.storage_service.get_image_info_by_hash"
        ) as mock_get_image_info:
            with patch("services.gcs_service.download_image") as mock_download_image:
                with patch("services.vision_service.is_enabled") as mock_vision_enabled:
                    mock_get_image_info.return_value = Mock(
                        image_hash="test_hash_12345678"
                    )
                    mock_download_image.return_value = b"fake_image_content"
                    mock_vision_enabled.return_value = False

                    response = client.post(
                        "/api/v1/analyze-nature", json=nature_analysis_request_data
                    )

                    assert response.status_code == 503
                    assert (
                        "Vision service is not available" in response.json()["detail"]
                    )


class TestAnnotatedImageEndpoint:
    """Test cases for annotated image download endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def annotation_request_data(self):
        """Create annotation request data"""
        return {
            "image_hash": "test_hash_12345678",
            "include_face_markers": True,
            "include_object_boxes": True,
            "include_labels": True,
            "output_format": "png",
            "quality": 95,
            "confidence_threshold": 0.5,
            "max_objects": 20,
            "annotation_style": {
                "face_marker_color": "#FFD700",
                "box_color": "#FFFFFF",
                "label_color": "#0066CC",
                "box_thickness": 2,
            },
        }

    @patch("services.storage_service.get_image_info_by_hash")
    @patch("services.gcs_service.download_image")
    @patch("services.enhanced_vision_service.detect_objects_enhanced")
    @patch("services.image_annotation_service.validate_annotation_request")
    @patch("services.image_annotation_service.render_annotated_image")
    @patch("services.gcs_service.upload_image")
    @patch("services.image_annotation_service.get_annotation_statistics")
    @patch("services.cache_service.get")
    @patch("services.cache_service.set")
    def test_annotated_image_success(
        self,
        mock_cache_set,
        mock_cache_get,
        mock_get_stats,
        mock_upload_image,
        mock_render_annotated,
        mock_validate_annotation,
        mock_enhanced_detection,
        mock_download_image,
        mock_get_image_info,
        client,
        annotation_request_data,
    ):
        """Test successful annotated image creation"""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_get_image_info.return_value = Mock(
            image_hash=annotation_request_data["image_hash"],
            gcs_url="https://storage.googleapis.com/test/image.jpg",
        )

        # Create mock image content
        img = Image.new("RGB", (300, 200), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        mock_image_content = buffer.getvalue()
        mock_download_image.return_value = mock_image_content

        # Mock enhanced detection response
        from models.image import (
            BoundingBox,
            EnhancedDetectionResponse,
            EnhancedDetectionResult,
            Point,
        )

        mock_detection_response = EnhancedDetectionResponse(
            image_hash=annotation_request_data["image_hash"],
            objects=[
                EnhancedDetectionResult(
                    object_id="obj_1",
                    class_name="Person",
                    confidence=0.9,
                    bounding_box=BoundingBox(x=0.1, y=0.1, width=0.3, height=0.5),
                    center_point=Point(x=0.25, y=0.35),
                    area_percentage=15.0,
                )
            ],
            faces=[],
            labels=[{"name": "Tree", "confidence": 0.8}],
            detection_time=datetime.now(),
            success=True,
            enabled=True,
        )
        mock_enhanced_detection.return_value = mock_detection_response

        # Mock validation
        mock_validate_annotation.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "image_info": {"width": 300, "height": 200},
        }

        # Mock annotation rendering
        annotated_img = Image.new("RGB", (300, 200), color="blue")
        annotated_buffer = io.BytesIO()
        annotated_img.save(annotated_buffer, format="PNG")
        mock_render_annotated.return_value = annotated_buffer.getvalue()

        # Mock GCS upload
        mock_upload_image.return_value = (
            "annotated_id",
            "annotated_hash",
            "https://storage.googleapis.com/test/annotated.png",
            {},
        )

        # Mock annotation statistics
        mock_get_stats.return_value = {
            "total_objects": 1,
            "total_faces": 0,
            "object_classes": {"Person": 1},
            "annotation_density": 1,
        }

        # Make request
        response = client.post(
            "/api/v1/download-annotated", json=annotation_request_data
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["image_hash"] == annotation_request_data["image_hash"]
        assert (
            data["result"]["annotated_image_url"]
            == "https://storage.googleapis.com/test/annotated.png"
        )
        assert data["result"]["annotation_stats"]["total_objects"] == 1
        assert data["processing_time_ms"] > 0

        # Verify service calls
        mock_enhanced_detection.assert_called_once()
        mock_validate_annotation.assert_called_once()
        mock_render_annotated.assert_called_once()
        mock_upload_image.assert_called_once()

    def test_annotated_image_validation_failure(self, client, annotation_request_data):
        """Test annotation with validation failure"""
        with patch(
            "services.storage_service.get_image_info_by_hash"
        ) as mock_get_image_info:
            with patch("services.gcs_service.download_image") as mock_download_image:
                with patch(
                    "services.enhanced_vision_service.detect_objects_enhanced"
                ) as mock_detection:
                    with patch(
                        "services.image_annotation_service.validate_annotation_request"
                    ) as mock_validate:
                        mock_get_image_info.return_value = Mock(
                            image_hash="test_hash_12345678"
                        )
                        mock_download_image.return_value = b"fake_image_content"

                        # Mock successful detection
                        from models.image import EnhancedDetectionResponse

                        mock_detection.return_value = EnhancedDetectionResponse(
                            image_hash="test_hash_12345678",
                            objects=[],
                            faces=[],
                            labels=[],
                            detection_time=datetime.now(),
                            success=True,
                            enabled=True,
                        )

                        # Mock validation failure
                        mock_validate.return_value = {
                            "valid": False,
                            "errors": ["Invalid annotation coordinates"],
                            "warnings": [],
                        }

                        response = client.post(
                            "/api/v1/download-annotated", json=annotation_request_data
                        )

                        assert response.status_code == 400
                        assert "Invalid annotation request" in response.json()["detail"]


class TestBatchProcessingEndpoints:
    """Test cases for batch processing endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def batch_request_data(self):
        """Create batch processing request data"""
        return {
            "operations": [
                {
                    "type": "enhanced_detection",
                    "image_hash": "test_hash_1",
                    "parameters": {"confidence_threshold": 0.5},
                    "max_retries": 3,
                },
                {
                    "type": "simple_extraction",
                    "image_hash": "test_hash_2",
                    "parameters": {
                        "bounding_box": {
                            "x": 0.1,
                            "y": 0.1,
                            "width": 0.3,
                            "height": 0.4,
                        },
                        "output_format": "png",
                    },
                    "max_retries": 2,
                },
            ],
            "callback_url": "https://example.com/callback",
            "max_concurrent_operations": 5,
        }

    @patch("services.batch_processing_service.create_batch_job")
    @patch("services.batch_processing_service.start_batch_job")
    def test_create_batch_job_success(
        self, mock_start_batch, mock_create_batch, client, batch_request_data
    ):
        """Test successful batch job creation"""
        # Setup mocks
        test_batch_id = "batch_12345678"
        mock_create_batch.return_value = test_batch_id
        mock_start_batch.return_value = True

        # Make request
        response = client.post("/api/v1/batch-process", json=batch_request_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == test_batch_id
        assert data["status"] == "running"
        assert data["total_operations"] == 2

        # Verify service calls
        mock_create_batch.assert_called_once()
        mock_start_batch.assert_called_once_with(test_batch_id)

    def test_create_batch_job_empty_operations(self, client):
        """Test batch job creation with empty operations"""
        empty_request = {
            "operations": [],
            "callback_url": "https://example.com/callback",
            "max_concurrent_operations": 5,
        }

        response = client.post("/api/v1/batch-process", json=empty_request)

        assert response.status_code == 400
        assert "Operations list cannot be empty" in response.json()["detail"]

    def test_create_batch_job_too_many_operations(self, client):
        """Test batch job creation with too many operations"""
        # Create request with 51 operations (exceeds limit of 50)
        operations = []
        for i in range(51):
            operations.append(
                {
                    "type": "enhanced_detection",
                    "image_hash": f"test_hash_{i}",
                    "parameters": {"confidence_threshold": 0.5},
                    "max_retries": 3,
                }
            )

        large_request = {
            "operations": operations,
            "callback_url": "https://example.com/callback",
            "max_concurrent_operations": 5,
        }

        response = client.post("/api/v1/batch-process", json=large_request)

        assert response.status_code == 400
        assert "Too many operations in batch" in response.json()["detail"]

    @patch("services.batch_processing_service.get_batch_status")
    def test_get_batch_status_success(self, mock_get_status, client):
        """Test successful batch status retrieval"""
        test_batch_id = "batch_12345678"

        # Mock batch status
        mock_status = {
            "batch_id": test_batch_id,
            "status": "running",
            "created_time": datetime.now().isoformat(),
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "callback_url": "https://example.com/callback",
            "max_concurrent_operations": 5,
            "total_operations": 2,
            "completed_operations": 1,
            "failed_operations": 0,
            "progress_percentage": 50.0,
            "operations": [
                {
                    "operation_id": "op_1",
                    "type": "enhanced_detection",
                    "image_hash": "test_hash_1",
                    "status": "completed",
                    "result": {"success": True},
                    "error_message": None,
                    "retry_count": 0,
                    "processing_time_ms": 1500,
                },
                {
                    "operation_id": "op_2",
                    "type": "simple_extraction",
                    "image_hash": "test_hash_2",
                    "status": "running",
                    "result": None,
                    "error_message": None,
                    "retry_count": 0,
                    "processing_time_ms": None,
                },
            ],
        }
        mock_get_status.return_value = mock_status

        # Make request
        response = client.get(f"/api/v1/batch-process/{test_batch_id}/status")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == test_batch_id
        assert data["status"] == "running"
        assert data["total_operations"] == 2
        assert data["completed_operations"] == 1
        assert data["progress_percentage"] == 50.0
        assert len(data["operations"]) == 2

        # Verify service call
        mock_get_status.assert_called_once_with(test_batch_id)

    def test_get_batch_status_not_found(self, client):
        """Test batch status retrieval for non-existent batch"""
        test_batch_id = "nonexistent_batch"

        with patch(
            "services.batch_processing_service.get_batch_status"
        ) as mock_get_status:
            mock_get_status.return_value = None

            response = client.get(f"/api/v1/batch-process/{test_batch_id}/status")

            assert response.status_code == 404
            assert f"Batch job {test_batch_id} not found" in response.json()["detail"]

    @patch("services.batch_processing_service.get_batch_results")
    def test_get_batch_results_success(self, mock_get_results, client):
        """Test successful batch results retrieval"""
        test_batch_id = "batch_12345678"

        # Mock batch results
        mock_results = {
            "batch_id": test_batch_id,
            "summary": {
                "total_operations": 2,
                "successful_operations": 1,
                "failed_operations": 1,
                "success_rate": 50.0,
                "total_processing_time_ms": 3000,
            },
            "results_by_type": {
                "enhanced_detection": {"successful": 1, "failed": 0},
                "simple_extraction": {"successful": 0, "failed": 1},
            },
            "successful_operations": [
                {
                    "operation_id": "op_1",
                    "type": "enhanced_detection",
                    "image_hash": "test_hash_1",
                    "status": "completed",
                    "result": {"success": True, "objects": []},
                    "error_message": None,
                    "retry_count": 0,
                    "processing_time_ms": 1500,
                }
            ],
            "failed_operations": [
                {
                    "operation_id": "op_2",
                    "type": "simple_extraction",
                    "image_hash": "test_hash_2",
                    "status": "failed",
                    "result": None,
                    "error_message": "Extraction failed",
                    "retry_count": 2,
                    "processing_time_ms": 1500,
                }
            ],
            "batch_metadata": {
                "created_time": datetime.now().isoformat(),
                "completed_time": datetime.now().isoformat(),
                "callback_url": "https://example.com/callback",
            },
        }
        mock_get_results.return_value = mock_results

        # Make request
        response = client.get(f"/api/v1/batch-process/{test_batch_id}/results")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == test_batch_id
        assert data["summary"]["total_operations"] == 2
        assert data["summary"]["success_rate"] == 50.0
        assert len(data["successful_operations"]) == 1
        assert len(data["failed_operations"]) == 1

        # Verify service call
        mock_get_results.assert_called_once_with(test_batch_id)

    @patch("services.batch_processing_service.cancel_batch_job")
    def test_cancel_batch_job_success(self, mock_cancel_batch, client):
        """Test successful batch job cancellation"""
        test_batch_id = "batch_12345678"
        mock_cancel_batch.return_value = True

        # Make request
        response = client.delete(f"/api/v1/batch-process/{test_batch_id}")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert f"Batch job {test_batch_id} cancelled successfully" in data["message"]

        # Verify service call
        mock_cancel_batch.assert_called_once_with(test_batch_id)

    def test_cancel_batch_job_not_found(self, client):
        """Test cancellation of non-existent batch job"""
        test_batch_id = "nonexistent_batch"

        with patch(
            "services.batch_processing_service.cancel_batch_job"
        ) as mock_cancel_batch:
            mock_cancel_batch.return_value = False

            response = client.delete(f"/api/v1/batch-process/{test_batch_id}")

            assert response.status_code == 404
            assert f"Batch job {test_batch_id} not found" in response.json()["detail"]


class TestCacheIntegration:
    """Test cache system integration across endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @patch("services.cache_service.get_cached_data")
    @patch("services.cache_service.set_cached_data")
    def test_cache_hit_and_miss_flow(self, mock_cache_set, mock_cache_get, client):
        """Test cache hit and miss flow for enhanced detection"""
        detection_request = {
            "image_hash": "test_hash_12345678",
            "include_faces": True,
            "include_labels": True,
            "confidence_threshold": 0.5,
            "max_results": 50,
        }

        # First request - cache miss
        mock_cache_get.return_value = None

        with patch(
            "services.storage_service.get_image_info_by_hash"
        ) as mock_get_image_info:
            with patch("services.gcs_service.download_image") as mock_download_image:
                with patch(
                    "services.enhanced_vision_service.detect_objects_enhanced"
                ) as mock_detection:
                    mock_get_image_info.return_value = Mock(
                        image_hash="test_hash_12345678"
                    )
                    mock_download_image.return_value = b"fake_image_content"

                    from models.image import EnhancedDetectionResponse

                    mock_detection_response = EnhancedDetectionResponse(
                        image_hash="test_hash_12345678",
                        objects=[],
                        faces=[],
                        labels=[],
                        detection_time=datetime.now(),
                        success=True,
                        enabled=True,
                    )
                    mock_detection.return_value = mock_detection_response

                    response = client.post(
                        "/api/v1/detect-objects-enhanced", json=detection_request
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["from_cache"] is False

                    # Verify cache was set
                    mock_cache_set.assert_called_once()

        # Second request - cache hit
        cached_result = {
            "image_hash": "test_hash_12345678",
            "objects": [],
            "faces": [],
            "labels": [],
            "detection_time": datetime.now().isoformat(),
            "success": True,
            "enabled": True,
            "from_cache": False,
        }
        mock_cache_get.return_value = cached_result

        response = client.post(
            "/api/v1/detect-objects-enhanced", json=detection_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["from_cache"] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
