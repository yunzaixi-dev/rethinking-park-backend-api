"""
Analysis-related models.

This module contains all models related to image analysis,
including detection results, analysis requests/responses, and specialized analysis types.
Enhanced with comprehensive validation, documentation, and business rule enforcement.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from .base import BaseModel, BaseRequest, BaseResponse, DomainModel
from .image import BoundingBox, ImageSize, Point
from .validators import (
    ModelValidator,
    validate_analysis_type,
    validate_batch_operation_type,
    validate_batch_status,
    validate_confidence_score,
    validate_health_status,
    validate_image_hash,
    validate_percentage,
    validate_season,
)


class AnalysisType(str, Enum):
    """分析类型枚举"""

    LABELS = "labels"
    OBJECTS = "objects"
    FACES = "faces"
    TEXT = "text"
    LANDMARKS = "landmarks"
    NATURAL_ELEMENTS = "natural_elements"
    ENHANCED_DETECTION = "enhanced_detection"


class AnalysisStatus(str, Enum):
    """分析状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class AnalysisModel(DomainModel):
    """
    Base class for all analysis-related domain models.

    Provides common functionality for analysis models with enhanced validation.
    """

    image_hash: str = Field(..., description="图像哈希值")
    analysis_type: AnalysisType = Field(..., description="分析类型")
    status: AnalysisStatus = Field(
        default=AnalysisStatus.PENDING, description="分析状态"
    )

    @field_validator("image_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate image hash format."""
        return validate_image_hash(v)

    def validate_business_rules(self) -> bool:
        """Validate business rules for analysis models."""
        return bool(self.image_hash and self.analysis_type)

    def get_display_name(self) -> str:
        """Get display name for the analysis."""
        analysis_type_str = (
            self.analysis_type
            if isinstance(self.analysis_type, str)
            else self.analysis_type.value
        )
        return f"{analysis_type_str} analysis for {self.image_hash[:8]}..."


# Detection Result Models
class DetectionResult(BaseModel):
    """
    基础检测结果模型

    Enhanced with confidence score validation and bounding box consistency checks.
    """

    confidence: float = Field(..., description="置信度分数", ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = Field(default=None, description="边界框")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence score."""
        return validate_confidence_score(v)

    @model_validator(mode="after")
    def validate_detection_consistency(self) -> "DetectionResult":
        """Validate detection result consistency."""
        if self.bounding_box:
            bbox_data = {
                "x": self.bounding_box.x,
                "y": self.bounding_box.y,
                "width": self.bounding_box.width,
                "height": self.bounding_box.height,
            }
            if not ModelValidator.validate_bounding_box_coordinates(bbox_data):
                raise ValueError("Invalid bounding box coordinates")

        return self

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if detection has high confidence."""
        return self.confidence >= threshold


class EnhancedDetectionResult(DetectionResult):
    """增强检测结果模型"""

    object_id: str = Field(..., description="对象唯一标识符")
    class_name: str = Field(..., description="对象类别名称")
    center_point: Point = Field(..., description="中心点坐标")
    area_percentage: float = Field(
        ..., description="占图像面积百分比", ge=0.0, le=100.0
    )

    def get_relative_size(self) -> str:
        """Get relative size description."""
        if self.area_percentage < 5:
            return "small"
        elif self.area_percentage < 20:
            return "medium"
        else:
            return "large"


class FaceLandmark(BaseModel):
    """人脸关键点模型"""

    type: str = Field(..., description="关键点类型")
    position: Point = Field(..., description="关键点位置")
    confidence: Optional[float] = Field(default=None, description="关键点置信度")


class FaceDetectionResult(DetectionResult):
    """人脸检测结果模型"""

    face_id: str = Field(..., description="人脸唯一标识符")
    center_point: Point = Field(..., description="人脸中心点")
    landmarks: Optional[List[FaceLandmark]] = Field(
        default=None, description="人脸关键点"
    )
    emotions: Optional[Dict[str, float]] = Field(
        default=None, description="情感分析结果"
    )
    demographics: Optional[Dict[str, Any]] = Field(
        default=None, description="人口统计信息"
    )
    anonymized: bool = Field(default=False, description="是否已匿名化")

    def get_dominant_emotion(self) -> Optional[str]:
        """Get the dominant emotion."""
        if not self.emotions:
            return None
        return max(self.emotions.items(), key=lambda x: x[1])[0]


# Color and Visual Analysis Models
class ColorInfo(BaseModel):
    """颜色信息模型"""

    red: float = Field(..., description="红色分量", ge=0.0, le=255.0)
    green: float = Field(..., description="绿色分量", ge=0.0, le=255.0)
    blue: float = Field(..., description="蓝色分量", ge=0.0, le=255.0)
    hex_code: Optional[str] = Field(default=None, description="十六进制颜色代码")
    color_name: Optional[str] = Field(default=None, description="颜色名称")
    percentage: Optional[float] = Field(
        default=None, description="颜色占比", ge=0.0, le=100.0
    )

    @property
    def rgb_tuple(self) -> tuple[float, float, float]:
        """Get RGB as tuple."""
        return (self.red, self.green, self.blue)

    def to_hex(self) -> str:
        """Convert to hex color code."""
        if self.hex_code:
            return self.hex_code
        return f"#{int(self.red):02x}{int(self.green):02x}{int(self.blue):02x}"


# Natural Elements Analysis Models
class VegetationHealthMetrics(BaseModel):
    """植被健康度指标模型"""

    overall_score: float = Field(..., description="总体健康度评分", ge=0.0, le=100.0)
    color_health_score: float = Field(
        ..., description="基于颜色的健康度评分", ge=0.0, le=100.0
    )
    coverage_health_score: float = Field(
        ..., description="基于覆盖率的健康度评分", ge=0.0, le=100.0
    )
    label_health_score: float = Field(
        ..., description="基于标签的健康度评分", ge=0.0, le=100.0
    )
    green_ratio: float = Field(..., description="绿色比例", ge=0.0, le=1.0)
    health_status: str = Field(
        ..., description="健康状态", pattern="^(healthy|moderate|poor|unknown)$"
    )
    recommendations: List[str] = Field(default=[], description="健康改善建议")

    def is_healthy(self) -> bool:
        """Check if vegetation is healthy."""
        return self.health_status == "healthy" and self.overall_score >= 70


class SeasonalAnalysis(BaseModel):
    """季节分析模型"""

    detected_seasons: List[str] = Field(default=[], description="检测到的季节")
    confidence_scores: Dict[str, float] = Field(
        default={}, description="各季节的置信度分数"
    )
    primary_season: Optional[str] = Field(default=None, description="主要季节")
    seasonal_features: List[str] = Field(default=[], description="季节特征描述")

    def get_season_confidence(self, season: str) -> float:
        """Get confidence score for a specific season."""
        return self.confidence_scores.get(season, 0.0)


class NaturalElementCategory(BaseModel):
    """自然元素类别模型"""

    category_name: str = Field(..., description="类别名称")
    coverage_percentage: float = Field(
        ..., description="覆盖率百分比", ge=0.0, le=100.0
    )
    confidence_score: float = Field(..., description="检测置信度", ge=0.0, le=1.0)
    detected_labels: List[str] = Field(default=[], description="检测到的相关标签")
    element_count: int = Field(default=0, description="检测到的元素数量")

    def is_dominant_category(self, threshold: float = 25.0) -> bool:
        """Check if this is a dominant category."""
        return self.coverage_percentage >= threshold


class NaturalElementsResult(BaseModel):
    """自然元素分析结果模型"""

    # Coverage statistics
    vegetation_coverage: float = Field(
        ..., description="植被覆盖率百分比", ge=0.0, le=100.0
    )
    sky_coverage: float = Field(..., description="天空覆盖率百分比", ge=0.0, le=100.0)
    water_coverage: float = Field(..., description="水体覆盖率百分比", ge=0.0, le=100.0)
    built_environment_coverage: float = Field(
        ..., description="建筑环境覆盖率百分比", ge=0.0, le=100.0
    )

    # Enhanced analysis
    vegetation_health_metrics: Optional[VegetationHealthMetrics] = Field(
        default=None, description="详细植被健康度指标"
    )
    dominant_colors: List[ColorInfo] = Field(default=[], description="主要颜色信息")
    color_diversity_score: Optional[float] = Field(
        default=None, description="颜色多样性评分", ge=0.0, le=100.0
    )
    seasonal_analysis: Optional[SeasonalAnalysis] = Field(
        default=None, description="详细季节分析"
    )
    element_categories: List[NaturalElementCategory] = Field(
        default=[], description="详细元素类别分析"
    )

    # Analysis metadata
    analysis_depth: str = Field(
        default="basic", description="分析深度", pattern="^(basic|comprehensive)$"
    )
    total_labels_analyzed: int = Field(default=0, description="分析的标签总数")
    overall_assessment: str = Field(default="unknown", description="总体评估")
    recommendations: List[str] = Field(default=[], description="改善建议")

    def get_dominant_element(self) -> str:
        """Get the dominant natural element."""
        coverages = {
            "vegetation": self.vegetation_coverage,
            "sky": self.sky_coverage,
            "water": self.water_coverage,
            "built_environment": self.built_environment_coverage,
        }
        return max(coverages.items(), key=lambda x: x[1])[0]


# Label Analysis Models
class LabelCategoryResult(BaseModel):
    """标签类别分析结果模型"""

    category_name: str = Field(..., description="类别名称")
    matched_labels: List[Dict[str, Any]] = Field(default=[], description="匹配的标签")
    total_confidence: float = Field(..., description="总置信度", ge=0.0)
    average_confidence: float = Field(..., description="平均置信度", ge=0.0, le=1.0)
    coverage_estimate: float = Field(
        ..., description="覆盖率估计百分比", ge=0.0, le=100.0
    )
    label_count: int = Field(..., description="匹配标签数量", ge=0)


class LabelAnalysisResult(BaseModel):
    """基于标签的分析结果模型"""

    all_labels: List[Dict[str, Any]] = Field(default=[], description="所有检测到的标签")
    category_analysis: List[LabelCategoryResult] = Field(
        default=[], description="类别分析结果"
    )
    natural_elements_summary: Dict[str, float] = Field(
        default={}, description="自然元素汇总"
    )
    confidence_distribution: Dict[str, int] = Field(
        default={}, description="置信度分布"
    )
    top_categories: List[str] = Field(default=[], description="主要类别")
    analysis_metadata: Dict[str, Any] = Field(default={}, description="分析元数据")


# Request Models
class ImageAnalysisRequest(BaseRequest):
    """图像分析请求模型"""

    image_hash: str = Field(..., description="图像哈希值")
    analysis_type: AnalysisType = Field(..., description="分析类型")
    options: Optional[Dict[str, Any]] = Field(default=None, description="分析选项")
    force_refresh: bool = Field(default=False, description="是否强制刷新缓存")
    confidence_threshold: float = Field(
        default=0.5, description="置信度阈值", ge=0.0, le=1.0
    )


class EnhancedDetectionRequest(BaseRequest):
    """增强检测请求模型"""

    image_hash: str = Field(..., description="图像哈希值")
    include_faces: bool = Field(default=True, description="是否包含人脸检测")
    include_labels: bool = Field(default=True, description="是否包含标签检测")
    confidence_threshold: float = Field(
        default=0.5, description="置信度阈值", ge=0.0, le=1.0
    )
    max_results: int = Field(default=50, description="最大结果数量", ge=1, le=100)


class NaturalElementsRequest(BaseRequest):
    """自然元素分析请求模型"""

    image_hash: str = Field(..., description="图像哈希值")
    analysis_types: Optional[List[str]] = Field(
        default=["vegetation", "water", "sky", "terrain"], description="分析类型列表"
    )
    analysis_depth: str = Field(
        default="comprehensive",
        description="分析深度",
        pattern="^(basic|comprehensive)$",
    )
    include_health_assessment: bool = Field(
        default=True, description="是否包含健康度评估"
    )
    include_seasonal_analysis: bool = Field(
        default=True, description="是否包含季节分析"
    )
    include_color_analysis: bool = Field(default=True, description="是否包含颜色分析")
    confidence_threshold: float = Field(
        default=0.3, description="标签置信度阈值", ge=0.0, le=1.0
    )


class LabelAnalysisRequest(BaseRequest):
    """基于标签的分析请求模型"""

    image_hash: str = Field(..., description="图像哈希值")
    target_categories: Optional[List[str]] = Field(
        default=["Plant", "Tree", "Sky", "Building", "Water", "Grass", "Flower"],
        description="目标分析类别",
    )
    include_confidence: bool = Field(default=True, description="是否包含置信度信息")
    confidence_threshold: float = Field(
        default=0.3, description="标签置信度阈值", ge=0.0, le=1.0
    )
    max_labels: int = Field(default=50, description="最大标签数量", ge=1, le=100)


# Response Models
class ImageAnalysisResponse(BaseResponse):
    """图像分析响应模型"""

    image_hash: str = Field(..., description="图像哈希值")
    analysis_type: AnalysisType = Field(..., description="分析类型")
    results: Optional[Dict[str, Any]] = Field(default=None, description="分析结果")
    processed_time: datetime = Field(..., description="处理时间")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    processing_time_ms: int = Field(default=0, description="处理时间（毫秒）")


class EnhancedDetectionResponse(BaseResponse):
    """增强检测响应模型"""

    image_hash: str = Field(..., description="图像哈希值")
    objects: List[EnhancedDetectionResult] = Field(
        default=[], description="检测到的对象"
    )
    faces: List[FaceDetectionResult] = Field(default=[], description="检测到的人脸")
    labels: List[Dict[str, Any]] = Field(default=[], description="图像标签")
    detection_time: datetime = Field(..., description="检测时间")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    enabled: bool = Field(default=True, description="Vision服务是否启用")


class NaturalElementsResponse(BaseResponse):
    """自然元素分析响应模型"""

    image_hash: str = Field(..., description="图像哈希值")
    results: Optional[NaturalElementsResult] = Field(
        default=None, description="分析结果"
    )
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    enabled: bool = Field(default=True, description="服务是否启用")


class LabelAnalysisResponse(BaseResponse):
    """基于标签的分析响应模型"""

    image_hash: str = Field(..., description="图像哈希值")
    results: LabelAnalysisResult = Field(..., description="分析结果")
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")


# Batch Processing Models
class BatchOperationRequest(BaseModel):
    """批处理操作请求模型"""

    type: str = Field(
        ...,
        description="操作类型",
        pattern="^(detect_objects|extract_object|analyze_labels|analyze_nature|annotate_image)$",
    )
    image_hash: str = Field(..., description="图像哈希值")
    parameters: Dict[str, Any] = Field(default={}, description="操作参数")
    max_retries: int = Field(default=2, description="最大重试次数", ge=0, le=5)


class BatchOperationResult(BaseModel):
    """批处理操作结果模型"""

    operation_id: str = Field(..., description="操作唯一标识符")
    operation_type: str = Field(..., description="操作类型")
    image_hash: str = Field(..., description="图像哈希值")
    status: str = Field(
        ...,
        description="操作状态",
        pattern="^(pending|running|completed|failed|cancelled)$",
    )
    result: Optional[Dict[str, Any]] = Field(default=None, description="操作结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    processing_time_ms: int = Field(default=0, description="处理时间（毫秒）")
    retry_count: int = Field(default=0, description="重试次数")
