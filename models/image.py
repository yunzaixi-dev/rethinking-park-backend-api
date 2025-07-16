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
    color_name: Optional[str] = Field(default=None, description="颜色名称")
    percentage: Optional[float] = Field(default=None, description="颜色占比", ge=0.0, le=100.0)

class VegetationHealthMetrics(BaseModel):
    """植被健康度指标模型"""
    overall_score: float = Field(..., description="总体健康度评分", ge=0.0, le=100.0)
    color_health_score: float = Field(..., description="基于颜色的健康度评分", ge=0.0, le=100.0)
    coverage_health_score: float = Field(..., description="基于覆盖率的健康度评分", ge=0.0, le=100.0)
    label_health_score: float = Field(..., description="基于标签的健康度评分", ge=0.0, le=100.0)
    green_ratio: float = Field(..., description="绿色比例", ge=0.0, le=1.0)
    health_status: str = Field(..., description="健康状态", pattern="^(healthy|moderate|poor|unknown)$")
    recommendations: List[str] = Field(default=[], description="健康改善建议")

class SeasonalAnalysis(BaseModel):
    """季节分析模型"""
    detected_seasons: List[str] = Field(default=[], description="检测到的季节")
    confidence_scores: Dict[str, float] = Field(default={}, description="各季节的置信度分数")
    primary_season: Optional[str] = Field(default=None, description="主要季节")
    seasonal_features: List[str] = Field(default=[], description="季节特征描述")

class NaturalElementCategory(BaseModel):
    """自然元素类别模型"""
    category_name: str = Field(..., description="类别名称")
    coverage_percentage: float = Field(..., description="覆盖率百分比", ge=0.0, le=100.0)
    confidence_score: float = Field(..., description="检测置信度", ge=0.0, le=1.0)
    detected_labels: List[str] = Field(default=[], description="检测到的相关标签")
    element_count: int = Field(default=0, description="检测到的元素数量")

class NaturalElementsResult(BaseModel):
    """自然元素分析结果模型"""
    # Coverage statistics
    vegetation_coverage: float = Field(..., description="植被覆盖率百分比", ge=0.0, le=100.0)
    sky_coverage: float = Field(..., description="天空覆盖率百分比", ge=0.0, le=100.0)
    water_coverage: float = Field(..., description="水体覆盖率百分比", ge=0.0, le=100.0)
    built_environment_coverage: float = Field(..., description="建筑环境覆盖率百分比", ge=0.0, le=100.0)
    
    # Enhanced vegetation health analysis
    vegetation_health_score: Optional[float] = Field(default=None, description="植被健康度评分", ge=0.0, le=100.0)
    vegetation_health_metrics: Optional[VegetationHealthMetrics] = Field(default=None, description="详细植被健康度指标")
    
    # Color analysis
    dominant_colors: List[ColorInfo] = Field(default=[], description="主要颜色信息")
    color_diversity_score: Optional[float] = Field(default=None, description="颜色多样性评分", ge=0.0, le=100.0)
    
    # Seasonal analysis
    seasonal_indicators: List[str] = Field(default=[], description="季节指示器")
    seasonal_analysis: Optional[SeasonalAnalysis] = Field(default=None, description="详细季节分析")
    
    # Detailed category breakdown
    element_categories: List[NaturalElementCategory] = Field(default=[], description="详细元素类别分析")
    
    # Analysis metadata
    analysis_time: datetime = Field(default_factory=datetime.now, description="分析时间")
    analysis_depth: str = Field(default="basic", description="分析深度", pattern="^(basic|comprehensive)$")
    total_labels_analyzed: int = Field(default=0, description="分析的标签总数")
    
    # Summary and recommendations
    overall_assessment: str = Field(default="unknown", description="总体评估")
    recommendations: List[str] = Field(default=[], description="改善建议")

class NaturalElementsRequest(BaseModel):
    """自然元素分析请求模型"""
    image_hash: str = Field(..., description="图像哈希值")
    analysis_depth: str = Field(default="comprehensive", description="分析深度", pattern="^(basic|comprehensive)$")
    include_health_assessment: bool = Field(default=True, description="是否包含健康度评估")
    include_seasonal_analysis: bool = Field(default=True, description="是否包含季节分析")
    include_color_analysis: bool = Field(default=True, description="是否包含颜色分析")
    confidence_threshold: float = Field(default=0.3, description="标签置信度阈值", ge=0.0, le=1.0)

class NaturalElementsResponse(BaseModel):
    """自然元素分析响应模型"""
    image_hash: str = Field(..., description="图像哈希值")
    results: Optional[NaturalElementsResult] = Field(default=None, description="分析结果")
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    success: bool = Field(default=True, description="分析是否成功")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    enabled: bool = Field(default=True, description="服务是否启用")

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

class SimpleExtractionRequest(BaseModel):
    """简单对象抠图请求模型"""
    image_hash: str = Field(..., description="图像哈希值")
    bounding_box: BoundingBox = Field(..., description="要抠图的边界框")
    output_format: str = Field(default="png", description="输出格式", pattern="^(png|webp|jpg)$")
    add_padding: int = Field(default=10, description="添加的边距（像素）", ge=0, le=100)
    background_color: Optional[str] = Field(default=None, description="背景颜色（十六进制）")
    quality: int = Field(default=95, description="输出质量（1-100）", ge=1, le=100)

class SimpleExtractionResult(BaseModel):
    """简单抠图结果模型"""
    extracted_image_url: str = Field(..., description="抠图结果的GCS URL")
    bounding_box: BoundingBox = Field(..., description="使用的边界框")
    original_size: ImageSize = Field(..., description="原始图像尺寸")
    extracted_size: ImageSize = Field(..., description="抠图结果尺寸")
    processing_method: str = Field(default="bounding_box", description="处理方法")
    file_size: int = Field(..., description="抠图文件大小（字节）")
    format: str = Field(..., description="输出格式")

class SimpleExtractionResponse(BaseModel):
    """简单抠图响应模型"""
    image_hash: str = Field(..., description="原始图像哈希值")
    extraction_id: str = Field(..., description="抠图任务唯一标识符")
    result: Optional[SimpleExtractionResult] = Field(default=None, description="抠图结果")
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    success: bool = Field(default=True, description="抠图是否成功")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    error_message: Optional[str] = Field(default=None, description="错误信息")

class LabelAnalysisRequest(BaseModel):
    """基于标签的分析请求模型"""
    image_hash: str = Field(..., description="图像哈希值")
    target_categories: Optional[List[str]] = Field(
        default=["Plant", "Tree", "Sky", "Building", "Water", "Grass", "Flower"], 
        description="目标分析类别"
    )
    include_confidence: bool = Field(default=True, description="是否包含置信度信息")
    confidence_threshold: float = Field(default=0.3, description="标签置信度阈值", ge=0.0, le=1.0)
    max_labels: int = Field(default=50, description="最大标签数量", ge=1, le=100)

class LabelCategoryResult(BaseModel):
    """标签类别分析结果模型"""
    category_name: str = Field(..., description="类别名称")
    matched_labels: List[Dict[str, Any]] = Field(default=[], description="匹配的标签")
    total_confidence: float = Field(..., description="总置信度", ge=0.0)
    average_confidence: float = Field(..., description="平均置信度", ge=0.0, le=1.0)
    coverage_estimate: float = Field(..., description="覆盖率估计百分比", ge=0.0, le=100.0)
    label_count: int = Field(..., description="匹配标签数量", ge=0)

class LabelAnalysisResult(BaseModel):
    """基于标签的分析结果模型"""
    all_labels: List[Dict[str, Any]] = Field(default=[], description="所有检测到的标签")
    category_analysis: List[LabelCategoryResult] = Field(default=[], description="类别分析结果")
    natural_elements_summary: Dict[str, float] = Field(default={}, description="自然元素汇总")
    confidence_distribution: Dict[str, int] = Field(default={}, description="置信度分布")
    top_categories: List[str] = Field(default=[], description="主要类别")
    analysis_metadata: Dict[str, Any] = Field(default={}, description="分析元数据")

class LabelAnalysisResponse(BaseModel):
    """基于标签的分析响应模型"""
    image_hash: str = Field(..., description="图像哈希值")
    results: LabelAnalysisResult = Field(..., description="分析结果")
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    success: bool = Field(default=True, description="分析是否成功")
    from_cache: bool = Field(default=False, description="结果是否来自缓存")
    error_message: Optional[str] = Field(default=None, description="错误信息")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情") 