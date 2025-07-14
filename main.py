from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from typing import Optional, List
import io
from datetime import datetime

from config import settings
from models.image import (
    ImageUploadResponse, 
    ImageAnalysisRequest, 
    ImageAnalysisResponse, 
    ErrorResponse, 
    ImageInfo,
    HashAnalysisRequest,
    DuplicateCheckResponse
)
from services.gcs_service import gcs_service
from services.vision_service import vision_service
from services.storage_service import storage_service
from services.cache_service import cache_service
from services.hash_service import hash_service
from services.rate_limiter import limiter, rate_limiter_service

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能公园图像分析API - 支持哈希去重、缓存和速率限制的Google Cloud Vision图像分析服务",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加速率限制支持
if settings.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limiter_service.create_rate_limit_handler())

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    try:
        await gcs_service.initialize()
        print("✅ Google Cloud Storage 初始化成功")
        
        await cache_service.initialize()
        print("✅ 缓存服务初始化完成")
        
    except Exception as e:
        print(f"❌ 服务初始化失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    try:
        await cache_service.close()
        print("✅ 缓存服务已关闭")
    except Exception as e:
        print(f"❌ 服务关闭失败: {e}")

@app.get("/")
async def root():
    """根路径 - API状态检查"""
    return {
        "message": "Rethinking Park Backend API",
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "duplicate_detection": settings.ENABLE_DUPLICATE_DETECTION,
            "cache_enabled": settings.REDIS_ENABLED,
            "rate_limit_enabled": settings.RATE_LIMIT_ENABLED
        }
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    stats = await storage_service.get_stats()
    cache_stats = await cache_service.get_cache_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "storage_stats": stats,
        "cache_stats": cache_stats
    }

@app.post(f"{settings.API_V1_STR}/upload", response_model=ImageUploadResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("upload"))
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    上传图像API
    
    - 计算图像哈希值，避免重复存储
    - 检测相似图像
    - 返回唯一的图像哈希作为标识符
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 验证图像
        is_valid, validation_message = gcs_service.validate_image(file_content, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_message)
        
        # 计算图像哈希
        md5_hash, perceptual_hash = hash_service.calculate_combined_hash(file_content)
        
        # 检查重复图像
        duplicate_check = await storage_service.check_duplicates(md5_hash, perceptual_hash)
        
        # 如果是完全重复的图像，返回现有信息
        if duplicate_check.is_duplicate:
            existing_image = await storage_service.get_image_info_by_hash(md5_hash)
            if existing_image:
                return ImageUploadResponse(
                    image_id=existing_image.image_id,
                    image_hash=md5_hash,
                    filename=file.filename,
                    file_size=len(file_content),
                    content_type=file.content_type,
                    gcs_url=existing_image.gcs_url,
                    upload_time=existing_image.upload_time,
                    status="duplicate",
                    is_duplicate=True,
                    similar_images=[img['image_hash'] for img in duplicate_check.similar_images]
                )
        
        # 上传到GCS
        image_id, image_hash, gcs_url, _ = await gcs_service.upload_image(
            file_content, 
            file.filename, 
            file.content_type
        )
        
        # 创建图像信息
        image_info = ImageInfo(
            image_id=image_id,
            image_hash=image_hash,
            perceptual_hash=perceptual_hash,
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            gcs_url=gcs_url,
            upload_time=datetime.now(),
            processed=False
        )
        
        # 保存到本地存储
        await storage_service.save_image_info(image_info)
        
        # 返回响应
        return ImageUploadResponse(
            image_id=image_id,
            image_hash=image_hash,
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            gcs_url=gcs_url,
            upload_time=datetime.now(),
            status="uploaded",
            is_duplicate=False,
            similar_images=[img['image_hash'] for img in duplicate_check.similar_images]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.post(f"{settings.API_V1_STR}/analyze", response_model=ImageAnalysisResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def analyze_image(request: Request, analysis_request: ImageAnalysisRequest):
    """
    图像分析API（基于哈希）
    
    - 使用图像哈希进行分析，支持缓存
    - 避免重复调用Vision API
    """
    try:
        image_hash = analysis_request.image_hash
        analysis_type = analysis_request.analysis_type
        
        # 检查缓存（除非强制刷新）
        if not analysis_request.force_refresh:
            cached_result = await cache_service.get_analysis_result(image_hash, analysis_type)
            if cached_result:
                return ImageAnalysisResponse(
                    image_hash=image_hash,
                    analysis_type=analysis_type,
                    results=cached_result["result"],
                    processed_time=datetime.fromisoformat(cached_result["cached_at"]),
                    success=True,
                    from_cache=True
                )
        
        # 获取图像信息
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # 从GCS下载图像内容进行分析
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # 使用Google Cloud Vision进行分析
        analysis_results = await vision_service.analyze_image(
            image_content, 
            analysis_type
        )
        
        # 缓存分析结果
        await cache_service.set_analysis_result(image_hash, analysis_type, analysis_results)
        
        # 更新存储的分析结果
        await storage_service.update_analysis_results(image_hash, analysis_results)
        
        return ImageAnalysisResponse(
            image_hash=image_hash,
            analysis_type=analysis_type,
            results=analysis_results,
            processed_time=datetime.now(),
            success=True,
            from_cache=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@app.post(f"{settings.API_V1_STR}/analyze-by-id", response_model=ImageAnalysisResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def analyze_image_by_id(request: Request, analysis_request: HashAnalysisRequest):
    """
    图像分析API（基于ID，向后兼容）
    """
    try:
        # 获取图像信息
        image_info = await storage_service.get_image_info(analysis_request.image_id)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # 转换为基于哈希的请求
        hash_request = ImageAnalysisRequest(
            image_hash=image_info.image_hash,
            analysis_type=analysis_request.analysis_type,
            options=analysis_request.options,
            force_refresh=False
        )
        
        return await analyze_image(request, hash_request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@app.get(f"{settings.API_V1_STR}/image/{{image_hash}}", response_model=ImageInfo)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_image_info_by_hash(request: Request, image_hash: str):
    """根据哈希值获取图像信息"""
    image_info = await storage_service.get_image_info_by_hash(image_hash)
    if not image_info:
        raise HTTPException(status_code=404, detail="图像未找到")
    return image_info

@app.get(f"{settings.API_V1_STR}/check-duplicate/{{image_hash}}", response_model=DuplicateCheckResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def check_duplicate(request: Request, image_hash: str):
    """检查图像是否重复"""
    # 首先尝试获取图像信息以获取感知哈希
    image_info = await storage_service.get_image_info_by_hash(image_hash)
    perceptual_hash = image_info.perceptual_hash if image_info else None
    
    return await storage_service.check_duplicates(image_hash, perceptual_hash)

@app.get(f"{settings.API_V1_STR}/images", response_model=List[ImageInfo])
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def list_images(
    request: Request,
    limit: int = Query(default=10, le=100, description="返回的图像数量"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """列出图像"""
    return await storage_service.list_images(limit=limit, offset=offset)

@app.delete(f"{settings.API_V1_STR}/image/{{image_hash}}")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("delete"))
async def delete_image_by_hash(request: Request, image_hash: str):
    """根据哈希值删除图像"""
    try:
        # 从缓存删除分析结果
        await cache_service.delete_analysis_result(image_hash)
        
        # 从GCS删除
        gcs_deleted = await gcs_service.delete_image(image_hash)
        
        # 从本地存储删除
        local_deleted = await storage_service.delete_image_info_by_hash(image_hash)
        
        if gcs_deleted or local_deleted:
            return {"message": f"图像 {image_hash[:8]}... 删除成功"}
        else:
            raise HTTPException(status_code=404, detail="图像未找到")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.get(f"{settings.API_V1_STR}/stats")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_stats(request: Request):
    """获取系统统计信息"""
    storage_stats = await storage_service.get_stats()
    cache_stats = await cache_service.get_cache_stats()
    
    return {
        "storage": storage_stats,
        "cache": cache_stats,
        "system": {
            "duplicate_detection": settings.ENABLE_DUPLICATE_DETECTION,
            "cache_enabled": settings.REDIS_ENABLED,
            "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD
        }
    }

# 错误处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="服务器内部错误",
            details={"exception": str(exc)}
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 