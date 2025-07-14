from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class ImageUploadResponse(BaseModel):
    """图像上传响应模型"""
    image_id: str = Field(..., description="图像的唯一标识符")
    filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    content_type: str = Field(..., description="文件MIME类型")
    gcs_url: str = Field(..., description="Google Cloud Storage URL")
    upload_time: datetime = Field(..., description="上传时间")
    status: str = Field(default="uploaded", description="图像状态")

class ImageInfo(BaseModel):
    """图像信息模型"""
    image_id: str
    filename: str
    file_size: int
    content_type: str
    gcs_url: str
    upload_time: datetime
    processed: bool = Field(default=False, description="是否已处理")
    analysis_results: Optional[Dict[str, Any]] = Field(default=None, description="分析结果")

class ImageAnalysisRequest(BaseModel):
    """图像分析请求模型"""
    image_id: str = Field(..., description="图像ID")
    analysis_type: str = Field(..., description="分析类型：vision, object_detection, etc.")
    options: Optional[Dict[str, Any]] = Field(default=None, description="分析选项")

class ImageAnalysisResponse(BaseModel):
    """图像分析响应模型"""
    image_id: str
    analysis_type: str
    results: Dict[str, Any] = Field(..., description="分析结果")
    processed_time: datetime
    success: bool = Field(default=True, description="分析是否成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情") 