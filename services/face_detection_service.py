import io
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import vision
from google.cloud.exceptions import GoogleCloudError
from PIL import Image, ImageDraw

from models.image import (
    BoundingBox,
    FaceDetectionRequest,
    FaceDetectionResponse,
    FaceDetectionResult,
    FaceLandmark,
    Point,
)

from .vision_service import VisionService

logger = logging.getLogger(__name__)


class FaceDetectionService(VisionService):
    """Specialized service for face detection with privacy protection and position marking"""

    def __init__(self):
        super().__init__()
        self.face_marker_color = "#FFD700"  # Yellow color for face markers
        self.face_marker_radius = 8
        self.anonymization_enabled = True

    async def detect_faces_enhanced(
        self,
        image_content: bytes,
        include_demographics: bool = False,
        anonymize_results: bool = True,
        confidence_threshold: float = 0.5,
    ) -> FaceDetectionResponse:
        """
        Enhanced face detection with yellow dot markers and anonymization options
        """
        if not self.enabled:
            return FaceDetectionResponse(
                image_hash="",
                faces=[],
                total_faces=0,
                detection_time=datetime.now(),
                success=False,
                anonymized=True,
                error_message="Vision service not enabled",
            )

        try:
            image = vision.Image(content=image_content)

            # Perform face detection
            faces = await self._detect_faces_with_positions(
                image, include_demographics, anonymize_results, confidence_threshold
            )

            return FaceDetectionResponse(
                image_hash="",  # Will be set by calling service
                faces=faces,
                total_faces=len(faces),
                detection_time=datetime.now(),
                success=True,
                anonymized=anonymize_results,
                error_message=None,
            )

        except GoogleCloudError as e:
            logger.error(f"Google Cloud Vision API error in face detection: {e}")
            return FaceDetectionResponse(
                image_hash="",
                faces=[],
                total_faces=0,
                detection_time=datetime.now(),
                success=False,
                anonymized=True,
                error_message=f"Vision API error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return FaceDetectionResponse(
                image_hash="",
                faces=[],
                total_faces=0,
                detection_time=datetime.now(),
                success=False,
                anonymized=True,
                error_message=f"Face detection error: {str(e)}",
            )

    async def _detect_faces_with_positions(
        self,
        image: vision.Image,
        include_demographics: bool = False,
        anonymize_results: bool = True,
        confidence_threshold: float = 0.5,
    ) -> List[FaceDetectionResult]:
        """Detect faces with precise position coordinates for marker placement"""
        try:
            response = self.client.face_detection(image=image)
            faces = []

            for idx, face in enumerate(response.face_annotations):
                if face.detection_confidence < confidence_threshold:
                    continue

                # Calculate face bounding box from vertices
                vertices = []
                x_coords = []
                y_coords = []

                for vertex in face.bounding_poly.vertices:
                    x_coords.append(vertex.x)
                    y_coords.append(vertex.y)

                # Calculate normalized coordinates (assuming image dimensions)
                # Note: Google Vision returns pixel coordinates, we need to normalize
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                width = max_x - min_x
                height = max_y - min_y

                # Calculate center point for yellow dot marker
                center_x = min_x + width / 2
                center_y = min_y + height / 2

                # Create bounding box model
                bounding_box = BoundingBox(
                    x=float(min_x),
                    y=float(min_y),
                    width=float(width),
                    height=float(height),
                )

                # Create center point for marker
                center_point = Point(x=float(center_x), y=float(center_y))

                # Extract face landmarks if available
                landmarks = []
                if hasattr(face, "landmarks") and face.landmarks:
                    for landmark in face.landmarks:
                        landmarks.append(
                            FaceLandmark(
                                type=landmark.type_.name,
                                position=Point(
                                    x=float(landmark.position.x),
                                    y=float(landmark.position.y),
                                ),
                            )
                        )

                # Extract emotions (anonymize if requested)
                emotions = {}
                if not anonymize_results or include_demographics:
                    emotions = {
                        "joy": face.joy_likelihood.name,
                        "sorrow": face.sorrow_likelihood.name,
                        "anger": face.anger_likelihood.name,
                        "surprise": face.surprise_likelihood.name,
                    }

                # Create face detection result
                face_result = FaceDetectionResult(
                    face_id=f"face_{idx}_{uuid.uuid4().hex[:8]}",
                    bounding_box=bounding_box,
                    center_point=center_point,
                    confidence=float(face.detection_confidence),
                    landmarks=landmarks if landmarks else None,
                    emotions=emotions if emotions else None,
                    anonymized=anonymize_results,
                )

                faces.append(face_result)

            return faces

        except Exception as e:
            logger.error(f"Face position detection failed: {e}")
            return []

    def create_face_markers_image(
        self,
        image_content: bytes,
        faces: List[FaceDetectionResult],
        marker_color: str = "#FFD700",
        marker_radius: int = 8,
    ) -> bytes:
        """
        Create an image with yellow dot markers on detected faces
        """
        try:
            # Open the original image
            pil_image = Image.open(io.BytesIO(image_content))
            draw = ImageDraw.Draw(pil_image)

            # Get image dimensions for coordinate conversion
            img_width, img_height = pil_image.size

            # Draw yellow dots on face centers
            for face in faces:
                # Convert normalized coordinates to pixel coordinates
                center_x = face.center_point.x
                center_y = face.center_point.y

                # If coordinates are normalized (0-1), convert to pixels
                if center_x <= 1.0 and center_y <= 1.0:
                    pixel_x = center_x * img_width
                    pixel_y = center_y * img_height
                else:
                    pixel_x = center_x
                    pixel_y = center_y

                # Draw yellow circle marker
                left = pixel_x - marker_radius
                top = pixel_y - marker_radius
                right = pixel_x + marker_radius
                bottom = pixel_y + marker_radius

                draw.ellipse(
                    [left, top, right, bottom], fill=marker_color, outline=marker_color
                )

            # Convert back to bytes
            output_buffer = io.BytesIO()
            pil_image.save(output_buffer, format="PNG")
            return output_buffer.getvalue()

        except Exception as e:
            logger.error(f"Face marker creation failed: {e}")
            return image_content  # Return original image on error

    def assign_face_ids(
        self, faces: List[FaceDetectionResult]
    ) -> List[FaceDetectionResult]:
        """
        Assign unique IDs to faces for tracking purposes
        """
        for idx, face in enumerate(faces):
            if not face.face_id or face.face_id.startswith("temp_"):
                face.face_id = f"face_{idx}_{uuid.uuid4().hex[:8]}"

        return faces

    def anonymize_face_data(
        self, faces: List[FaceDetectionResult]
    ) -> List[FaceDetectionResult]:
        """
        Remove or anonymize sensitive face data for privacy protection
        """
        anonymized_faces = []

        for face in faces:
            # Create anonymized copy
            anonymized_face = FaceDetectionResult(
                face_id=face.face_id,
                bounding_box=face.bounding_box,
                center_point=face.center_point,
                confidence=face.confidence,
                landmarks=None,  # Remove landmarks for privacy
                emotions=None,  # Remove emotions for privacy
                anonymized=True,
            )
            anonymized_faces.append(anonymized_face)

        return anonymized_faces

    def get_face_statistics(self, faces: List[FaceDetectionResult]) -> Dict[str, Any]:
        """
        Generate statistics about detected faces
        """
        if not faces:
            return {
                "total_faces": 0,
                "average_confidence": 0.0,
                "confidence_distribution": {},
                "face_sizes": [],
            }

        # Calculate statistics
        total_faces = len(faces)
        confidences = [face.confidence for face in faces]
        average_confidence = sum(confidences) / len(confidences)

        # Confidence distribution
        high_confidence = len([c for c in confidences if c >= 0.8])
        medium_confidence = len([c for c in confidences if 0.5 <= c < 0.8])
        low_confidence = len([c for c in confidences if c < 0.5])

        # Face sizes (area percentages)
        face_sizes = []
        for face in faces:
            area = face.bounding_box.width * face.bounding_box.height
            face_sizes.append(area)

        return {
            "total_faces": total_faces,
            "average_confidence": round(average_confidence, 3),
            "confidence_distribution": {
                "high": high_confidence,
                "medium": medium_confidence,
                "low": low_confidence,
            },
            "face_sizes": face_sizes,
            "largest_face_area": max(face_sizes) if face_sizes else 0.0,
            "smallest_face_area": min(face_sizes) if face_sizes else 0.0,
        }


# Global face detection service instance
face_detection_service = FaceDetectionService()
