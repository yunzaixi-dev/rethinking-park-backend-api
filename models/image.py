from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class ImageUploadResponse(BaseModel):
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
    similar_images: Optional[List[str]] = Field(default=None, description="相似图像列表")

class ImageInfo(BaseModel):
    """图像信息模型"""
    image_id: str
    image_hash: str = Field(..., description="图像MD5哈希值")
    perceptual_hash: Optional[str] = Field(default=None, description="感知哈希值")
    filename: str
    file_size: int
    content_type: str
    gcs_url: str
    upload_time: datetime
    processed: bool = Field(default=False, description="是否已处理")
    analysis_results: Optional[Dict[str, Any]] = Field(default=None, description="分析结果")

class ImageAnalysisRequest(BaseModel):
    """图像分析请求模型"""
    image_hash: str = Field(..., description="图像哈希值（用于缓存和查找）")
    analysis_type: str = Field(..., description="分析类型：labels, objects, text, faces, landmarks等")
    options: Optional[Dict[str, Any]] = Field(default=None, description="分析选项")
    force_refresh: bool = Field(default=False, description="是否强制刷新缓存")

class ImageAnalysisResponse(BaseModel):
    """图像分析响应模型"""
    image_hash: str
    analysis_type: str
    results: Dict[str, Any] = Field(..., description="分析结果")
    processed_time: datetime
    success: bool = Field(default=True, description="分析是否成功")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    error_message: Optional[str] = Field(default=None, description="错误信息")

class HashAnalysisRequest(BaseModel):
    """基于哈希的分析请求（旧版兼容）"""
    image_id: str = Field(..., description="图像ID")
    analysis_type: str = Field(..., description="分析类型")
    options: Optional[Dict[str, Any]] = Field(default=None, description="分析选项")

class DuplicateCheckResponse(BaseModel):
    """重复检测响应模型"""
    image_hash: str
    is_duplicate: bool
    exact_matches: List[str] = Field(default=[], description="完全相同的图像哈希列表")
    similar_images: List[Dict[str, Any]] = Field(default=[], description="相似图像信息")

class Point(BaseModel):
    """坐标点模型"""
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")

class BoundingBox(BaseModel):
    """边界框模型"""
    x: float = Field(..., description="左上角X坐标（归一化）")
    y: float = Field(..., description="左上角Y坐标（归一化）")
    width: float = Field(..., description="宽度（归一化）")
    height: float = Field(..., description="高度（归一化）")
    normalized_vertices: Optional[List[Point]] = Field(default=None, description="归一化顶点坐标")

class ImageSize(BaseModel):
    """图像尺寸模型"""
    width: int = Field(..., description="图像宽度")
    height: int = Field(..., description="图像高度")

class EnhancedDetectionResult(BaseModel):
    """增强检测结果模型"""
    object_id: str = Field(..., description="对象唯一标识符")
    class_name: str = Field(..., description="对象类别名称")
    confidence: float = Field(..., description="置信度分数（0-1）", ge=0.0, le=1.0)
    bounding_box: BoundingBox = Field(..., description="边界框信息")
    center_point: Point = Field(..., description="中心点坐标")
    area_percentage: float = Field(..., description="占图像面积百分比", ge=0.0, le=100.0)

class FaceLandmark(BaseModel):
    """人脸关键点模型"""
    type: str = Field(..., description="关键点类型")
    position: Point = Field(..., description="关键点位置")

class FaceDetectionResult(BaseModel):
    """人脸检测结果模型"""
    face_id: str = Field(..., description="人脸唯一标识符")
    bounding_box: BoundingBox = Field(..., description="人脸边界框")
    center_point: Point = Field(..., description="人脸中心点（用于标记）")
    confidence: float = Field(..., description="检测置信度", ge=0.0, le=1.0)
    landmarks: Optional[List[FaceLandmark]] = Field(default=None, description="人脸关键点")
    emotions: Optional[Dict[str, str]] = Field(default=None, description="情感分析结果")
    anonymized: bool = Field(default=False, description="是否已匿名化")

class ColorInfo(BaseModel):
    """颜色信息模型"""
    red: float = Field(..., description="红色分量", ge=0.0, le=255.0)
    green: float = Field(..., description="绿色分量", ge=0.0, le=255.0)
    blue: float = Field(..., description="蓝色分量", ge=0.0, le=255.0)
    hex_code: Optional[str] = Field(default=None, description="十六进制颜色代码")

class NaturalElementsResult(BaseModel):
    """自然元素分析结果模型"""
    vegetation_coverage: float = Field(..., description="植被覆盖率百分比", ge=0.0, le=100.0)
    sky_coverage: float = Field(..., description="天空覆盖率百分比", ge=0.0, le=100.0)
    water_coverage: float = Field(..., description="水体覆盖率百分比", ge=0.0, le=100.0)
    built_environment_coverage: float = Field(..., description="建筑环境覆盖率百分比", ge=0.0, le=100.0)
    vegetation_health_score: Optional[float] = Field(default=None, description="植被健康度评分", ge=0.0, le=100.0)
    dominant_colors: List[ColorInfo] = Field(default=[], description="主要颜色信息")
    seasonal_indicators: List[str] = Field(default=[], description="季节指示器")

class EnhancedDetectionRequest(BaseModel):
    """增强检测请求模型"""
    image_hash: str = Field(..., description="图像哈希值")
    include_faces: bool = Field(default=True, description="是否包含人脸检测")
    include_labels: bool = Field(default=True, description="是否包含标签检测")
    confidence_threshold: float = Field(default=0.5, description="置信度阈值", ge=0.0, le=1.0)
    max_results: int = Field(default=50, description="最大结果数量", ge=1, le=100)

class EnhancedDetectionResponse(BaseModel):
    """增强检测响应模型"""
    image_hash: str = Field(..., description="图像哈希值")
    objects: List[EnhancedDetectionResult] = Field(default=[], description="检测到的对象")
    faces: List[FaceDetectionResult] = Field(default=[], description="检测到的人脸")
    labels: List[Dict[str, Any]] = Field(default=[], description="图像标签")
    detection_time: datetime = Field(..., description="检测时间")
    success: bool = Field(default=True, description="检测是否成功")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    enabled: bool = Field(default=True, description="Vision服务是否启用")

class FaceDetectionRequest(BaseModel):
    """人脸检测请求模型"""
    image_hash: str = Field(..., description="图像哈希值")
    include_demographics: bool = Field(default=False, description="是否包含人口统计信息")
    anonymize_results: bool = Field(default=True, description="是否匿名化结果")
    confidence_threshold: float = Field(default=0.5, description="置信度阈值", ge=0.0, le=1.0)

class FaceDetectionResponse(BaseModel):
    """人脸检测响应模型"""
    image_hash: str = Field(..., description="图像哈希值")
    faces: List[FaceDetectionResult] = Field(default=[], description="检测到的人脸")
    total_faces: int = Field(..., description="检测到的人脸总数")
    detection_time: datetime = Field(..., description="检测时间")
    success: bool = Field(default=True, description="检测是否成功")
    anonymized: bool = Field(default=True, description="结果是否已匿名化")
    error_message: Optional[str] = Field(default=None, description="错误信息")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情") 