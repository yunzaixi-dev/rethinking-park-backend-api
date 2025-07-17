"""
Image-related models.

This module contains all models related to image handling,
including image metadata, upload responses, and geometric primitives.
Enhanced with comprehensive validation, documentation, and serialization.
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from .base import BaseModel, BaseRequest, BaseResponse, DomainModel, TimestampMixin
from .validators import (
    ModelValidator,
    validate_content_type,
    validate_filename,
    validate_gcs_url,
    validate_hex_color,
    validate_image_hash,
    validate_normalized_coordinate,
    validate_positive_integer,
)


class Point(BaseModel):
    """坐标点模型"""

    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")

    def distance_to(self, other: "Point") -> float:
        """Calculate distance to another point."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class BoundingBox(BaseModel):
    """边界框模型"""

    x: float = Field(..., description="左上角X坐标（归一化）", ge=0.0, le=1.0)
    y: float = Field(..., description="左上角Y坐标（归一化）", ge=0.0, le=1.0)
    width: float = Field(..., description="宽度（归一化）", ge=0.0, le=1.0)
    height: float = Field(..., description="高度（归一化）", ge=0.0, le=1.0)
    normalized_vertices: Optional[List[Point]] = Field(
        default=None, description="归一化顶点坐标"
    )

    @property
    def center(self) -> Point:
        """Get the center point of the bounding box."""
        return Point(x=self.x + self.width / 2, y=self.y + self.height / 2)

    @property
    def area(self) -> float:
        """Get the area of the bounding box."""
        return self.width * self.height

    def contains_point(self, point: Point) -> bool:
        """Check if a point is inside this bounding box."""
        return (
            self.x <= point.x <= self.x + self.width
            and self.y <= point.y <= self.y + self.height
        )

    def intersects(self, other: "BoundingBox") -> bool:
        """Check if this bounding box intersects with another."""
        return not (
            self.x + self.width < other.x
            or other.x + other.width < self.x
            or self.y + self.height < other.y
            or other.y + other.height < self.y
        )


class ImageSize(BaseModel):
    """图像尺寸模型"""

    width: int = Field(..., description="图像宽度", gt=0)
    height: int = Field(..., description="图像高度", gt=0)

    @property
    def aspect_ratio(self) -> float:
        """Get the aspect ratio (width/height)."""
        return self.width / self.height

    @property
    def total_pixels(self) -> int:
        """Get the total number of pixels."""
        return self.width * self.height

    def is_landscape(self) -> bool:
        """Check if the image is in landscape orientation."""
        return self.width > self.height

    def is_portrait(self) -> bool:
        """Check if the image is in portrait orientation."""
        return self.height > self.width

    def is_square(self) -> bool:
        """Check if the image is square."""
        return self.width == self.height


class ImageModel(DomainModel):
    """
    Base class for all image-related domain models.

    Provides common functionality for image models including
    business rule validation and display name generation.
    Enhanced with comprehensive field validation.
    """

    image_hash: str = Field(..., description="图像MD5哈希值")
    filename: str = Field(..., description="原始文件名")

    @field_validator("image_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate image hash format."""
        return validate_image_hash(v)

    @field_validator("filename")
    @classmethod
    def validate_filename_field(cls, v: str) -> str:
        """Validate filename format."""
        return validate_filename(v)

    def validate_business_rules(self) -> bool:
        """Validate business rules for image models."""
        # Basic validation: hash and filename must be present
        return bool(self.image_hash and self.filename)

    def get_display_name(self) -> str:
        """Get display name for the image."""
        return f"{self.filename} ({self.image_hash[:8]}...)"


class ImageInfo(ImageModel):
    """
    图像信息模型

    Enhanced with comprehensive validation for all fields
    and business rule validation for image processing workflow.
    """

    perceptual_hash: Optional[str] = Field(default=None, description="感知哈希值")
    file_size: int = Field(..., description="文件大小（字节）", gt=0)
    content_type: str = Field(..., description="文件MIME类型")
    gcs_url: str = Field(..., description="Google Cloud Storage URL")
    processed: bool = Field(default=False, description="是否已处理")
    analysis_results: Optional[Dict[str, Any]] = Field(
        default=None, description="分析结果"
    )
    image_size: Optional[ImageSize] = Field(default=None, description="图像尺寸信息")

    @field_validator("content_type")
    @classmethod
    def validate_content_type_field(cls, v: str) -> str:
        """Validate content type format."""
        return validate_content_type(v)

    @field_validator("gcs_url")
    @classmethod
    def validate_gcs_url_field(cls, v: str) -> str:
        """Validate GCS URL format."""
        return validate_gcs_url(v)

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size."""
        return validate_positive_integer(v)

    @model_validator(mode="after")
    def validate_image_info_consistency(self) -> "ImageInfo":
        """Validate consistency between fields."""
        # If processed is True, analysis_results should exist
        if self.processed and not self.analysis_results:
            raise ValueError("Processed images must have analysis results")

        # If image_size exists, validate dimensions
        if self.image_size:
            if not ModelValidator.validate_image_dimensions(
                self.image_size.width, self.image_size.height
            ):
                raise ValueError("Invalid image dimensions")

        return self

    def validate_business_rules(self) -> bool:
        """Validate business rules for image info."""
        base_valid = super().validate_business_rules()
        size_valid = self.file_size > 0
        url_valid = bool(self.gcs_url)
        content_type_valid = self.content_type.startswith("image/")

        return base_valid and size_valid and url_valid and content_type_valid

    def is_processed(self) -> bool:
        """Check if the image has been processed."""
        return self.processed and self.analysis_results is not None

    def get_analysis_result(self, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Get specific analysis result by type."""
        if not self.analysis_results:
            return None
        return self.analysis_results.get(analysis_type)

    def get_processing_status(self) -> str:
        """Get detailed processing status."""
        if not self.processed:
            return "unprocessed"
        elif self.analysis_results:
            return "fully_processed"
        else:
            return "partially_processed"


# Request Models
class ImageUploadRequest(BaseRequest):
    """图像上传请求模型"""

    filename: str = Field(..., description="文件名")
    content_type: str = Field(..., description="文件MIME类型")
    file_size: int = Field(..., description="文件大小（字节）", gt=0)
    check_duplicates: bool = Field(default=True, description="是否检查重复")

    def validate_request(self) -> bool:
        """Validate image upload request."""
        base_valid = super().validate_request()
        content_type_valid = self.content_type.startswith("image/")
        size_valid = self.file_size > 0
        filename_valid = bool(self.filename.strip())

        return base_valid and content_type_valid and size_valid and filename_valid


class DuplicateCheckRequest(BaseRequest):
    """重复检测请求模型"""

    image_hash: str = Field(..., description="图像哈希值")
    check_perceptual: bool = Field(default=True, description="是否检查感知哈希")
    similarity_threshold: float = Field(
        default=0.95, description="相似度阈值", ge=0.0, le=1.0
    )


# Response Models
class ImageUploadResponse(BaseResponse):
    """图像上传响应模型"""

    image_id: str = Field(..., description="图像的唯一标识符")
    image_hash: str = Field(..., description="图像MD5哈希值")
    filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    content_type: str = Field(..., description="文件MIME类型")
    gcs_url: str = Field(..., description="Google Cloud Storage URL")
    upload_time: datetime = Field(..., description="上传时间")
    status: str = Field(default="uploaded", description="图像状态")
    is_duplicate: bool = Field(default=False, description="是否为重复图像")
    similar_images: Optional[List[str]] = Field(
        default=None, description="相似图像列表"
    )


class DuplicateCheckResponse(BaseResponse):
    """重复检测响应模型"""

    image_hash: str = Field(..., description="图像哈希值")
    is_duplicate: bool = Field(..., description="是否为重复")
    exact_matches: List[str] = Field(default=[], description="完全相同的图像哈希列表")
    similar_images: List[Dict[str, Any]] = Field(default=[], description="相似图像信息")
    similarity_scores: Dict[str, float] = Field(default={}, description="相似度分数")


class ImageInfoResponse(BaseResponse):
    """图像信息响应模型"""

    image_info: Optional[ImageInfo] = Field(default=None, description="图像信息")


class ImageListResponse(BaseResponse):
    """图像列表响应模型"""

    images: List[ImageInfo] = Field(default=[], description="图像列表")
    total_count: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")


# Specialized Models for Image Operations
class ImageMetadata(BaseModel):
    """图像元数据模型"""

    format: str = Field(..., description="图像格式")
    mode: str = Field(..., description="图像模式")
    size: ImageSize = Field(..., description="图像尺寸")
    has_transparency: bool = Field(default=False, description="是否有透明通道")
    color_space: Optional[str] = Field(default=None, description="色彩空间")
    dpi: Optional[tuple[int, int]] = Field(default=None, description="DPI信息")
    exif_data: Optional[Dict[str, Any]] = Field(default=None, description="EXIF数据")


class ImageProcessingOptions(BaseModel):
    """图像处理选项模型"""

    resize: Optional[ImageSize] = Field(default=None, description="调整大小")
    quality: int = Field(default=95, description="质量", ge=1, le=100)
    format: Optional[str] = Field(default=None, description="输出格式")
    optimize: bool = Field(default=True, description="是否优化")
    progressive: bool = Field(default=False, description="是否渐进式")
    strip_metadata: bool = Field(default=False, description="是否移除元数据")


class ImageTransformation(BaseModel):
    """图像变换模型"""

    operation: str = Field(..., description="操作类型")
    parameters: Dict[str, Any] = Field(default={}, description="操作参数")
    order: int = Field(default=0, description="执行顺序")

    def validate_operation(self) -> bool:
        """Validate the transformation operation."""
        valid_operations = [
            "resize",
            "crop",
            "rotate",
            "flip",
            "blur",
            "sharpen",
            "brightness",
            "contrast",
            "saturation",
        ]
        return self.operation in valid_operations
