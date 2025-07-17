"""
Image processing service module.

This module provides image processing capabilities including object extraction,
enhancement, and manipulation based on the base service architecture.
"""

import io
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from app.services.base import AsyncService, ServiceConfig
from models.image import BoundingBox, EnhancedDetectionResult, ImageSize, Point

logger = logging.getLogger(__name__)


class SimpleExtractionResult:
    """Result model for simple object extraction"""

    def __init__(
        self,
        extracted_image_bytes: bytes,
        bounding_box: BoundingBox,
        original_size: ImageSize,
        extracted_size: ImageSize,
        processing_method: str = "bounding_box",
        extraction_id: str = None,
    ):
        self.extracted_image_bytes = extracted_image_bytes
        self.bounding_box = bounding_box
        self.original_size = original_size
        self.extracted_size = extracted_size
        self.processing_method = processing_method
        self.extraction_id = extraction_id or f"extract_{uuid.uuid4().hex[:8]}"


class ImageProcessingService(AsyncService):
    """Service for image processing and object extraction based on bounding boxes"""

    def __init__(self, config: ServiceConfig = None):
        if config is None:
            config = ServiceConfig(name="image_processing", enabled=True, timeout=30.0)
        super().__init__(config)

        self.default_padding = 10
        self.background_threshold = (
            30  # Color difference threshold for background removal
        )
        self.max_extraction_size = (2000, 2000)  # Maximum size for extracted objects

    async def _initialize(self):
        """Initialize image processing service"""
        self.log_operation("Initializing image processing service")
        # No specific initialization needed for image processing
        pass

    async def _health_check(self):
        """Health check for image processing service"""
        # Test basic PIL functionality
        try:
            test_image = Image.new("RGB", (100, 100), color="red")
            buffer = io.BytesIO()
            test_image.save(buffer, format="PNG")
            if len(buffer.getvalue()) == 0:
                raise Exception("PIL image processing not working")
        except Exception as e:
            raise Exception(f"Image processing health check failed: {e}")

    async def extract_by_bounding_box(
        self,
        image_content: bytes,
        bounding_box: BoundingBox,
        padding: int = None,
        output_format: str = "PNG",
        background_removal: bool = False,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> SimpleExtractionResult:
        """
        Extract object from image using bounding box coordinates with optional padding
        """
        async with self.ensure_initialized():
            try:
                self.log_operation(
                    "extract_by_bounding_box",
                    bbox=f"{bounding_box.x},{bounding_box.y},{bounding_box.width},{bounding_box.height}",
                    format=output_format,
                )

                # Load image
                pil_image = Image.open(io.BytesIO(image_content))
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")

                original_size = ImageSize(
                    width=pil_image.width, height=pil_image.height
                )

                # Apply default padding if not specified
                if padding is None:
                    padding = self.default_padding

                # Calculate extraction coordinates
                extraction_coords = self._calculate_extraction_coordinates(
                    bounding_box, original_size, padding
                )

                # Extract the region
                extracted_region = pil_image.crop(extraction_coords)

                # Apply background removal if requested
                if background_removal:
                    extracted_region = self._apply_simple_background_removal(
                        extracted_region, background_color
                    )

                # Resize if too large
                extracted_region = self._resize_if_needed(extracted_region)

                # Convert to bytes
                output_buffer = io.BytesIO()
                if output_format.upper() == "PNG":
                    extracted_region.save(output_buffer, format="PNG", optimize=True)
                elif output_format.upper() in ["JPG", "JPEG"]:
                    # Convert to RGB for JPEG (no transparency)
                    if extracted_region.mode == "RGBA":
                        rgb_image = Image.new(
                            "RGB", extracted_region.size, (255, 255, 255)
                        )
                        rgb_image.paste(
                            extracted_region,
                            mask=(
                                extracted_region.split()[-1]
                                if extracted_region.mode == "RGBA"
                                else None
                            ),
                        )
                        extracted_region = rgb_image
                    extracted_region.save(
                        output_buffer, format="JPEG", quality=95, optimize=True
                    )
                elif output_format.upper() == "WEBP":
                    extracted_region.save(
                        output_buffer, format="WEBP", quality=95, optimize=True
                    )
                else:
                    # Default to PNG
                    extracted_region.save(output_buffer, format="PNG", optimize=True)

                extracted_size = ImageSize(
                    width=extracted_region.width, height=extracted_region.height
                )

                return SimpleExtractionResult(
                    extracted_image_bytes=output_buffer.getvalue(),
                    bounding_box=bounding_box,
                    original_size=original_size,
                    extracted_size=extracted_size,
                    processing_method=(
                        "bounding_box_with_padding" if padding > 0 else "bounding_box"
                    ),
                )

            except Exception as e:
                self.log_error("extract_by_bounding_box", e)
                raise Exception(f"Extraction failed: {str(e)}")

    def _calculate_extraction_coordinates(
        self, bounding_box: BoundingBox, image_size: ImageSize, padding: int
    ) -> Tuple[int, int, int, int]:
        """Calculate pixel coordinates for extraction with padding"""

        # Convert normalized coordinates to pixel coordinates if needed
        if bounding_box.x <= 1.0 and bounding_box.y <= 1.0:
            # Normalized coordinates
            x = int(bounding_box.x * image_size.width)
            y = int(bounding_box.y * image_size.height)
            width = int(bounding_box.width * image_size.width)
            height = int(bounding_box.height * image_size.height)
        else:
            # Pixel coordinates
            x = int(bounding_box.x)
            y = int(bounding_box.y)
            width = int(bounding_box.width)
            height = int(bounding_box.height)

        # Apply padding
        left = max(0, x - padding)
        top = max(0, y - padding)
        right = min(image_size.width, x + width + padding)
        bottom = min(image_size.height, y + height + padding)

        return (left, top, right, bottom)

    def _apply_simple_background_removal(
        self,
        image: Image.Image,
        background_color: Optional[Tuple[int, int, int]] = None,
    ) -> Image.Image:
        """
        Apply simple background removal using color thresholding
        """
        try:
            # Convert to RGBA for transparency support
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Convert to numpy array for processing
            img_array = np.array(image)

            # Determine background color
            if background_color is None:
                # Use corner pixels to estimate background color
                background_color = self._estimate_background_color(img_array)

            # Create mask for background pixels
            background_mask = self._create_background_mask(img_array, background_color)

            # Apply transparency to background pixels
            img_array[:, :, 3] = np.where(background_mask, 0, img_array[:, :, 3])

            # Convert back to PIL Image
            return Image.fromarray(img_array, "RGBA")

        except Exception as e:
            self.logger.error(f"Background removal failed: {e}")
            return image  # Return original image on error

    def _estimate_background_color(self, img_array: np.ndarray) -> Tuple[int, int, int]:
        """Estimate background color from corner pixels"""
        height, width = img_array.shape[:2]
        corner_size = min(20, width // 10, height // 10)

        # Sample corner regions
        corners = [
            img_array[:corner_size, :corner_size],  # Top-left
            img_array[:corner_size, -corner_size:],  # Top-right
            img_array[-corner_size:, :corner_size],  # Bottom-left
            img_array[-corner_size:, -corner_size:],  # Bottom-right
        ]

        # Calculate mean color of all corners
        all_corner_pixels = np.concatenate(
            [corner.reshape(-1, img_array.shape[2]) for corner in corners]
        )
        mean_color = np.mean(all_corner_pixels, axis=0)

        return tuple(mean_color[:3].astype(int))

    def _create_background_mask(
        self, img_array: np.ndarray, background_color: Tuple[int, int, int]
    ) -> np.ndarray:
        """Create mask for background pixels based on color similarity"""
        # Calculate color difference from background color
        color_diff = np.sqrt(
            np.sum((img_array[:, :, :3] - background_color) ** 2, axis=2)
        )

        # Create mask where pixels are similar to background color
        return color_diff < self.background_threshold

    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds maximum size limits"""
        if (
            image.width <= self.max_extraction_size[0]
            and image.height <= self.max_extraction_size[1]
        ):
            return image

        # Calculate scaling factor to fit within limits
        scale_x = self.max_extraction_size[0] / image.width
        scale_y = self.max_extraction_size[1] / image.height
        scale = min(scale_x, scale_y)

        new_width = int(image.width * scale)
        new_height = int(image.height * scale)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    async def batch_extract_objects(
        self,
        image_content: bytes,
        objects: List[EnhancedDetectionResult],
        padding: int = None,
        output_format: str = "PNG",
        background_removal: bool = False,
    ) -> List[SimpleExtractionResult]:
        """
        Extract multiple objects from the same image in batch
        """
        async with self.ensure_initialized():
            results = []

            for obj in objects:
                try:
                    result = await self.extract_by_bounding_box(
                        image_content=image_content,
                        bounding_box=obj.bounding_box,
                        padding=padding,
                        output_format=output_format,
                        background_removal=background_removal,
                    )
                    result.extraction_id = (
                        f"extract_{obj.object_id}_{uuid.uuid4().hex[:8]}"
                    )
                    results.append(result)

                except Exception as e:
                    self.log_error("batch_extract_objects", e, object_id=obj.object_id)
                    continue

            return results

    async def extract_with_custom_region(
        self,
        image_content: bytes,
        x: float,
        y: float,
        width: float,
        height: float,
        padding: int = None,
        output_format: str = "PNG",
        background_removal: bool = False,
    ) -> SimpleExtractionResult:
        """
        Extract custom region specified by coordinates
        """
        custom_bbox = BoundingBox(x=x, y=y, width=width, height=height)

        return await self.extract_by_bounding_box(
            image_content=image_content,
            bounding_box=custom_bbox,
            padding=padding,
            output_format=output_format,
            background_removal=background_removal,
        )

    async def enhance_extracted_object(
        self,
        extracted_result: SimpleExtractionResult,
        enhance_contrast: bool = True,
        enhance_sharpness: bool = True,
        enhance_color: bool = True,
    ) -> SimpleExtractionResult:
        """
        Apply enhancements to extracted object
        """
        async with self.ensure_initialized():
            try:
                self.log_operation(
                    "enhance_extracted_object",
                    extraction_id=extracted_result.extraction_id,
                )

                # Load extracted image
                pil_image = Image.open(
                    io.BytesIO(extracted_result.extracted_image_bytes)
                )

                # Apply enhancements
                if enhance_contrast:
                    enhancer = ImageEnhance.Contrast(pil_image)
                    pil_image = enhancer.enhance(1.2)  # Increase contrast by 20%

                if enhance_sharpness:
                    enhancer = ImageEnhance.Sharpness(pil_image)
                    pil_image = enhancer.enhance(1.1)  # Increase sharpness by 10%

                if enhance_color:
                    enhancer = ImageEnhance.Color(pil_image)
                    pil_image = enhancer.enhance(
                        1.1
                    )  # Increase color saturation by 10%

                # Convert back to bytes
                output_buffer = io.BytesIO()
                if pil_image.mode == "RGBA":
                    pil_image.save(output_buffer, format="PNG", optimize=True)
                else:
                    pil_image.save(
                        output_buffer, format="JPEG", quality=95, optimize=True
                    )

                # Update result
                extracted_result.extracted_image_bytes = output_buffer.getvalue()
                extracted_result.processing_method += "_enhanced"

                return extracted_result

            except Exception as e:
                self.log_error(
                    "enhance_extracted_object",
                    e,
                    extraction_id=extracted_result.extraction_id,
                )
                return extracted_result  # Return original on error

    async def get_extraction_statistics(
        self,
        original_size: ImageSize,
        extracted_size: ImageSize,
        bounding_box: BoundingBox,
    ) -> Dict[str, Any]:
        """
        Calculate statistics about the extraction
        """
        # Calculate area ratios
        original_area = original_size.width * original_size.height
        extracted_area = extracted_size.width * extracted_size.height

        # Calculate bounding box area in pixels
        if bounding_box.x <= 1.0 and bounding_box.y <= 1.0:
            bbox_area = (bounding_box.width * original_size.width) * (
                bounding_box.height * original_size.height
            )
        else:
            bbox_area = bounding_box.width * bounding_box.height

        return {
            "original_dimensions": {
                "width": original_size.width,
                "height": original_size.height,
            },
            "extracted_dimensions": {
                "width": extracted_size.width,
                "height": extracted_size.height,
            },
            "area_ratio": extracted_area / original_area if original_area > 0 else 0,
            "size_reduction_ratio": (
                extracted_area / original_area if original_area > 0 else 0
            ),
            "bounding_box_area": bbox_area,
            "extraction_efficiency": (
                bbox_area / extracted_area if extracted_area > 0 else 0
            ),
        }

    async def validate_extraction_request(
        self, image_content: bytes, bounding_box: BoundingBox, padding: int = None
    ) -> Dict[str, Any]:
        """
        Validate extraction request parameters
        """
        validation_result = {"valid": True, "errors": [], "warnings": []}

        try:
            # Validate image
            pil_image = Image.open(io.BytesIO(image_content))
            image_size = ImageSize(width=pil_image.width, height=pil_image.height)

            # Validate bounding box coordinates
            if bounding_box.x < 0 or bounding_box.y < 0:
                validation_result["errors"].append(
                    "Bounding box coordinates cannot be negative"
                )

            if bounding_box.width <= 0 or bounding_box.height <= 0:
                validation_result["errors"].append(
                    "Bounding box dimensions must be positive"
                )

            # Check if bounding box is within image bounds
            if bounding_box.x <= 1.0 and bounding_box.y <= 1.0:
                # Normalized coordinates
                if (
                    bounding_box.x + bounding_box.width > 1.0
                    or bounding_box.y + bounding_box.height > 1.0
                ):
                    validation_result["errors"].append(
                        "Bounding box extends beyond image boundaries"
                    )
            else:
                # Pixel coordinates
                if (
                    bounding_box.x + bounding_box.width > image_size.width
                    or bounding_box.y + bounding_box.height > image_size.height
                ):
                    validation_result["errors"].append(
                        "Bounding box extends beyond image boundaries"
                    )

            # Validate padding
            if padding is not None and padding < 0:
                validation_result["errors"].append("Padding cannot be negative")

            # Check extraction size
            extraction_coords = self._calculate_extraction_coordinates(
                bounding_box, image_size, padding or 0
            )
            extraction_width = extraction_coords[2] - extraction_coords[0]
            extraction_height = extraction_coords[3] - extraction_coords[1]

            if extraction_width < 10 or extraction_height < 10:
                validation_result["warnings"].append("Extracted region is very small")

            if extraction_width > 2000 or extraction_height > 2000:
                validation_result["warnings"].append(
                    "Extracted region is very large and will be resized"
                )

            if validation_result["errors"]:
                validation_result["valid"] = False

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Image validation failed: {str(e)}")

        return validation_result
