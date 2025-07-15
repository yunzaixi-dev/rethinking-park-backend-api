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

logger = logging.getLogger(__name__)

class EnhancedVisionService(VisionService):
    """Enhanced Google Cloud Vision service with advanced detection and annotation capabilities"""
    
    def __init__(self):
        super().__init__()
        self.default_font_size = 16
        self.face_marker_radius = 8
        self.box_thickness = 2
        
    async def detect_objects_enhanced(
        self, 
        image_content: bytes, 
        include_faces: bool = True,
        include_labels: bool = True,
        confidence_threshold: float = 0.5,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Enhanced object detection with precise bounding boxes and confidence scores
        """
        if not self.enabled:
            return {
                "objects": [],
                "faces": [],
                "labels": [],
                "error": "Vision service not enabled",
                "enabled": False
            }
            
        try:
            image = vision.Image(content=image_content)
            results = {"enabled": True, "detection_time": datetime.now().isoformat()}
            
            # Enhanced object detection
            objects = await self._detect_objects_enhanced(image, confidence_threshold, max_results)
            results["objects"] = objects
            
            # Face detection with positions
            if include_faces:
                faces = await self._detect_faces_enhanced(image)
                results["faces"] = faces
            
            # Label detection for context
            if include_labels:
                labels = await self._detect_labels_enhanced(image, confidence_threshold)
                results["labels"] = labels
            
            return results
            
        except GoogleCloudError as e:
            raise Exception(f"Google Cloud Vision API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Enhanced object detection failed: {str(e)}")
    
    async def _detect_objects_enhanced(
        self, 
        image: vision.Image, 
        confidence_threshold: float = 0.5,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Enhanced object detection with detailed bounding box information"""
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
                    vertices.append({"x": vertex.x, "y": vertex.y})
                    x_coords.append(vertex.x)
                    y_coords.append(vertex.y)
                
                # Calculate bounding box properties
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                width = max_x - min_x
                height = max_y - min_y
                center_x = min_x + width / 2
                center_y = min_y + height / 2
                
                objects.append({
                    "object_id": f"obj_{idx}_{uuid.uuid4().hex[:8]}",
                    "class_name": obj.name,
                    "confidence": float(obj.score),
                    "bounding_box": {
                        "normalized_vertices": vertices,
                        "x": float(min_x),
                        "y": float(min_y),
                        "width": float(width),
                        "height": float(height)
                    },
                    "center_point": {
                        "x": float(center_x),
                        "y": float(center_y)
                    },
                    "area_percentage": float(width * height * 100)
                })
                
                if len(objects) >= max_results:
                    break
            
            return objects
            
        except Exception as e:
            logger.error(f"Enhanced object detection failed: {e}")
            return []
    
    async def _detect_faces_enhanced(self, image: vision.Image) -> List[Dict[str, Any]]:
        """Enhanced face detection with position marking"""
        try:
            response = self.client.face_detection(image=image)
            faces = []
            
            for idx, face in enumerate(response.face_annotations):
                # Calculate face bounding box
                vertices = []
                x_coords = []
                y_coords = []
                
                for vertex in face.bounding_poly.vertices:
                    vertices.append({"x": vertex.x, "y": vertex.y})
                    x_coords.append(vertex.x)
                    y_coords.append(vertex.y)
                
                # Calculate center point for marker placement
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                
                faces.append({
                    "face_id": f"face_{idx}_{uuid.uuid4().hex[:8]}",
                    "bounding_box": {
                        "vertices": vertices,
                        "x": min_x,
                        "y": min_y,
                        "width": max_x - min_x,
                        "height": max_y - min_y
                    },
                    "center_point": {
                        "x": center_x,
                        "y": center_y
                    },
                    "confidence": float(face.detection_confidence),
                    "emotions": {
                        "joy": face.joy_likelihood.name,
                        "sorrow": face.sorrow_likelihood.name,
                        "anger": face.anger_likelihood.name,
                        "surprise": face.surprise_likelihood.name
                    }
                })
            
            return faces
            
        except Exception as e:
            logger.error(f"Enhanced face detection failed: {e}")
            return []
    
    async def _detect_labels_enhanced(
        self, 
        image: vision.Image, 
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Enhanced label detection with confidence filtering"""
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

# Global enhanced vision service instance
enhanced_vision_service = EnhancedVisionService()