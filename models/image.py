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

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情") 