from google.cloud import vision
from google.cloud.exceptions import GoogleCloudError
from google.auth.exceptions import DefaultCredentialsError
from typing import Dict, Any, List, Optional, Tuple
import io
import base64
import logging
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import uuid

from config import settings
from .vision_service import VisionService
from .face_detection_service import FaceDetectionService
from .error_handling import (
    VisionAPIException,
    ProcessingException,
    retry_vision_api,
    retry_processing,
    handle_vision_api_error,
    handle_processing_error
)
from models.image import (
    EnhancedDetectionResult,
    EnhancedDetectionRequest,
    EnhancedDetectionResponse,
    FaceDetectionResult,
    BoundingBox,
    Point,
    NaturalElementsResult,
    ColorInfo
)

logger = logging.getLogger(__name__)

class EnhancedVisionService(VisionService):
    """Enhanced Google Cloud Vision service with advanced detection and annotation capabilities"""
    
    def __init__(self):
        super().__init__()
        self.default_font_size = 16
        self.face_marker_radius = 8
        self.box_thickness = 2
        self.face_detection_service = FaceDetectionService()
        
    @retry_vision_api(max_attempts=3, base_delay=1.0)
    async def detect_objects_enhanced(
        self, 
        image_content: bytes, 
        image_hash: str,
        include_faces: bool = True,
        include_labels: bool = True,
        confidence_threshold: float = 0.5,
        max_results: int = 50
    ) -> EnhancedDetectionResponse:
        """
        Enhanced object detection with precise bounding boxes and confidence scores
        """
        if not self.enabled:
            return EnhancedDetectionResponse(
                image_hash=image_hash,
                objects=[],
                faces=[],
                labels=[],
                detection_time=datetime.now(),
                success=False,
                enabled=False,
                error_message="Vision service not enabled"
            )
            
        try:
            image = vision.Image(content=image_content)
            
            # Enhanced object detection with retry
            objects = await self._detect_objects_enhanced_with_retry(image, confidence_threshold, max_results)
            
            # Face detection with positions using specialized service
            faces = []
            if include_faces:
                try:
                    face_response = await self.face_detection_service.detect_faces_enhanced(
                        image_content, 
                        include_demographics=False,
                        anonymize_results=True,
                        confidence_threshold=confidence_threshold
                    )
                    faces = face_response.faces
                except Exception as face_error:
                    logger.warning(f"Face detection failed, continuing without faces: {face_error}")
                    # Continue without faces rather than failing completely
            
            # Label detection for context
            labels = []
            if include_labels:
                try:
                    labels = await self._detect_labels_enhanced_with_retry(image, confidence_threshold)
                except Exception as label_error:
                    logger.warning(f"Label detection failed, continuing without labels: {label_error}")
                    # Continue without labels rather than failing completely
            
            return EnhancedDetectionResponse(
                image_hash=image_hash,
                objects=objects,
                faces=faces,
                labels=labels,
                detection_time=datetime.now(),
                success=True,
                enabled=True,
                error_message=None
            )
            
        except (GoogleCloudError, VisionAPIException) as e:
            # Handle Vision API errors with proper error recovery
            error_info = handle_vision_api_error(e, image_hash)
            logger.error(f"Vision API error after retries: {error_info}")
            
            return EnhancedDetectionResponse(
                image_hash=image_hash,
                objects=[],
                faces=[],
                labels=[],
                detection_time=datetime.now(),
                success=False,
                enabled=True,
                error_message=error_info.get("message", str(e))
            )
        except Exception as e:
            # Handle other processing errors
            error_info = handle_processing_error(e, "enhanced_detection", image_hash=image_hash)
            logger.error(f"Enhanced detection error: {error_info}")
            
            return EnhancedDetectionResponse(
                image_hash=image_hash,
                objects=[],
                faces=[],
                labels=[],
                detection_time=datetime.now(),
                success=False,
                enabled=True,
                error_message=error_info.get("message", str(e))
            )
    
    @retry_vision_api(max_attempts=2, base_delay=0.5)
    async def _detect_objects_enhanced_with_retry(
        self, 
        image: vision.Image, 
        confidence_threshold: float = 0.5,
        max_results: int = 50
    ) -> List[EnhancedDetectionResult]:
        """Enhanced object detection with detailed bounding box information and retry logic"""
        try:
            response = self.client.object_localization(image=image)
            objects = []
            
            for idx, obj in enumerate(response.localized_object_annotations):
                if obj.score < confidence_threshold:
                    continue
                    
                # Calculate normalized bounding box coordinates
                vertices = []
                x_coords = []
                y_coords = []
                
                for vertex in obj.bounding_poly.normalized_vertices:
                    vertices.append(Point(x=vertex.x, y=vertex.y))
                    x_coords.append(vertex.x)
                    y_coords.append(vertex.y)
                
                # Calculate bounding box properties
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                width = max_x - min_x
                height = max_y - min_y
                center_x = min_x + width / 2
                center_y = min_y + height / 2
                
                # Create bounding box model
                bounding_box = BoundingBox(
                    x=float(min_x),
                    y=float(min_y),
                    width=float(width),
                    height=float(height),
                    normalized_vertices=vertices
                )
                
                # Create center point model
                center_point = Point(x=float(center_x), y=float(center_y))
                
                # Create enhanced detection result
                detection_result = EnhancedDetectionResult(
                    object_id=f"obj_{idx}_{uuid.uuid4().hex[:8]}",
                    class_name=obj.name,
                    confidence=float(obj.score),
                    bounding_box=bounding_box,
                    center_point=center_point,
                    area_percentage=float(width * height * 100)
                )
                
                objects.append(detection_result)
                
                if len(objects) >= max_results:
                    break
            
            return objects
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Vision API error in object detection: {e}")
            raise VisionAPIException(f"Object detection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Enhanced object detection failed: {e}")
            raise ProcessingException(f"Object detection processing failed: {str(e)}", "object_detection")

    async def _detect_objects_enhanced(
        self, 
        image: vision.Image, 
        confidence_threshold: float = 0.5,
        max_results: int = 50
    ) -> List[EnhancedDetectionResult]:
        """Enhanced object detection with detailed bounding box information (legacy method)"""
        try:
            return await self._detect_objects_enhanced_with_retry(image, confidence_threshold, max_results)
        except Exception as e:
            logger.error(f"Enhanced object detection failed: {e}")
            return []
    

    
    @retry_vision_api(max_attempts=2, base_delay=0.5)
    async def _detect_labels_enhanced_with_retry(
        self, 
        image: vision.Image, 
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Enhanced label detection with confidence filtering and retry logic"""
        try:
            response = self.client.label_detection(image=image)
            labels = []
            
            for label in response.label_annotations:
                if label.score >= confidence_threshold:
                    labels.append({
                        "name": label.description,
                        "confidence": float(label.score),
                        "topicality": float(label.topicality)
                    })
            
            return labels
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Vision API error in label detection: {e}")
            raise VisionAPIException(f"Label detection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Enhanced label detection failed: {e}")
            raise ProcessingException(f"Label detection processing failed: {str(e)}", "label_detection")

    async def _detect_labels_enhanced(
        self, 
        image: vision.Image, 
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Enhanced label detection with confidence filtering (legacy method)"""
        try:
            return await self._detect_labels_enhanced_with_retry(image, confidence_threshold)
        except Exception as e:
            logger.error(f"Enhanced label detection failed: {e}")
            return []
    
    async def analyze_natural_elements(self, image_content: bytes) -> Dict[str, Any]:
        """
        Analyze natural elements in park images using Google Vision labels
        """
        if not self.enabled:
            return {
                "natural_elements": {},
                "error": "Vision service not enabled",
                "enabled": False
            }
            
        try:
            image = vision.Image(content=image_content)
            
            # Get labels for natural element analysis
            labels_response = await self._detect_labels_enhanced(image, confidence_threshold=0.3)
            
            # Categorize natural elements
            natural_elements = self._categorize_natural_elements(labels_response)
            
            # Analyze image colors for vegetation health
            pil_image = Image.open(io.BytesIO(image_content))
            color_analysis = self._analyze_image_colors(pil_image)
            
            return {
                "natural_elements": natural_elements,
                "color_analysis": color_analysis,
                "vegetation_health_score": self._calculate_vegetation_health(
                    natural_elements, color_analysis
                ),
                "analysis_time": datetime.now().isoformat(),
                "enabled": True
            }
            
        except Exception as e:
            logger.error(f"Natural elements analysis failed: {e}")
            return {
                "natural_elements": {},
                "error": str(e),
                "enabled": True
            }
    
    def _categorize_natural_elements(self, labels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize labels into natural element types"""
        categories = {
            "vegetation": [],
            "sky": [],
            "water": [],
            "terrain": [],
            "built_environment": []
        }
        
        # Define category mappings
        vegetation_keywords = ["tree", "plant", "grass", "flower", "leaf", "vegetation", "forest", "garden"]
        sky_keywords = ["sky", "cloud", "atmosphere"]
        water_keywords = ["water", "lake", "river", "pond", "stream"]
        terrain_keywords = ["ground", "soil", "rock", "stone", "path", "trail"]
        built_keywords = ["building", "structure", "bench", "fence", "road", "sidewalk"]
        
        coverage_stats = {
            "vegetation_coverage": 0.0,
            "sky_coverage": 0.0,
            "water_coverage": 0.0,
            "built_environment_coverage": 0.0
        }
        
        for label in labels:
            label_name = label["name"].lower()
            confidence = label["confidence"]
            
            # Categorize based on keywords
            if any(keyword in label_name for keyword in vegetation_keywords):
                categories["vegetation"].append(label)
                coverage_stats["vegetation_coverage"] += confidence
            elif any(keyword in label_name for keyword in sky_keywords):
                categories["sky"].append(label)
                coverage_stats["sky_coverage"] += confidence
            elif any(keyword in label_name for keyword in water_keywords):
                categories["water"].append(label)
                coverage_stats["water_coverage"] += confidence
            elif any(keyword in label_name for keyword in terrain_keywords):
                categories["terrain"].append(label)
            elif any(keyword in label_name for keyword in built_keywords):
                categories["built_environment"].append(label)
                coverage_stats["built_environment_coverage"] += confidence
        
        # Normalize coverage percentages
        total_coverage = sum(coverage_stats.values())
        if total_coverage > 0:
            for key in coverage_stats:
                coverage_stats[key] = min(100.0, (coverage_stats[key] / total_coverage) * 100)
        
        return {
            "categories": categories,
            "coverage_statistics": coverage_stats
        }
    
    def _analyze_image_colors(self, pil_image: Image.Image) -> Dict[str, Any]:
        """Analyze dominant colors in the image for vegetation health assessment"""
        try:
            # Resize image for faster processing
            img_small = pil_image.resize((100, 100))
            img_array = np.array(img_small)
            
            # Calculate color statistics
            mean_colors = np.mean(img_array, axis=(0, 1))
            
            # Calculate green ratio for vegetation health
            if len(mean_colors) >= 3:
                green_ratio = mean_colors[1] / (mean_colors[0] + mean_colors[1] + mean_colors[2])
            else:
                green_ratio = 0.0
            
            return {
                "dominant_colors": {
                    "red": float(mean_colors[0]) if len(mean_colors) > 0 else 0.0,
                    "green": float(mean_colors[1]) if len(mean_colors) > 1 else 0.0,
                    "blue": float(mean_colors[2]) if len(mean_colors) > 2 else 0.0
                },
                "green_ratio": float(green_ratio),
                "brightness": float(np.mean(mean_colors))
            }
            
        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            return {
                "dominant_colors": {"red": 0.0, "green": 0.0, "blue": 0.0},
                "green_ratio": 0.0,
                "brightness": 0.0
            }
    
    def _calculate_vegetation_health(
        self, 
        natural_elements: Dict[str, Any], 
        color_analysis: Dict[str, Any]
    ) -> Optional[float]:
        """Calculate vegetation health score based on coverage and color analysis"""
        try:
            vegetation_coverage = natural_elements.get("coverage_statistics", {}).get("vegetation_coverage", 0.0)
            green_ratio = color_analysis.get("green_ratio", 0.0)
            
            if vegetation_coverage == 0:
                return None
            
            # Simple health score calculation
            # Higher green ratio and vegetation coverage = better health
            health_score = (green_ratio * 0.6 + (vegetation_coverage / 100) * 0.4) * 100
            return min(100.0, max(0.0, health_score))
            
        except Exception as e:
            logger.error(f"Vegetation health calculation failed: {e}")
            return None
    
    def apply_confidence_filtering(
        self, 
        objects: List[EnhancedDetectionResult], 
        faces: List[FaceDetectionResult],
        labels: List[Dict[str, Any]],
        confidence_threshold: float = 0.5
    ) -> Tuple[List[EnhancedDetectionResult], List[FaceDetectionResult], List[Dict[str, Any]]]:
        """
        Apply confidence-based filtering to detection results
        """
        # Filter objects by confidence
        filtered_objects = [obj for obj in objects if obj.confidence >= confidence_threshold]
        
        # Filter faces by confidence
        filtered_faces = [face for face in faces if face.confidence >= confidence_threshold]
        
        # Filter labels by confidence
        filtered_labels = [label for label in labels if label.get("confidence", 0.0) >= confidence_threshold]
        
        return filtered_objects, filtered_faces, filtered_labels
    
    def calculate_detection_quality_metrics(
        self, 
        objects: List[EnhancedDetectionResult], 
        faces: List[FaceDetectionResult]
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics for detection results
        """
        metrics = {
            "total_objects": len(objects),
            "total_faces": len(faces),
            "object_confidence_stats": {},
            "face_confidence_stats": {},
            "detection_quality_score": 0.0
        }
        
        # Calculate object confidence statistics
        if objects:
            object_confidences = [obj.confidence for obj in objects]
            metrics["object_confidence_stats"] = {
                "mean": sum(object_confidences) / len(object_confidences),
                "min": min(object_confidences),
                "max": max(object_confidences),
                "high_confidence_count": len([c for c in object_confidences if c >= 0.8]),
                "medium_confidence_count": len([c for c in object_confidences if 0.5 <= c < 0.8]),
                "low_confidence_count": len([c for c in object_confidences if c < 0.5])
            }
        
        # Calculate face confidence statistics
        if faces:
            face_confidences = [face.confidence for face in faces]
            metrics["face_confidence_stats"] = {
                "mean": sum(face_confidences) / len(face_confidences),
                "min": min(face_confidences),
                "max": max(face_confidences),
                "high_confidence_count": len([c for c in face_confidences if c >= 0.8]),
                "medium_confidence_count": len([c for c in face_confidences if 0.5 <= c < 0.8]),
                "low_confidence_count": len([c for c in face_confidences if c < 0.5])
            }
        
        # Calculate overall detection quality score
        total_detections = len(objects) + len(faces)
        if total_detections > 0:
            all_confidences = [obj.confidence for obj in objects] + [face.confidence for face in faces]
            average_confidence = sum(all_confidences) / len(all_confidences)
            high_confidence_ratio = len([c for c in all_confidences if c >= 0.8]) / total_detections
            
            # Quality score based on average confidence and high confidence ratio
            metrics["detection_quality_score"] = (average_confidence * 0.6 + high_confidence_ratio * 0.4) * 100
        
        return metrics
    
    async def detect_with_position_marking(
        self, 
        image_content: bytes, 
        image_hash: str,
        confidence_threshold: float = 0.5,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Enhanced detection with precise position marking functionality
        Combines object detection and face detection with position coordinates
        """
        try:
            # Perform enhanced detection
            detection_response = await self.detect_objects_enhanced(
                image_content=image_content,
                image_hash=image_hash,
                include_faces=True,
                include_labels=True,
                confidence_threshold=confidence_threshold,
                max_results=max_results
            )
            
            if not detection_response.success:
                return {
                    "success": False,
                    "error": detection_response.error_message,
                    "enabled": detection_response.enabled
                }
            
            # Apply confidence filtering
            filtered_objects, filtered_faces, filtered_labels = self.apply_confidence_filtering(
                detection_response.objects,
                detection_response.faces,
                detection_response.labels,
                confidence_threshold
            )
            
            # Calculate quality metrics
            quality_metrics = self.calculate_detection_quality_metrics(filtered_objects, filtered_faces)
            
            # Prepare position marking data
            position_data = {
                "objects_with_positions": [
                    {
                        "object_id": obj.object_id,
                        "class_name": obj.class_name,
                        "confidence": obj.confidence,
                        "center_point": {"x": obj.center_point.x, "y": obj.center_point.y},
                        "bounding_box": {
                            "x": obj.bounding_box.x,
                            "y": obj.bounding_box.y,
                            "width": obj.bounding_box.width,
                            "height": obj.bounding_box.height
                        }
                    } for obj in filtered_objects
                ],
                "faces_with_positions": [
                    {
                        "face_id": face.face_id,
                        "confidence": face.confidence,
                        "center_point": {"x": face.center_point.x, "y": face.center_point.y},
                        "marker_style": "yellow_dot",
                        "anonymized": face.anonymized
                    } for face in filtered_faces
                ]
            }
            
            return {
                "success": True,
                "image_hash": image_hash,
                "detection_time": detection_response.detection_time.isoformat(),
                "position_data": position_data,
                "quality_metrics": quality_metrics,
                "labels": filtered_labels,
                "enabled": True
            }
            
        except Exception as e:
            logger.error(f"Position marking detection failed: {e}")
            return {
                "success": False,
                "error": f"Position marking failed: {str(e)}",
                "enabled": self.enabled
            }

# Global enhanced vision service instance
enhanced_vision_service = EnhancedVisionService()