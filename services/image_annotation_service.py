from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List, Optional, Tuple
import io
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class ImageAnnotationService:
    """Service for rendering annotations on images based on detection results"""
    
    def __init__(self):
        self.default_colors = {
            "face_marker": "#FFD700",  # Yellow
            "object_box": "#FFFFFF",   # White
            "label_text": "#0066CC",   # Blue
            "connection_line": "#0066CC"  # Blue
        }
        self.default_font_size = 16
        self.face_marker_radius = 8
        self.box_thickness = 2
        
    def render_annotations(
        self,
        image_content: bytes,
        detection_results: Dict[str, Any],
        annotation_options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Render annotations on image based on detection results
        """
        try:
            # Load image
            pil_image = Image.open(io.BytesIO(image_content))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Create drawing context
            draw = ImageDraw.Draw(pil_image)
            
            # Get annotation options
            options = annotation_options or {}
            include_faces = options.get("include_face_markers", True)
            include_objects = options.get("include_object_boxes", True)
            include_labels = options.get("include_labels", True)
            
            # Get image dimensions
            img_width, img_height = pil_image.size
            
            # Render face markers
            if include_faces and "faces" in detection_results:
                self._render_face_markers(
                    draw, detection_results["faces"], 
                    img_width, img_height, options
                )
            
            # Render object bounding boxes
            if include_objects and "objects" in detection_results:
                self._render_object_boxes(
                    draw, detection_results["objects"], 
                    img_width, img_height, options
                )
            
            # Render labels with connections
            if include_labels and "objects" in detection_results:
                self._render_connected_labels(
                    draw, detection_results["objects"], 
                    img_width, img_height, options
                )
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            output_format = options.get("output_format", "PNG").upper()
            quality = options.get("quality", 95)
            
            if output_format == "JPEG":
                pil_image.save(output_buffer, format="JPEG", quality=quality)
            else:
                pil_image.save(output_buffer, format="PNG")
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Image annotation failed: {e}")
            raise Exception(f"Failed to render annotations: {str(e)}")
    
    def _render_face_markers(
        self,
        draw: ImageDraw.Draw,
        faces: List[Dict[str, Any]],
        img_width: int,
        img_height: int,
        options: Dict[str, Any]
    ):
        """Render yellow dot markers for detected faces"""
        try:
            marker_color = options.get("face_marker_color", self.default_colors["face_marker"])
            marker_radius = options.get("face_marker_radius", self.face_marker_radius)
            
            for face in faces:
                center_point = face.get("center_point", {})
                
                # Convert normalized coordinates to pixel coordinates
                if "x" in center_point and "y" in center_point:
                    # Check if coordinates are normalized (0-1) or absolute
                    x = center_point["x"]
                    y = center_point["y"]
                    
                    if x <= 1.0 and y <= 1.0:
                        # Normalized coordinates
                        pixel_x = int(x * img_width)
                        pixel_y = int(y * img_height)
                    else:
                        # Absolute coordinates
                        pixel_x = int(x)
                        pixel_y = int(y)
                    
                    # Draw filled circle
                    draw.ellipse(
                        [
                            pixel_x - marker_radius,
                            pixel_y - marker_radius,
                            pixel_x + marker_radius,
                            pixel_y + marker_radius
                        ],
                        fill=marker_color,
                        outline=marker_color
                    )
                    
        except Exception as e:
            logger.error(f"Face marker rendering failed: {e}")
    
    def _render_object_boxes(
        self,
        draw: ImageDraw.Draw,
        objects: List[Dict[str, Any]],
        img_width: int,
        img_height: int,
        options: Dict[str, Any]
    ):
        """Render white bounding boxes for detected objects"""
        try:
            box_color = options.get("box_color", self.default_colors["object_box"])
            box_thickness = options.get("box_thickness", self.box_thickness)
            
            for obj in objects:
                bbox = obj.get("bounding_box", {})
                
                if "x" in bbox and "y" in bbox and "width" in bbox and "height" in bbox:
                    # Normalized coordinates
                    x = bbox["x"]
                    y = bbox["y"]
                    width = bbox["width"]
                    height = bbox["height"]
                    
                    # Convert to pixel coordinates
                    pixel_x1 = int(x * img_width)
                    pixel_y1 = int(y * img_height)
                    pixel_x2 = int((x + width) * img_width)
                    pixel_y2 = int((y + height) * img_height)
                    
                    # Draw rectangle outline
                    for i in range(box_thickness):
                        draw.rectangle(
                            [
                                pixel_x1 - i,
                                pixel_y1 - i,
                                pixel_x2 + i,
                                pixel_y2 + i
                            ],
                            outline=box_color,
                            fill=None
                        )
                        
        except Exception as e:
            logger.error(f"Object box rendering failed: {e}")
    
    def _render_connected_labels(
        self,
        draw: ImageDraw.Draw,
        objects: List[Dict[str, Any]],
        img_width: int,
        img_height: int,
        options: Dict[str, Any]
    ):
        """Render connected labels for detected objects"""
        try:
            label_color = options.get("label_color", self.default_colors["label_text"])
            connection_color = options.get("connection_color", self.default_colors["connection_line"])
            font_size = options.get("font_size", self.default_font_size)
            
            # Try to load a font, fall back to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
            
            # Calculate label positions (left side, stacked vertically)
            label_start_x = 20
            label_start_y = 20
            label_spacing = font_size + 5
            
            for idx, obj in enumerate(objects):
                class_name = obj.get("class_name", "Unknown")
                confidence = obj.get("confidence", 0.0)
                bbox = obj.get("bounding_box", {})
                
                # Create label text
                label_text = f"{class_name} ({confidence:.2f})"
                
                # Calculate label position
                label_y = label_start_y + (idx * label_spacing)
                
                # Draw label text
                if font:
                    draw.text(
                        (label_start_x, label_y),
                        label_text,
                        fill=label_color,
                        font=font
                    )
                else:
                    draw.text(
                        (label_start_x, label_y),
                        label_text,
                        fill=label_color
                    )
                
                # Draw connection line to object
                if "x" in bbox and "y" in bbox and "width" in bbox and "height" in bbox:
                    # Calculate object center
                    obj_center_x = int((bbox["x"] + bbox["width"] / 2) * img_width)
                    obj_center_y = int((bbox["y"] + bbox["height"] / 2) * img_height)
                    
                    # Calculate label end point
                    if font:
                        text_bbox = draw.textbbox((0, 0), label_text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                    else:
                        text_width = len(label_text) * 8  # Rough estimate
                    
                    label_end_x = label_start_x + text_width
                    label_center_y = label_y + font_size // 2
                    
                    # Draw connection line
                    draw.line(
                        [
                            (label_end_x, label_center_y),
                            (obj_center_x, obj_center_y)
                        ],
                        fill=connection_color,
                        width=1
                    )
                    
        except Exception as e:
            logger.error(f"Connected labels rendering failed: {e}")
    
    def create_annotated_download_image(
        self,
        image_content: bytes,
        detection_results: Dict[str, Any],
        style_options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Create a downloadable annotated image with custom styling
        """
        try:
            # Default style options for download
            default_options = {
                "include_face_markers": True,
                "include_object_boxes": True,
                "include_labels": True,
                "output_format": "PNG",
                "quality": 95,
                "face_marker_color": "#FFD700",
                "box_color": "#FFFFFF",
                "label_color": "#0066CC",
                "connection_color": "#0066CC",
                "box_thickness": 2,
                "face_marker_radius": 8,
                "font_size": 16
            }
            
            # Merge with provided options
            if style_options:
                default_options.update(style_options)
            
            return self.render_annotations(
                image_content,
                detection_results,
                default_options
            )
            
        except Exception as e:
            logger.error(f"Download image creation failed: {e}")
            raise Exception(f"Failed to create download image: {str(e)}")

# Global image annotation service instance
image_annotation_service = ImageAnnotationService()