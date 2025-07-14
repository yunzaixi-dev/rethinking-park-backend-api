from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
import io
from datetime import datetime

from config import settings
from models.image import ImageUploadResponse, ImageAnalysisRequest, ImageAnalysisResponse, ErrorResponse, ImageInfo
from services.gcs_service import gcs_service
from services.vision_service import vision_service
from services.storage_service import storage_service

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能公园图像分析API - 使用Google Cloud Vision进行图像上传和分析",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
    except Exception as e:
        print(f"❌ GCS初始化失败: {e}")

@app.get("/")
async def root():
    """根路径 - API状态检查"""
    return {
        "message": "Rethinking Park Backend API",
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    stats = await storage_service.get_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    }

@app.post(f"{settings.API_V1_STR}/upload", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    上传图像API
    
    接收图像文件，验证格式，上传到Google Cloud Storage，返回唯一的图像ID
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 验证图像
        is_valid, validation_message = gcs_service.validate_image(file_content, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_message)
        
        # 上传到GCS
        image_id, gcs_url = await gcs_service.upload_image(
            file_content, 
            file.filename, 
            file.content_type
        )
        
        # 创建图像信息
        image_info = ImageInfo(
            image_id=image_id,
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
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            gcs_url=gcs_url,
            upload_time=datetime.now(),
            status="uploaded"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.post(f"{settings.API_V1_STR}/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    图像分析API
    
    使用图像ID进行Google Cloud Vision分析，支持多种分析类型
    """
    try:
        # 获取图像信息
        image_info = await storage_service.get_image_info(request.image_id)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # 从GCS下载图像内容进行分析
        image_content = await gcs_service.download_image(request.image_id)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # 使用Google Cloud Vision进行分析
        analysis_results = await vision_service.analyze_image(
            image_content, 
            request.analysis_type
        )
        
        # 更新存储的分析结果
        await storage_service.update_analysis_results(request.image_id, analysis_results)
        
        return ImageAnalysisResponse(
            image_id=request.image_id,
            analysis_type=request.analysis_type,
            results=analysis_results,
            processed_time=datetime.now(),
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@app.get(f"{settings.API_V1_STR}/image/{{image_id}}", response_model=ImageInfo)
async def get_image_info(image_id: str):
    """获取图像信息"""
    image_info = await storage_service.get_image_info(image_id)
    if not image_info:
        raise HTTPException(status_code=404, detail="图像未找到")
    return image_info

@app.get(f"{settings.API_V1_STR}/images", response_model=List[ImageInfo])
async def list_images(
    limit: int = Query(default=10, le=100, description="返回的图像数量"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """列出图像"""
    return await storage_service.list_images(limit=limit, offset=offset)

@app.delete(f"{settings.API_V1_STR}/image/{{image_id}}")
async def delete_image(image_id: str):
    """删除图像"""
    try:
        # 从GCS删除
        gcs_deleted = await gcs_service.delete_image(image_id)
        
        # 从本地存储删除
        local_deleted = await storage_service.delete_image_info(image_id)
        
        if gcs_deleted or local_deleted:
            return {"message": f"图像 {image_id} 删除成功"}
        else:
            raise HTTPException(status_code=404, detail="图像未找到")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.get(f"{settings.API_V1_STR}/stats")
async def get_stats():
    """获取系统统计信息"""
    return await storage_service.get_stats()

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