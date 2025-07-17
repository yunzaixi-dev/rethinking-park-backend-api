"""
Unit tests for enhanced image processing services
Tests Google Vision API integration accuracy, face detection, and annotation rendering
"""

import asyncio
import base64
import io
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image, ImageDraw

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import vision
    from google.cloud.exceptions import GoogleCloudError

    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

    # Mock Google Cloud classes for testing
    class MockVision:
        class Image:
            def __init__(self, content):
                self.content = content

    class MockGoogleCloudError(Exception):
        pass

    vision = MockVision()
    GoogleCloudError = MockGoogleCloudError


# Mock model classes for testing
class BoundingBox:
    def __init__(self, x, y, width, height, normalized_vertices=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.normalized_vertices = normalized_vertices or []


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class ImageSize:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class EnhancedDetectionResult:
    def __init__(
        self,
        object_id,
        class_name,
        confidence,
        bounding_box,
        center_point,
        area_percentage,
    ):
        self.object_id = object_id
        self.class_name = class_name
        self.confidence = confidence
        self.bounding_box = bounding_box
        self.center_point = center_point
        self.area_percentage = area_percentage


class FaceDetectionResult:
    def __init__(
        self,
        face_id,
        bounding_box,
        center_point,
        confidence,
        landmarks=None,
        emotions=None,
        anonymized=True,
    ):
        self.face_id = face_id
        self.bounding_box = bounding_box
        self.center_point = center_point
        self.confidence = confidence
        self.landmarks = landmarks
        self.emotions = emotions
        self.anonymized = anonymized


class FaceLandmark:
    def __init__(self, type, position):
        self.type = type
        self.position = position


class TestEnhancedVisionService:
    """Test cases for EnhancedVisionService"""

    @pytest.fixture
    def service(self):
        """Create EnhancedVisionService instance for testing"""
        service = EnhancedVisionService()
        service.enabled = True
        return service

    @pytest.fixture
    def mock_image_content(self):
        """Create mock image content for testing"""
        # Create a simple test image
        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.fixture
    def mock_vision_client(self):
        """Create mock Google Vision client"""
        mock_client = Mock()

        # Mock object localization response
        mock_object = Mock()
        mock_object.name = "Person"
        mock_object.score = 0.85

        # Mock bounding poly with normalized vertices
        mock_vertex1 = Mock()
        mock_vertex1.x = 0.1
        mock_vertex1.y = 0.1
        mock_vertex2 = Mock()
        mock_vertex2.x = 0.4
        mock_vertex2.y = 0.1
        mock_vertex3 = Mock()
        mock_vertex3.x = 0.4
        mock_vertex3.y = 0.6
        mock_vertex4 = Mock()
        mock_vertex4.x = 0.1
        mock_vertex4.y = 0.6

        mock_object.bounding_poly.normalized_vertices = [
            mock_vertex1,
            mock_vertex2,
            mock_vertex3,
            mock_vertex4,
        ]

        mock_response = Mock()
        mock_response.localized_object_annotations = [mock_object]
        mock_client.object_localization.return_value = mock_response

        # Mock label detection response
        mock_label = Mock()
        mock_label.description = "Tree"
        mock_label.score = 0.9
        mock_label.topicality = 0.8

        mock_label_response = Mock()
        mock_label_response.label_annotations = [mock_label]
        mock_client.label_detection.return_value = mock_label_response

        return mock_client

    @pytest.mark.asyncio
    async def test_detect_objects_enhanced_success(
        self, service, mock_image_content, mock_vision_client
    ):
        """Test successful enhanced object detection"""
        service.client = mock_vision_client

        result = await service.detect_objects_enhanced(
            image_content=mock_image_content,
            image_hash="test_hash",
            include_faces=False,
            include_labels=True,
            confidence_threshold=0.5,
        )

        assert result.success is True
        assert result.image_hash == "test_hash"
        assert len(result.objects) == 1
        assert result.objects[0].class_name == "Person"
        assert result.objects[0].confidence == 0.85
        assert result.objects[0].bounding_box.x == 0.1
        assert result.objects[0].bounding_box.y == 0.1
        assert result.objects[0].bounding_box.width == 0.3
        assert result.objects[0].bounding_box.height == 0.5
        assert len(result.labels) == 1
        assert result.labels[0]["name"] == "Tree"

    @pytest.mark.asyncio
    async def test_detect_objects_enhanced_disabled_service(
        self, service, mock_image_content
    ):
        """Test detection when service is disabled"""
        service.enabled = False

        result = await service.detect_objects_enhanced(
            image_content=mock_image_content, image_hash="test_hash"
        )

        assert result.success is False
        assert result.enabled is False
        assert "not enabled" in result.error_message
        assert len(result.objects) == 0

    @pytest.mark.asyncio
    async def test_detect_objects_enhanced_vision_api_error(
        self, service, mock_image_content
    ):
        """Test handling of Google Vision API errors"""
        mock_client = Mock()
        mock_client.object_localization.side_effect = GoogleCloudError("API Error")
        service.client = mock_client

        result = await service.detect_objects_enhanced(
            image_content=mock_image_content, image_hash="test_hash"
        )

        assert result.success is False
        assert result.enabled is True
        assert "API Error" in result.error_message
        assert len(result.objects) == 0

    @pytest.mark.asyncio
    async def test_confidence_filtering(
        self, service, mock_image_content, mock_vision_client
    ):
        """Test confidence threshold filtering"""
        # Create mock objects with different confidence scores
        mock_high_conf = Mock()
        mock_high_conf.name = "Person"
        mock_high_conf.score = 0.9
        mock_high_conf.bounding_poly.normalized_vertices = [
            Mock(x=0.1, y=0.1),
            Mock(x=0.4, y=0.1),
            Mock(x=0.4, y=0.6),
            Mock(x=0.1, y=0.6),
        ]

        mock_low_conf = Mock()
        mock_low_conf.name = "Car"
        mock_low_conf.score = 0.3
        mock_low_conf.bounding_poly.normalized_vertices = [
            Mock(x=0.5, y=0.5),
            Mock(x=0.8, y=0.5),
            Mock(x=0.8, y=0.8),
            Mock(x=0.5, y=0.8),
        ]

        mock_response = Mock()
        mock_response.localized_object_annotations = [mock_high_conf, mock_low_conf]
        mock_vision_client.object_localization.return_value = mock_response

        service.client = mock_vision_client

        result = await service.detect_objects_enhanced(
            image_content=mock_image_content,
            image_hash="test_hash",
            confidence_threshold=0.5,
            include_faces=False,
            include_labels=False,
        )

        # Only high confidence object should be returned
        assert len(result.objects) == 1
        assert result.objects[0].class_name == "Person"
        assert result.objects[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_bounding_box_calculation_accuracy(
        self, service, mock_image_content, mock_vision_client
    ):
        """Test accuracy of bounding box coordinate calculations"""
        service.client = mock_vision_client

        result = await service.detect_objects_enhanced(
            image_content=mock_image_content,
            image_hash="test_hash",
            include_faces=False,
            include_labels=False,
        )

        bbox = result.objects[0].bounding_box
        center = result.objects[0].center_point

        # Verify bounding box calculations
        assert bbox.x == 0.1
        assert bbox.y == 0.1
        assert bbox.width == 0.3  # 0.4 - 0.1
        assert bbox.height == 0.5  # 0.6 - 0.1

        # Verify center point calculations
        expected_center_x = 0.1 + 0.3 / 2  # 0.25
        expected_center_y = 0.1 + 0.5 / 2  # 0.35
        assert abs(center.x - expected_center_x) < 0.001
        assert abs(center.y - expected_center_y) < 0.001

        # Verify area percentage calculation
        expected_area = 0.3 * 0.5 * 100  # 15%
        assert abs(result.objects[0].area_percentage - expected_area) < 0.001

    @pytest.mark.asyncio
    async def test_natural_elements_analysis(self, service, mock_image_content):
        """Test natural elements analysis functionality"""
        # Mock label detection for natural elements
        mock_client = Mock()

        mock_tree_label = Mock()
        mock_tree_label.description = "Tree"
        mock_tree_label.score = 0.9
        mock_tree_label.topicality = 0.8

        mock_grass_label = Mock()
        mock_grass_label.description = "Grass"
        mock_grass_label.score = 0.7
        mock_grass_label.topicality = 0.6

        mock_sky_label = Mock()
        mock_sky_label.description = "Sky"
        mock_sky_label.score = 0.8
        mock_sky_label.topicality = 0.9

        mock_response = Mock()
        mock_response.label_annotations = [
            mock_tree_label,
            mock_grass_label,
            mock_sky_label,
        ]
        mock_client.label_detection.return_value = mock_response

        service.client = mock_client

        result = await service.analyze_natural_elements(mock_image_content)

        assert result["enabled"] is True
        assert "natural_elements" in result
        assert "color_analysis" in result
        assert "vegetation_health_score" in result

        # Check categorization
        categories = result["natural_elements"]["categories"]
        assert len(categories["vegetation"]) == 2  # Tree and Grass
        assert len(categories["sky"]) == 1  # Sky

        # Check coverage statistics
        coverage = result["natural_elements"]["coverage_statistics"]
        assert coverage["vegetation_coverage"] > 0
        assert coverage["sky_coverage"] > 0

    def test_color_analysis_accuracy(self, service):
        """Test color analysis accuracy for vegetation health assessment"""
        # Create test image with known colors
        img = Image.new("RGB", (100, 100), color=(50, 150, 50))  # Green-dominant
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_content = buffer.getvalue()

        pil_image = Image.open(io.BytesIO(image_content))
        color_analysis = service._analyze_image_colors(pil_image)

        # Verify color analysis results
        assert (
            color_analysis["dominant_colors"]["green"]
            > color_analysis["dominant_colors"]["red"]
        )
        assert (
            color_analysis["dominant_colors"]["green"]
            > color_analysis["dominant_colors"]["blue"]
        )
        assert color_analysis["green_ratio"] > 0.3  # Should be high for green image
        assert color_analysis["brightness"] > 0

    def test_vegetation_health_calculation(self, service):
        """Test vegetation health score calculation"""
        # Mock natural elements data
        natural_elements = {"coverage_statistics": {"vegetation_coverage": 60.0}}

        # Mock color analysis data
        color_analysis = {"green_ratio": 0.4}

        health_score = service._calculate_vegetation_health(
            natural_elements, color_analysis
        )

        assert health_score is not None
        assert 0 <= health_score <= 100
        assert health_score > 30  # Should be decent for good green ratio and coverage


class TestFaceDetectionService:
    """Test cases for FaceDetectionService"""

    @pytest.fixture
    def service(self):
        """Create FaceDetectionService instance for testing"""
        service = FaceDetectionService()
        service.enabled = True
        return service

    @pytest.fixture
    def mock_image_content(self):
        """Create mock image content for testing"""
        img = Image.new("RGB", (200, 200), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.fixture
    def mock_face_client(self):
        """Create mock Google Vision client for face detection"""
        mock_client = Mock()

        # Mock face detection response
        mock_face = Mock()
        mock_face.detection_confidence = 0.9

        # Mock bounding poly with pixel coordinates
        mock_vertex1 = Mock()
        mock_vertex1.x = 50
        mock_vertex1.y = 30
        mock_vertex2 = Mock()
        mock_vertex2.x = 120
        mock_vertex2.y = 30
        mock_vertex3 = Mock()
        mock_vertex3.x = 120
        mock_vertex3.y = 100
        mock_vertex4 = Mock()
        mock_vertex4.x = 50
        mock_vertex4.y = 100

        mock_face.bounding_poly.vertices = [
            mock_vertex1,
            mock_vertex2,
            mock_vertex3,
            mock_vertex4,
        ]

        # Mock emotion likelihoods
        mock_face.joy_likelihood.name = "LIKELY"
        mock_face.sorrow_likelihood.name = "UNLIKELY"
        mock_face.anger_likelihood.name = "UNLIKELY"
        mock_face.surprise_likelihood.name = "POSSIBLE"

        # Mock landmarks
        mock_face.landmarks = []

        mock_response = Mock()
        mock_response.face_annotations = [mock_face]
        mock_client.face_detection.return_value = mock_response

        return mock_client

    @pytest.mark.asyncio
    async def test_detect_faces_enhanced_success(
        self, service, mock_image_content, mock_face_client
    ):
        """Test successful face detection with position marking"""
        service.client = mock_face_client

        result = await service.detect_faces_enhanced(
            image_content=mock_image_content,
            include_demographics=False,
            anonymize_results=True,
            confidence_threshold=0.5,
        )

        assert result.success is True
        assert result.total_faces == 1
        assert result.anonymized is True
        assert len(result.faces) == 1

        face = result.faces[0]
        assert face.confidence == 0.9
        assert face.anonymized is True
        assert face.face_id.startswith("face_")

        # Check bounding box calculations
        assert face.bounding_box.x == 50.0
        assert face.bounding_box.y == 30.0
        assert face.bounding_box.width == 70.0  # 120 - 50
        assert face.bounding_box.height == 70.0  # 100 - 30

        # Check center point calculations
        expected_center_x = 50 + 70 / 2  # 85
        expected_center_y = 30 + 70 / 2  # 65
        assert face.center_point.x == expected_center_x
        assert face.center_point.y == expected_center_y

    @pytest.mark.asyncio
    async def test_face_detection_confidence_filtering(
        self, service, mock_image_content
    ):
        """Test confidence threshold filtering for face detection"""
        mock_client = Mock()

        # Create faces with different confidence scores
        mock_high_conf_face = Mock()
        mock_high_conf_face.detection_confidence = 0.9
        mock_high_conf_face.bounding_poly.vertices = [
            Mock(x=10, y=10),
            Mock(x=50, y=10),
            Mock(x=50, y=50),
            Mock(x=10, y=50),
        ]
        mock_high_conf_face.joy_likelihood.name = "LIKELY"
        mock_high_conf_face.sorrow_likelihood.name = "UNLIKELY"
        mock_high_conf_face.anger_likelihood.name = "UNLIKELY"
        mock_high_conf_face.surprise_likelihood.name = "POSSIBLE"
        mock_high_conf_face.landmarks = []

        mock_low_conf_face = Mock()
        mock_low_conf_face.detection_confidence = 0.3
        mock_low_conf_face.bounding_poly.vertices = [
            Mock(x=100, y=100),
            Mock(x=140, y=100),
            Mock(x=140, y=140),
            Mock(x=100, y=140),
        ]
        mock_low_conf_face.joy_likelihood.name = "UNLIKELY"
        mock_low_conf_face.sorrow_likelihood.name = "UNLIKELY"
        mock_low_conf_face.anger_likelihood.name = "UNLIKELY"
        mock_low_conf_face.surprise_likelihood.name = "UNLIKELY"
        mock_low_conf_face.landmarks = []

        mock_response = Mock()
        mock_response.face_annotations = [mock_high_conf_face, mock_low_conf_face]
        mock_client.face_detection.return_value = mock_response

        service.client = mock_client

        result = await service.detect_faces_enhanced(
            image_content=mock_image_content, confidence_threshold=0.5
        )

        # Only high confidence face should be returned
        assert len(result.faces) == 1
        assert result.faces[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_face_detection_anonymization(
        self, service, mock_image_content, mock_face_client
    ):
        """Test face detection anonymization functionality"""
        service.client = mock_face_client

        # Test with anonymization enabled
        result_anon = await service.detect_faces_enhanced(
            image_content=mock_image_content,
            anonymize_results=True,
            include_demographics=False,
        )

        face_anon = result_anon.faces[0]
        assert face_anon.anonymized is True
        assert face_anon.emotions is None or len(face_anon.emotions) == 0

        # Test with anonymization disabled
        result_no_anon = await service.detect_faces_enhanced(
            image_content=mock_image_content,
            anonymize_results=False,
            include_demographics=True,
        )

        face_no_anon = result_no_anon.faces[0]
        assert face_no_anon.anonymized is False
        assert face_no_anon.emotions is not None
        assert len(face_no_anon.emotions) > 0

    def test_create_face_markers_image(self, service, mock_image_content):
        """Test face marker image creation"""
        # Create test face result
        face = FaceDetectionResult(
            face_id="test_face",
            bounding_box=BoundingBox(x=50, y=50, width=40, height=40),
            center_point=Point(x=70, y=70),
            confidence=0.9,
            anonymized=True,
        )

        result_image = service.create_face_markers_image(
            image_content=mock_image_content,
            faces=[face],
            marker_color="#FFD700",
            marker_radius=8,
        )

        # Verify that we get image data back
        assert isinstance(result_image, bytes)
        assert len(result_image) > 0

        # Verify the image can be opened
        pil_image = Image.open(io.BytesIO(result_image))
        assert pil_image.size == (200, 200)  # Original image size

    def test_face_statistics_calculation(self, service):
        """Test face statistics calculation"""
        faces = [
            FaceDetectionResult(
                face_id="face1",
                bounding_box=BoundingBox(x=0.1, y=0.1, width=0.2, height=0.3),
                center_point=Point(x=0.2, y=0.25),
                confidence=0.9,
                anonymized=True,
            ),
            FaceDetectionResult(
                face_id="face2",
                bounding_box=BoundingBox(x=0.5, y=0.5, width=0.15, height=0.25),
                center_point=Point(x=0.575, y=0.625),
                confidence=0.7,
                anonymized=True,
            ),
            FaceDetectionResult(
                face_id="face3",
                bounding_box=BoundingBox(x=0.3, y=0.2, width=0.1, height=0.2),
                center_point=Point(x=0.35, y=0.3),
                confidence=0.4,
                anonymized=True,
            ),
        ]

        stats = service.get_face_statistics(faces)

        assert stats["total_faces"] == 3
        assert abs(stats["average_confidence"] - 0.667) < 0.01
        assert stats["confidence_distribution"]["high"] == 1  # >= 0.8
        assert stats["confidence_distribution"]["medium"] == 1  # 0.5-0.8
        assert stats["confidence_distribution"]["low"] == 1  # < 0.5
        assert len(stats["face_sizes"]) == 3
        assert stats["largest_face_area"] == 0.06  # 0.2 * 0.3
        assert stats["smallest_face_area"] == 0.02  # 0.1 * 0.2


class TestImageAnnotationService:
    """Test cases for ImageAnnotationService"""

    @pytest.fixture
    def service(self):
        """Create ImageAnnotationService instance for testing"""
        return ImageAnnotationService()

    @pytest.fixture
    def mock_image_content(self):
        """Create mock image content for testing"""
        img = Image.new("RGB", (300, 200), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.fixture
    def mock_objects(self):
        """Create mock detection objects for testing"""
        return [
            EnhancedDetectionResult(
                object_id="obj1",
                class_name="Person",
                confidence=0.9,
                bounding_box=BoundingBox(x=0.1, y=0.1, width=0.3, height=0.5),
                center_point=Point(x=0.25, y=0.35),
                area_percentage=15.0,
            ),
            EnhancedDetectionResult(
                object_id="obj2",
                class_name="Car",
                confidence=0.8,
                bounding_box=BoundingBox(x=0.5, y=0.6, width=0.4, height=0.3),
                center_point=Point(x=0.7, y=0.75),
                area_percentage=12.0,
            ),
        ]

    @pytest.fixture
    def mock_faces(self):
        """Create mock face detection results for testing"""
        return [
            FaceDetectionResult(
                face_id="face1",
                bounding_box=BoundingBox(x=0.2, y=0.15, width=0.1, height=0.15),
                center_point=Point(x=0.25, y=0.225),
                confidence=0.95,
                anonymized=True,
            )
        ]

    def test_render_annotated_image_success(
        self, service, mock_image_content, mock_objects, mock_faces
    ):
        """Test successful rendering of annotated image with all elements"""
        result_image = service.render_annotated_image(
            image_content=mock_image_content,
            objects=mock_objects,
            faces=mock_faces,
            labels=[{"name": "Tree", "confidence": 0.8}],
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=True,
        )

        # Verify that we get image data back
        assert isinstance(result_image, bytes)
        assert len(result_image) > 0

        # Verify the image can be opened and has correct dimensions
        pil_image = Image.open(io.BytesIO(result_image))
        assert pil_image.size == (300, 200)  # Original image size
        assert pil_image.mode == "RGB"

    def test_render_bounding_boxes_only(
        self, service, mock_image_content, mock_objects
    ):
        """Test rendering only bounding boxes"""
        result_image = service.render_bounding_boxes_only(
            image_content=mock_image_content, objects=mock_objects
        )

        assert isinstance(result_image, bytes)
        assert len(result_image) > 0

        # Verify image properties
        pil_image = Image.open(io.BytesIO(result_image))
        assert pil_image.size == (300, 200)

    def test_render_face_markers_only(self, service, mock_image_content, mock_faces):
        """Test rendering only face markers"""
        result_image = service.render_face_markers_only(
            image_content=mock_image_content, faces=mock_faces
        )

        assert isinstance(result_image, bytes)
        assert len(result_image) > 0

        # Verify image properties
        pil_image = Image.open(io.BytesIO(result_image))
        assert pil_image.size == (300, 200)

    def test_create_annotation_overlay(self, service, mock_objects, mock_faces):
        """Test creation of transparent annotation overlay"""
        image_size = ImageSize(width=400, height=300)

        overlay_image = service.create_annotation_overlay(
            image_size=image_size, objects=mock_objects, faces=mock_faces
        )

        assert isinstance(overlay_image, bytes)
        assert len(overlay_image) > 0

        # Verify overlay properties
        pil_image = Image.open(io.BytesIO(overlay_image))
        assert pil_image.size == (400, 300)
        assert pil_image.mode == "RGBA"  # Should be transparent

    def test_annotation_statistics(self, service, mock_objects, mock_faces):
        """Test annotation statistics calculation"""
        stats = service.get_annotation_statistics(
            objects=mock_objects, faces=mock_faces
        )

        assert stats["total_objects"] == 2
        assert stats["total_faces"] == 1
        assert stats["object_classes"]["Person"] == 1
        assert stats["object_classes"]["Car"] == 1
        assert stats["annotation_density"] == 3  # 2 objects + 1 face

        # Check confidence statistics
        conf_stats = stats["confidence_stats"]
        assert conf_stats["high_confidence_count"] == 2  # Person (0.9) and Face (0.95)
        assert conf_stats["medium_confidence_count"] == 1  # Car (0.8)
        assert conf_stats["low_confidence_count"] == 0

    def test_validate_annotation_request_success(
        self, service, mock_image_content, mock_objects, mock_faces
    ):
        """Test successful annotation request validation"""
        validation = service.validate_annotation_request(
            image_content=mock_image_content, objects=mock_objects, faces=mock_faces
        )

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert validation["image_info"]["width"] == 300
        assert validation["image_info"]["height"] == 200

    def test_validate_annotation_request_invalid_coordinates(
        self, service, mock_image_content
    ):
        """Test validation with invalid coordinates"""
        invalid_objects = [
            EnhancedDetectionResult(
                object_id="invalid_obj",
                class_name="Person",
                confidence=0.9,
                bounding_box=BoundingBox(
                    x=1.5, y=1.5, width=0.3, height=0.5
                ),  # Invalid coordinates
                center_point=Point(x=1.65, y=1.75),
                area_percentage=15.0,
            )
        ]

        validation = service.validate_annotation_request(
            image_content=mock_image_content, objects=invalid_objects
        )

        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert "Invalid bounding box" in validation["errors"][0]

    def test_custom_styling(
        self, service, mock_image_content, mock_objects, mock_faces
    ):
        """Test custom styling options"""
        custom_styles = {
            "face_marker_color": "#FF0000",  # Red instead of yellow
            "box_color": "#00FF00",  # Green instead of white
            "box_thickness": 3,
            "label_color": "#FF00FF",  # Magenta instead of blue
        }

        result_image = service.render_annotated_image(
            image_content=mock_image_content,
            objects=mock_objects,
            faces=mock_faces,
            custom_styles=custom_styles,
        )

        assert isinstance(result_image, bytes)
        assert len(result_image) > 0

        # Verify image can be opened
        pil_image = Image.open(io.BytesIO(result_image))
        assert pil_image.size == (300, 200)

    def test_hex_to_rgb_conversion(self, service):
        """Test hex color to RGB conversion"""
        # Test standard hex colors
        assert service._hex_to_rgb("#FF0000") == (255, 0, 0)  # Red
        assert service._hex_to_rgb("#00FF00") == (0, 255, 0)  # Green
        assert service._hex_to_rgb("#0000FF") == (0, 0, 255)  # Blue
        assert service._hex_to_rgb("#FFFFFF") == (255, 255, 255)  # White
        assert service._hex_to_rgb("#000000") == (0, 0, 0)  # Black

        # Test hex without # prefix
        assert service._hex_to_rgb("FFD700") == (255, 215, 0)  # Gold


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
