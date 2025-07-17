"""
Google Cloud Vision service module.

This module provides Google Cloud Vision API integration based on the base service architecture.
"""

import base64
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import vision
from google.cloud.exceptions import GoogleCloudError

from app.core.exceptions import ServiceNotAvailableError
from app.services.base import AsyncService, ServiceConfig

logger = logging.getLogger(__name__)


class GoogleVisionService(AsyncService):
    """Google Cloud Vision analysis service"""

    def __init__(self, config: ServiceConfig = None):
        if config is None:
            config = ServiceConfig(name="google_vision", enabled=True, timeout=30.0)
        super().__init__(config)

        self.client = None
        self._vision_enabled = False

    async def _initialize(self):
        """Initialize Google Cloud Vision service"""
        try:
            self.log_operation("Initializing Google Cloud Vision client")

            # Try to initialize Google Cloud Vision client
            self.client = vision.ImageAnnotatorClient()
            self._vision_enabled = True

            self.log_operation("Google Cloud Vision client initialized successfully")

        except DefaultCredentialsError:
            self.logger.warning(
                "Google Cloud credentials not found, Vision analysis will be disabled"
            )
            self._vision_enabled = False
            # Don't raise exception - service can still work in disabled mode

        except Exception as e:
            self.log_error("_initialize", e)
            self._vision_enabled = False
            # Don't raise exception - service can still work in disabled mode

    async def _health_check(self):
        """Health check for Google Vision service"""
        if not self._vision_enabled:
            # Service is healthy but disabled
            return

        try:
            # Test with a simple image
            test_image = vision.Image(content=b"")
            # This will fail but we can catch the specific error to verify client works
            self.client.label_detection(image=test_image)
        except Exception as e:
            # Expected to fail with empty image, but client should be working
            if "empty" in str(e).lower() or "invalid" in str(e).lower():
                # This is expected - client is working
                return
            else:
                raise Exception(f"Google Vision client not working: {e}")

    def is_enabled(self) -> bool:
        """Check if Vision service is available"""
        return self._vision_enabled

    async def analyze_image(
        self, image_content: bytes, analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Analyze image content
        analysis_type: comprehensive, objects, text, landmarks, faces, labels, safety
        """
        async with self.ensure_initialized():
            if not self._vision_enabled:
                self.logger.warning(
                    "Vision service not enabled, returning mock results"
                )
                return {
                    "objects": [],
                    "text_detection": {"full_text": "", "individual_texts": []},
                    "landmarks": [],
                    "labels": [],
                    "faces": [],
                    "safe_search": {},
                    "error": "Vision service not enabled - Google Cloud credentials not found",
                    "enabled": False,
                }

            try:
                self.log_operation("analyze_image", analysis_type=analysis_type)

                image = vision.Image(content=image_content)
                results = {"enabled": True}

                if analysis_type == "comprehensive" or analysis_type == "all":
                    # Comprehensive analysis
                    results.update(await self._detect_objects(image))
                    results.update(await self._detect_text(image))
                    results.update(await self._detect_landmarks(image))
                    results.update(await self._detect_labels(image))
                    results.update(await self._detect_faces(image))
                    results.update(await self._analyze_safe_search(image))

                elif analysis_type == "objects":
                    results.update(await self._detect_objects(image))

                elif analysis_type == "text":
                    results.update(await self._detect_text(image))

                elif analysis_type == "landmarks":
                    results.update(await self._detect_landmarks(image))

                elif analysis_type == "labels":
                    results.update(await self._detect_labels(image))

                elif analysis_type == "faces":
                    results.update(await self._detect_faces(image))

                elif analysis_type == "safety":
                    results.update(await self._analyze_safe_search(image))

                results["analysis_time"] = datetime.now().isoformat()
                results["analysis_type"] = analysis_type

                return results

            except GoogleCloudError as e:
                self.log_error("analyze_image", e, analysis_type=analysis_type)
                raise Exception(f"Google Cloud Vision API error: {str(e)}")
            except Exception as e:
                self.log_error("analyze_image", e, analysis_type=analysis_type)
                raise Exception(f"Image analysis failed: {str(e)}")

    async def _detect_objects(self, image: vision.Image) -> Dict[str, Any]:
        """Detect objects in image"""
        try:
            response = self.client.object_localization(image=image)
            objects = []

            for obj in response.localized_object_annotations:
                vertices = []
                for vertex in obj.bounding_poly.normalized_vertices:
                    vertices.append({"x": vertex.x, "y": vertex.y})

                objects.append(
                    {
                        "name": obj.name,
                        "confidence": obj.score,
                        "bounding_box": vertices,
                    }
                )

            return {"objects": objects}

        except Exception as e:
            self.logger.error(f"Object detection failed: {e}")
            return {"objects": []}

    async def _detect_text(self, image: vision.Image) -> Dict[str, Any]:
        """Detect text in image"""
        try:
            response = self.client.text_detection(image=image)
            texts = []

            if response.text_annotations:
                # First result is full text
                full_text = response.text_annotations[0].description

                # Rest are individual words/characters
                for text in response.text_annotations[1:]:
                    vertices = []
                    for vertex in text.bounding_poly.vertices:
                        vertices.append({"x": vertex.x, "y": vertex.y})

                    texts.append({"text": text.description, "bounding_box": vertices})

                return {
                    "text_detection": {
                        "full_text": full_text,
                        "individual_texts": texts,
                    }
                }

            return {"text_detection": {"full_text": "", "individual_texts": []}}

        except Exception as e:
            self.logger.error(f"Text detection failed: {e}")
            return {"text_detection": {"full_text": "", "individual_texts": []}}

    async def _detect_landmarks(self, image: vision.Image) -> Dict[str, Any]:
        """Detect landmarks in image"""
        try:
            response = self.client.landmark_detection(image=image)
            landmarks = []

            for landmark in response.landmark_annotations:
                locations = []
                for location in landmark.locations:
                    locations.append(
                        {
                            "latitude": location.lat_lng.latitude,
                            "longitude": location.lat_lng.longitude,
                        }
                    )

                landmarks.append(
                    {
                        "name": landmark.description,
                        "confidence": landmark.score,
                        "locations": locations,
                    }
                )

            return {"landmarks": landmarks}

        except Exception as e:
            self.logger.error(f"Landmark detection failed: {e}")
            return {"landmarks": []}

    async def _detect_labels(self, image: vision.Image) -> Dict[str, Any]:
        """Detect image labels"""
        try:
            response = self.client.label_detection(image=image)
            labels = []

            for label in response.label_annotations:
                labels.append(
                    {
                        "name": label.description,
                        "confidence": label.score,
                        "topicality": label.topicality,
                    }
                )

            return {"labels": labels}

        except Exception as e:
            self.logger.error(f"Label detection failed: {e}")
            return {"labels": []}

    async def _detect_faces(self, image: vision.Image) -> Dict[str, Any]:
        """Detect faces in image"""
        try:
            response = self.client.face_detection(image=image)
            faces = []

            for face in response.face_annotations:
                vertices = []
                for vertex in face.bounding_poly.vertices:
                    vertices.append({"x": vertex.x, "y": vertex.y})

                faces.append(
                    {
                        "bounding_box": vertices,
                        "detection_confidence": face.detection_confidence,
                        "joy_likelihood": face.joy_likelihood.name,
                        "sorrow_likelihood": face.sorrow_likelihood.name,
                        "anger_likelihood": face.anger_likelihood.name,
                        "surprise_likelihood": face.surprise_likelihood.name,
                    }
                )

            return {"faces": faces}

        except Exception as e:
            self.logger.error(f"Face detection failed: {e}")
            return {"faces": []}

    async def _analyze_safe_search(self, image: vision.Image) -> Dict[str, Any]:
        """Safe search analysis"""
        try:
            response = self.client.safe_search_detection(image=image)
            safe_search = response.safe_search_annotation

            return {
                "safe_search": {
                    "adult": safe_search.adult.name,
                    "spoof": safe_search.spoof.name,
                    "medical": safe_search.medical.name,
                    "violence": safe_search.violence.name,
                    "racy": safe_search.racy.name,
                }
            }

        except Exception as e:
            self.logger.error(f"Safe search analysis failed: {e}")
            return {"safe_search": {}}
