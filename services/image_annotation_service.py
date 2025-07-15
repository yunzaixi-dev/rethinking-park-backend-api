from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional, Tuple
import io
import logging
import numpy as np
from datetime import datetime

from models.image import (
    EnhancedDetectionResult,
    FaceDetectionResult,
    BoundingBox,
    Point,
    ImageSize
)

logger = logging.getLogger(__name__)

class ImageAnnotationService:
    """Service for rendering annotations on images including bounding boxes, face markers, and labels"""
    
    def __init__(self):
        # Default styling configuration
        self.default_styles = {
            "face_marker_color": "#FFD700",  # Yellow
            "face_marker_radius": 8,
            "box_color": "#FFFFFF",  # White
            "box_thickness": 2,
            "label_color": "#0066CC",  # Blue
            "label_font_size": 16,
            "connection_line_color": "#0066CC",  # Blue
            "connection_line_width": 1,
            "text_background_color": "#FFFFFF",
            "text_background_alpha": 180
        }
        
    def render_annotated_image(
        self,
        image_content: bytes,
        objects: List[EnhancedDetectionResult] = None,
        faces: List[FaceDetectionResult] = None,
        labels: List[Dict[str, Any]] = None,
        include_face_markers: bool = True,
        include_object_boxes: bool = True,
        include_labels: bool = True,
        custom_styles: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Render complete annotated image with all detection results
        """
        try:
            # Load image
            pil_image = Image.open(io.BytesIO(image_content))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Apply custom styles if provided
            styles = self.default_styles.copy()
            if custom_styles:
                styles.update(custom_styles)
            
            # Create drawing context
            draw = ImageDraw.Draw(pil_image)
            img_width, img_height = pil_image.size
            
            # Render object bounding boxes
            if include_object_boxes and objects:
                self._render_bounding_boxes(draw, objects, img_width, img_height, styles)
            
            # Render face markers
            if include_face_markers and faces:
                self._render_face_markers(draw, faces, img_width, img_height, styles)
            
            # Render labels with connections
            if include_labels and (objects or labels):
                self._render_labels_with_connections(
                    draw, objects or [], labels or [], img_width, img_height, styles
                )
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            pil_image.save(output_buffer, format='PNG', quality=95)
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Image annotation rendering failed: {e}")
            return image_content  # Return original image on error
    
    def _render_bounding_boxes(
        self,
        draw: ImageDraw.Draw,
        objects: List[EnhancedDetectionResult],
        img_width: int,
        img_height: int,
        styles: Dict[str, Any]
    ):
        """Render white bounding boxes around detected objects"""
        box_color = styles.get("box_color", "#FFFFFF")
        box_thickness = styles.get("box_thickness", 2)
        
        for obj in objects:
            bbox = obj.bounding_box
            
            # Convert normalized coordinates to pixel coordinates
            x = bbox.x * img_width if bbox.x <= 1.0 else bbox.x
            y = bbox.y * img_height if bbox.y <= 1.0 else bbox.y
            width = bbox.width * img_width if bbox.width <= 1.0 else bbox.width
            height = bbox.height * img_height if bbox.height <= 1.0 else bbox.height
            
            # Calculate rectangle coordinates
            left = int(x)
            top = int(y)
            right = int(x + width)
            bottom = int(y + height)
            
            # Draw bounding box with specified thickness
            for i in range(box_thickness):
                draw.rectangle(
                    [left - i, top - i, right + i, bottom + i],
                    outline=box_color,
                    fill=None
                )
    
    def _render_face_markers(
        self,
        draw: ImageDraw.Draw,
        faces: List[FaceDetectionResult],
        img_width: int,
        img_height: int,
        styles: Dict[str, Any]
    ):
        """Render yellow dot markers on detected faces"""
        marker_color = styles.get("face_marker_color", "#FFD700")
        marker_radius = styles.get("face_marker_radius", 8)
        
        for face in faces:
            center = face.center_point
            
            # Convert normalized coordinates to pixel coordinates
            center_x = center.x * img_width if center.x <= 1.0 else center.x
            center_y = center.y * img_height if center.y <= 1.0 else center.y
            
            # Draw yellow circle marker
            left = int(center_x - marker_radius)
            top = int(center_y - marker_radius)
            right = int(center_x + marker_radius)
            bottom = int(center_y + marker_radius)
            
            draw.ellipse(
                [left, top, right, bottom],
                fill=marker_color,
                outline=marker_color
            )
    
    def _render_labels_with_connections(
        self,
        draw: ImageDraw.Draw,
        objects: List[EnhancedDetectionResult],
        labels: List[Dict[str, Any]],
        img_width: int,
        img_height: int,
        styles: Dict[str, Any]
    ):
        """Render labels with connection lines to detected objects"""
        label_color = styles.get("label_color", "#0066CC")
        connection_color = styles.get("connection_line_color", "#0066CC")
        connection_width = styles.get("connection_line_width", 1)
        font_size = styles.get("label_font_size", 16)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Define label collection point (top-left area)
        label_start_x = 20
        label_start_y = 20
        label_spacing = font_size + 5
        
        # Render object labels with connections
        current_y = label_start_y
        for idx, obj in enumerate(objects):
            label_text = f"{obj.class_name} ({obj.confidence:.2f})"
            
            # Draw connection line from label to object center
            obj_center_x = obj.center_point.x * img_width if obj.center_point.x <= 1.0 else obj.center_point.x
            obj_center_y = obj.center_point.y * img_height if obj.center_point.y <= 1.0 else obj.center_point.y
            
            # Draw line from label position to object center
            draw.line(
                [(label_start_x, current_y + font_size // 2), (int(obj_center_x), int(obj_center_y))],
                fill=connection_color,
                width=connection_width
            )
            
            # Draw text background for better readability
            if font:
                text_bbox = draw.textbbox((label_start_x, current_y), label_text, font=font)
                text_bg_color = (*self._hex_to_rgb(styles.get("text_background_color", "#FFFFFF")), 
                               styles.get("text_background_alpha", 180))
                draw.rectangle(text_bbox, fill=text_bg_color)
                
                # Draw label text
                draw.text((label_start_x, current_y), label_text, fill=label_color, font=font)
            else:
                # Fallback without font
                draw.text((label_start_x, current_y), label_text, fill=label_color)
            
            current_y += label_spacing
        
        # Add general labels if provided
        if labels:
            current_y += 10  # Add some spacing
            for label in labels[:5]:  # Limit to top 5 labels
                label_text = f"{label.get('name', 'Unknown')} ({label.get('confidence', 0):.2f})"
                
                if font:
                    text_bbox = draw.textbbox((label_start_x, current_y), label_text, font=font)
                    text_bg_color = (*self._hex_to_rgb(styles.get("text_background_color", "#FFFFFF")), 
                                   styles.get("text_background_alpha", 180))
                    draw.rectangle(text_bbox, fill=text_bg_color)
                    draw.text((label_start_x, current_y), label_text, fill=label_color, font=font)
                else:
                    draw.text((label_start_x, current_y), label_text, fill=label_color)
                
                current_y += label_spacing
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def render_bounding_boxes_only(
        self,
        image_content: bytes,
        objects: List[EnhancedDetectionResult],
        custom_styles: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Render only bounding boxes on the image"""
        return self.render_annotated_image(
            image_content=image_content,
            objects=objects,
            faces=None,
            labels=None,
            include_face_markers=False,
            include_object_boxes=True,
            include_labels=False,
            custom_styles=custom_styles
        )
    
    def render_face_markers_only(
        self,
        image_content: bytes,
        faces: List[FaceDetectionResult],
        custom_styles: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Render only face markers on the image"""
        return self.render_annotated_image(
            image_content=image_content,
            objects=None,
            faces=faces,
            labels=None,
            include_face_markers=True,
            include_object_boxes=False,
            include_labels=False,
            custom_styles=custom_styles
        )
    
    def create_annotation_overlay(
        self,
        image_size: ImageSize,
        objects: List[EnhancedDetectionResult] = None,
        faces: List[FaceDetectionResult] = None,
        custom_styles: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Create a transparent overlay with only annotations (no background image)"""
        try:
            # Create transparent image
            overlay = Image.new('RGBA', (image_size.width, image_size.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Apply custom styles
            styles = self.default_styles.copy()
            if custom_styles:
                styles.update(custom_styles)
            
            # Render annotations on transparent overlay
            if objects:
                self._render_bounding_boxes(draw, objects, image_size.width, image_size.height, styles)
            
            if faces:
                self._render_face_markers(draw, faces, image_size.width, image_size.height, styles)
            
            # Convert to bytes
            output_buffer = io.BytesIO()
            overlay.save(output_buffer, format='PNG')
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Annotation overlay creation failed: {e}")
            # Return empty transparent image
            empty_overlay = Image.new('RGBA', (image_size.width, image_size.height), (0, 0, 0, 0))
            output_buffer = io.BytesIO()
            empty_overlay.save(output_buffer, format='PNG')
            return output_buffer.getvalue()
    
    def get_annotation_statistics(
        self,
        objects: List[EnhancedDetectionResult] = None,
        faces: List[FaceDetectionResult] = None
    ) -> Dict[str, Any]:
        """Get statistics about annotations to be rendered"""
        stats = {
            "total_objects": len(objects) if objects else 0,
            "total_faces": len(faces) if faces else 0,
            "object_classes": {},
            "confidence_stats": {},
            "annotation_density": 0.0
        }
        
        # Object class distribution
        if objects:
            for obj in objects:
                class_name = obj.class_name
                if class_name not in stats["object_classes"]:
                    stats["object_classes"][class_name] = 0
                stats["object_classes"][class_name] += 1
            
            # Confidence statistics
            confidences = [obj.confidence for obj in objects]
            if faces:
                confidences.extend([face.confidence for face in faces])
            
            if confidences:
                stats["confidence_stats"] = {
                    "mean": sum(confidences) / len(confidences),
                    "min": min(confidences),
                    "max": max(confidences),
                    "high_confidence_count": len([c for c in confidences if c >= 0.8]),
                    "medium_confidence_count": len([c for c in confidences if 0.5 <= c < 0.8]),
                    "low_confidence_count": len([c for c in confidences if c < 0.5])
                }
        
        # Calculate annotation density (annotations per 1000 pixels)
        total_annotations = stats["total_objects"] + stats["total_faces"]
        stats["annotation_density"] = total_annotations
        
        return stats
    
    def validate_annotation_request(
        self,
        image_content: bytes,
        objects: List[EnhancedDetectionResult] = None,
        faces: List[FaceDetectionResult] = None
    ) -> Dict[str, Any]:
        """Validate annotation request and return validation results"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "image_info": {}
        }
        
        try:
            # Validate image
            pil_image = Image.open(io.BytesIO(image_content))
            validation_result["image_info"] = {
                "width": pil_image.width,
                "height": pil_image.height,
                "mode": pil_image.mode,
                "format": pil_image.format
            }
            
            # Check image size limits
            if pil_image.width > 4000 or pil_image.height > 4000:
                validation_result["warnings"].append("Large image size may affect rendering performance")
            
            # Validate object coordinates
            if objects:
                for obj in objects:
                    bbox = obj.bounding_box
                    if not (0 <= bbox.x <= 1 and 0 <= bbox.y <= 1 and 
                           0 <= bbox.width <= 1 and 0 <= bbox.height <= 1):
                        if not (bbox.x >= 0 and bbox.y >= 0 and 
                               bbox.x + bbox.width <= pil_image.width and 
                               bbox.y + bbox.height <= pil_image.height):
                            validation_result["errors"].append(f"Invalid bounding box for object {obj.object_id}")
            
            # Validate face coordinates
            if faces:
                for face in faces:
                    center = face.center_point
                    if not (0 <= center.x <= 1 and 0 <= center.y <= 1):
                        if not (0 <= center.x <= pil_image.width and 0 <= center.y <= pil_image.height):
                            validation_result["errors"].append(f"Invalid center point for face {face.face_id}")
            
            # Check annotation density
            total_annotations = (len(objects) if objects else 0) + (len(faces) if faces else 0)
            if total_annotations > 100:
                validation_result["warnings"].append("High annotation density may affect readability")
            
            if validation_result["errors"]:
                validation_result["valid"] = False
                
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Image validation failed: {str(e)}")
        
        return validation_result

# Global image annotation service instance
image_annotation_service = ImageAnnotationService()