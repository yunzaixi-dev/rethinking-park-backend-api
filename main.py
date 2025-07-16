from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from typing import Optional, List
import io
import uuid
from datetime import datetime

from config import settings
from models.image import (
    ImageUploadResponse, 
    ImageAnalysisRequest, 
    ImageAnalysisResponse, 
    ErrorResponse, 
    ImageInfo,
    HashAnalysisRequest,
    DuplicateCheckResponse,
    EnhancedDetectionRequest,
    EnhancedDetectionResponse,
    SimpleExtractionRequest,
    SimpleExtractionResponse,
    LabelAnalysisRequest,
    LabelAnalysisResponse,
    NaturalElementsRequest,
    NaturalElementsResponse,
    AnnotatedImageRequest,
    AnnotatedImageResponse,
    BatchProcessingRequest,
    BatchProcessingResponse,
    BatchJobStatus,
    BatchResultsResponse
)
from services.gcs_service import gcs_service
from services.vision_service import vision_service
from services.enhanced_vision_service import enhanced_vision_service
from services.image_processing_service import image_processing_service
from services.label_analysis_service import label_analysis_service
from services.storage_service import storage_service
from services.cache_service import cache_service
from services.hash_service import hash_service
from services.rate_limiter import limiter, rate_limiter_service
from services.natural_element_analyzer import natural_element_analyzer
from services.image_annotation_service import image_annotation_service
from services.batch_processing_service import batch_processing_service
from services.performance_optimizer import get_performance_optimizer
from services.monitoring_service import get_monitoring_service

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
        
        # Initialize performance optimizer
        optimizer = await get_performance_optimizer()
        print("✅ 性能优化器初始化完成")
        
    except Exception as e:
        print(f"❌ 服务初始化失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    try:
        # Shutdown performance optimizer
        optimizer = await get_performance_optimizer()
        await optimizer.shutdown()
        print("✅ 性能优化器已关闭")
        
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
    cache_stats = cache_service.get_stats()
    
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
    cache_stats = cache_service.get_stats()
    
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

# Enhanced Image Processing Endpoints

@app.post(f"{settings.API_V1_STR}/detect-objects-enhanced", response_model=EnhancedDetectionResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def detect_objects_enhanced(request: Request, detection_request: EnhancedDetectionRequest):
    """
    Enhanced object detection endpoint with face detection inclusion
    
    - Provides precise bounding boxes and confidence scores
    - Includes face detection with position marking
    - Returns detailed object information with unique IDs
    - Supports confidence threshold filtering
    """
    try:
        image_hash = detection_request.image_hash
        
        # Check cache first (unless force refresh is requested)
        cache_key = f"enhanced_detection:{image_hash}:{detection_request.confidence_threshold}:{detection_request.include_faces}:{detection_request.include_labels}"
        cached_result = await cache_service.get_cached_data(cache_key)
        
        if cached_result:
            # Return cached result with updated timestamp
            cached_response = EnhancedDetectionResponse(**cached_result)
            cached_response.from_cache = True
            return cached_response
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Perform enhanced object detection
        detection_response = await enhanced_vision_service.detect_objects_enhanced(
            image_content=image_content,
            image_hash=image_hash,
            include_faces=detection_request.include_faces,
            include_labels=detection_request.include_labels,
            confidence_threshold=detection_request.confidence_threshold,
            max_results=detection_request.max_results
        )
        
        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, 
            detection_response.dict(), 
            ttl=3600  # Cache for 1 hour
        )
        
        return detection_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced detection failed: {str(e)}")

@app.post(f"{settings.API_V1_STR}/extract-object-simple", response_model=SimpleExtractionResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def extract_object_simple(request: Request, extraction_request: SimpleExtractionRequest):
    """
    Simple object extraction endpoint using bounding box coordinates
    
    - Extracts objects based on bounding box with optional padding
    - Supports multiple output formats (PNG, WEBP, JPG)
    - Stores extracted objects in GCS
    - Provides simple background removal options
    """
    try:
        start_time = datetime.now()
        image_hash = extraction_request.image_hash
        
        # Generate extraction ID
        extraction_id = f"extract_{image_hash[:8]}_{uuid.uuid4().hex[:8]}"
        
        # Check cache first
        cache_key = f"simple_extraction:{image_hash}:{hash(str(extraction_request.bounding_box.dict()))}:{extraction_request.output_format}:{extraction_request.add_padding}"
        cached_result = await cache_service.get_cached_data(cache_key)
        
        if cached_result:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cached_response = SimpleExtractionResponse(**cached_result)
            cached_response.from_cache = True
            cached_response.processing_time_ms = processing_time
            return cached_response
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Validate extraction request
        validation_result = image_processing_service.validate_extraction_request(
            image_content, extraction_request.bounding_box, extraction_request.add_padding
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid extraction request: {'; '.join(validation_result['errors'])}"
            )
        
        # Perform simple object extraction
        extraction_result = image_processing_service.extract_by_bounding_box(
            image_content=image_content,
            bounding_box=extraction_request.bounding_box,
            padding=extraction_request.add_padding,
            output_format=extraction_request.output_format.upper(),
            background_removal=False  # Simple extraction without background removal for now
        )
        
        # Upload extracted object to GCS
        extracted_filename = f"extracted_{extraction_id}.{extraction_request.output_format.lower()}"
        content_type = f"image/{extraction_request.output_format.lower()}"
        if extraction_request.output_format.lower() == "jpg":
            content_type = "image/jpeg"
        
        # Upload to GCS with a specific path for extracted objects
        extracted_image_id, extracted_hash, extracted_gcs_url, _ = await gcs_service.upload_image(
            extraction_result.extracted_image_bytes,
            extracted_filename,
            content_type,
            folder_prefix="extracted/"
        )
        
        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        from models.image import SimpleExtractionResult as ResponseExtractionResult
        response_result = ResponseExtractionResult(
            extracted_image_url=extracted_gcs_url,
            bounding_box=extraction_request.bounding_box,
            original_size=extraction_result.original_size,
            extracted_size=extraction_result.extracted_size,
            processing_method=extraction_result.processing_method,
            file_size=len(extraction_result.extracted_image_bytes),
            format=extraction_request.output_format.lower()
        )
        
        response = SimpleExtractionResponse(
            image_hash=image_hash,
            extraction_id=extraction_id,
            result=response_result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None
        )
        
        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, 
            response.dict(), 
            ttl=7200  # Cache for 2 hours
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return SimpleExtractionResponse(
            image_hash=extraction_request.image_hash,
            extraction_id=f"failed_{uuid.uuid4().hex[:8]}",
            result=None,
            processing_time_ms=processing_time,
            success=False,
            from_cache=False,
            error_message=f"Extraction failed: {str(e)}"
        )

@app.post(f"{settings.API_V1_STR}/analyze-by-labels", response_model=LabelAnalysisResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def analyze_by_labels(request: Request, analysis_request: LabelAnalysisRequest):
    """
    Label-based analysis endpoint for natural element categorization
    
    - Analyzes images based on Google Vision labels
    - Categorizes natural elements (vegetation, sky, water, etc.)
    - Provides confidence-based coverage estimation
    - Includes natural element insights and recommendations
    """
    try:
        start_time = datetime.now()
        image_hash = analysis_request.image_hash
        
        # Check cache first
        cache_key = f"label_analysis:{image_hash}:{hash(str(sorted(analysis_request.target_categories)))}:{analysis_request.confidence_threshold}:{analysis_request.max_labels}"
        cached_result = await cache_service.get_cached_data(cache_key)
        
        if cached_result:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cached_response = LabelAnalysisResponse(**cached_result)
            cached_response.from_cache = True
            cached_response.processing_time_ms = processing_time
            return cached_response
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Get labels from Google Vision API
        labels_response = await vision_service.analyze_image(image_content, "labels")
        if not labels_response or "labels" not in labels_response:
            raise HTTPException(status_code=500, detail="Failed to get labels from Vision API")
        
        # Filter labels by confidence threshold
        all_labels = labels_response["labels"]
        filtered_labels = [
            label for label in all_labels 
            if label.get("confidence", 0) >= analysis_request.confidence_threshold
        ][:analysis_request.max_labels]
        
        # Perform label-based analysis
        analysis_result = label_analysis_service.analyze_by_labels(
            labels=filtered_labels,
            image_content=image_content,
            analysis_depth="comprehensive",
            include_confidence=analysis_request.include_confidence
        )
        
        # Create category results for target categories
        category_results = []
        categorized_elements = analysis_result.get("categorized_elements", {})
        
        for target_category in analysis_request.target_categories:
            category_key = target_category.lower()
            # Map common category names to our internal categories
            if category_key in ["plant", "tree", "grass", "flower"]:
                category_key = "vegetation"
            elif category_key in ["building", "structure"]:
                category_key = "built_environment"
            
            matched_labels = categorized_elements.get(category_key, [])
            
            if matched_labels:
                total_confidence = sum(label.get("confidence", 0) for label in matched_labels)
                average_confidence = total_confidence / len(matched_labels)
                coverage_estimate = min(100.0, total_confidence * 20)  # Simple coverage estimation
                
                from models.image import LabelCategoryResult
                category_result = LabelCategoryResult(
                    category_name=target_category,
                    matched_labels=matched_labels,
                    total_confidence=total_confidence,
                    average_confidence=average_confidence,
                    coverage_estimate=coverage_estimate,
                    label_count=len(matched_labels)
                )
                category_results.append(category_result)
        
        # Extract coverage statistics
        coverage_stats = analysis_result.get("coverage_statistics", {})
        natural_elements_summary = {
            "vegetation": coverage_stats.get("vegetation_coverage", 0.0),
            "sky": coverage_stats.get("sky_coverage", 0.0),
            "water": coverage_stats.get("water_coverage", 0.0),
            "built_environment": coverage_stats.get("built_environment_coverage", 0.0)
        }
        
        # Create confidence distribution
        confidence_analysis = analysis_result.get("confidence_analysis", {})
        confidence_distribution = confidence_analysis.get("confidence_distribution", {
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0
        })
        
        # Get top categories
        top_categories = sorted(
            natural_elements_summary.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        top_categories = [category for category, _ in top_categories if _ > 0]
        
        # Create analysis result
        from models.image import LabelAnalysisResult
        result = LabelAnalysisResult(
            all_labels=filtered_labels,
            category_analysis=category_results,
            natural_elements_summary=natural_elements_summary,
            confidence_distribution=confidence_distribution,
            top_categories=top_categories,
            analysis_metadata={
                "total_labels_processed": len(filtered_labels),
                "confidence_threshold": analysis_request.confidence_threshold,
                "target_categories": analysis_request.target_categories,
                "analysis_time": datetime.now().isoformat()
            }
        )
        
        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response = LabelAnalysisResponse(
            image_hash=image_hash,
            results=result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None
        )
        
        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, 
            response.dict(), 
            ttl=3600  # Cache for 1 hour
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return LabelAnalysisResponse(
            image_hash=analysis_request.image_hash,
            results=None,
            processing_time_ms=processing_time,
            success=False,
            from_cache=False,
            error_message=f"Label analysis failed: {str(e)}"
        )

@app.post(f"{settings.API_V1_STR}/analyze-nature", response_model=NaturalElementsResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def analyze_nature(request: Request, analysis_request: NaturalElementsRequest):
    """
    Natural elements analysis endpoint with comprehensive health assessment
    
    - Implements comprehensive analysis with health assessment
    - Creates coverage statistics and color analysis
    - Provides vegetation health metrics and seasonal analysis
    - Includes detailed recommendations for park management
    """
    try:
        start_time = datetime.now()
        image_hash = analysis_request.image_hash
        
        # Check cache first
        cache_key = f"nature_analysis:{image_hash}:{analysis_request.analysis_depth}:{analysis_request.include_health_assessment}:{analysis_request.include_seasonal_analysis}:{analysis_request.include_color_analysis}:{analysis_request.confidence_threshold}"
        cached_result = await cache_service.get(cache_key)
        
        if cached_result:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cached_response = NaturalElementsResponse(**cached_result)
            cached_response.from_cache = True
            cached_response.processing_time_ms = processing_time
            return cached_response
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Check if Vision service is enabled
        if not vision_service.is_enabled():
            raise HTTPException(
                status_code=503, 
                detail="Vision service is not available - Google Cloud credentials not found"
            )
        
        # Perform comprehensive natural elements analysis
        analysis_result = await natural_element_analyzer.analyze_natural_elements(
            image_content=image_content,
            vision_client=vision_service.client,
            analysis_depth=analysis_request.analysis_depth
        )
        
        # Apply confidence threshold filtering if needed
        if analysis_request.confidence_threshold > 0.3:
            # Filter out low-confidence elements from categories
            filtered_categories = []
            for category in analysis_result.element_categories:
                if category.confidence_score >= analysis_request.confidence_threshold:
                    filtered_categories.append(category)
            analysis_result.element_categories = filtered_categories
        
        # Optionally disable certain analysis components based on request
        if not analysis_request.include_health_assessment:
            analysis_result.vegetation_health_score = None
            analysis_result.vegetation_health_metrics = None
        
        if not analysis_request.include_seasonal_analysis:
            analysis_result.seasonal_indicators = []
            analysis_result.seasonal_analysis = None
        
        if not analysis_request.include_color_analysis:
            analysis_result.dominant_colors = []
            analysis_result.color_diversity_score = None
        
        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response = NaturalElementsResponse(
            image_hash=image_hash,
            results=analysis_result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None,
            enabled=True
        )
        
        # Cache the result for future requests
        await cache_service.set(
            cache_key, 
            response.dict(), 
            ttl_hours=2  # Cache for 2 hours (longer than other endpoints due to complexity)
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return NaturalElementsResponse(
            image_hash=analysis_request.image_hash,
            results=None,
            processing_time_ms=processing_time,
            success=False,
            from_cache=False,
            error_message=f"Natural elements analysis failed: {str(e)}",
            enabled=vision_service.is_enabled()
        )

@app.post(f"{settings.API_V1_STR}/download-annotated", response_model=AnnotatedImageResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def download_annotated(request: Request, annotation_request: AnnotatedImageRequest):
    """
    Annotated image download endpoint
    
    - Implements POST /api/v1/download-annotated
    - Add face markers and object boxes rendering
    - Create customizable annotation styles
    - Requirements: 1.1, 1.2
    """
    try:
        start_time = datetime.now()
        image_hash = annotation_request.image_hash
        
        # Generate annotation ID
        annotation_id = f"annotated_{image_hash[:8]}_{uuid.uuid4().hex[:8]}"
        
        # Check cache first
        cache_key = f"annotated_image:{image_hash}:{annotation_request.include_face_markers}:{annotation_request.include_object_boxes}:{annotation_request.include_labels}:{annotation_request.output_format}:{annotation_request.confidence_threshold}:{annotation_request.max_objects}"
        if annotation_request.annotation_style:
            cache_key += f":{hash(str(annotation_request.annotation_style.dict()))}"
        
        cached_result = await cache_service.get(cache_key)
        
        if cached_result:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cached_response = AnnotatedImageResponse(**cached_result)
            cached_response.from_cache = True
            cached_response.processing_time_ms = processing_time
            return cached_response
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Get detection results for annotation
        objects = []
        faces = []
        labels = []
        
        # Get enhanced detection results if needed
        if annotation_request.include_object_boxes or annotation_request.include_labels:
            try:
                detection_response = await enhanced_vision_service.detect_objects_enhanced(
                    image_content=image_content,
                    image_hash=image_hash,
                    include_faces=annotation_request.include_face_markers,
                    include_labels=annotation_request.include_labels,
                    confidence_threshold=annotation_request.confidence_threshold,
                    max_results=annotation_request.max_objects
                )
                
                if detection_response.success:
                    objects = detection_response.objects[:annotation_request.max_objects]
                    if annotation_request.include_face_markers:
                        faces = detection_response.faces
                    if annotation_request.include_labels:
                        labels = detection_response.labels
                        
            except Exception as e:
                # Log error but continue with empty detection results
                print(f"Warning: Detection failed for annotation: {e}")
        
        # Prepare custom styles
        custom_styles = None
        if annotation_request.annotation_style:
            custom_styles = annotation_request.annotation_style.dict()
        
        # Validate annotation request
        validation_result = image_annotation_service.validate_annotation_request(
            image_content=image_content,
            objects=objects,
            faces=faces
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid annotation request: {'; '.join(validation_result['errors'])}"
            )
        
        # Render annotated image
        annotated_image_bytes = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=objects if annotation_request.include_object_boxes else None,
            faces=faces if annotation_request.include_face_markers else None,
            labels=labels if annotation_request.include_labels else None,
            include_face_markers=annotation_request.include_face_markers,
            include_object_boxes=annotation_request.include_object_boxes,
            include_labels=annotation_request.include_labels,
            custom_styles=custom_styles
        )
        
        # Upload annotated image to GCS
        annotated_filename = f"annotated_{annotation_id}.{annotation_request.output_format.lower()}"
        content_type = f"image/{annotation_request.output_format.lower()}"
        if annotation_request.output_format.lower() == "jpg":
            content_type = "image/jpeg"
        
        # Convert to requested format if not PNG
        if annotation_request.output_format.lower() != "png":
            from PIL import Image
            import io
            
            pil_image = Image.open(io.BytesIO(annotated_image_bytes))
            if annotation_request.output_format.lower() == "jpg":
                # Convert to RGB for JPEG (remove alpha channel)
                if pil_image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', pil_image.size, (255, 255, 255))
                    if pil_image.mode == 'RGBA':
                        background.paste(pil_image, mask=pil_image.split()[-1])
                    else:
                        background.paste(pil_image, mask=pil_image.split()[-1])
                    pil_image = background
                
                output_buffer = io.BytesIO()
                pil_image.save(output_buffer, format='JPEG', quality=annotation_request.quality)
                annotated_image_bytes = output_buffer.getvalue()
            elif annotation_request.output_format.lower() == "webp":
                output_buffer = io.BytesIO()
                pil_image.save(output_buffer, format='WEBP', quality=annotation_request.quality)
                annotated_image_bytes = output_buffer.getvalue()
        
        # Upload to GCS with a specific path for annotated images
        annotated_image_id, annotated_hash, annotated_gcs_url, _ = await gcs_service.upload_image(
            annotated_image_bytes,
            annotated_filename,
            content_type,
            folder_prefix="annotated/"
        )
        
        # Get annotation statistics
        annotation_stats = image_annotation_service.get_annotation_statistics(
            objects=objects,
            faces=faces
        )
        
        # Get image size
        from PIL import Image
        pil_image = Image.open(io.BytesIO(annotated_image_bytes))
        from models.image import ImageSize
        image_size = ImageSize(width=pil_image.width, height=pil_image.height)
        
        # Create response result
        from models.image import AnnotatedImageResult
        result = AnnotatedImageResult(
            annotated_image_url=annotated_gcs_url,
            original_image_url=image_info.gcs_url,
            annotation_stats=annotation_stats,
            file_size=len(annotated_image_bytes),
            format=annotation_request.output_format.lower(),
            image_size=image_size
        )
        
        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response = AnnotatedImageResponse(
            image_hash=image_hash,
            annotation_id=annotation_id,
            result=result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None
        )
        
        # Cache the result for future requests
        await cache_service.set(
            cache_key,
            response.dict(),
            ttl_hours=2  # Cache for 2 hours
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return AnnotatedImageResponse(
            image_hash=annotation_request.image_hash,
            annotation_id=f"failed_{uuid.uuid4().hex[:8]}",
            result=None,
            processing_time_ms=processing_time,
            success=False,
            from_cache=False,
            error_message=f"Annotation failed: {str(e)}"
        )

# Batch Processing Endpoints

@app.post(f"{settings.API_V1_STR}/batch-process", response_model=BatchProcessingResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("batch"))
async def create_batch_job(request: Request, batch_request: BatchProcessingRequest):
    """
    Create and start a batch processing job
    
    This endpoint allows processing multiple operations on images in batch.
    Supports up to 10 concurrent operations and 50 total operations per batch.
    """
    start_time = datetime.now()
    
    try:
        # Validate operations
        if not batch_request.operations:
            raise HTTPException(status_code=400, detail="Operations list cannot be empty")
        
        if len(batch_request.operations) > 50:
            raise HTTPException(status_code=400, detail="Too many operations in batch (max 50)")
        
        # Convert operations to dict format
        operations_data = []
        for op in batch_request.operations:
            operations_data.append({
                "type": op.type,
                "image_hash": op.image_hash,
                "parameters": op.parameters,
                "max_retries": op.max_retries
            })
        
        # Create batch job
        batch_id = await batch_processing_service.create_batch_job(
            operations=operations_data,
            callback_url=batch_request.callback_url,
            max_concurrent_operations=batch_request.max_concurrent_operations
        )
        
        # Start the batch job
        started = await batch_processing_service.start_batch_job(batch_id)
        if not started:
            raise HTTPException(status_code=500, detail="Failed to start batch job")
        
        return BatchProcessingResponse(
            batch_id=batch_id,
            status="running",
            message=f"Batch job created and started with {len(batch_request.operations)} operations",
            created_time=start_time,
            total_operations=len(batch_request.operations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@app.get(f"{settings.API_V1_STR}/batch-process/{{batch_id}}/status", response_model=BatchJobStatus)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def get_batch_status(request: Request, batch_id: str):
    """
    Get the status of a batch processing job
    
    Returns detailed status including progress, individual operation statuses,
    and completion statistics.
    """
    try:
        status = await batch_processing_service.get_batch_status(batch_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Batch job {batch_id} not found")
        
        # Convert to response model
        operations = []
        for op_data in status.get("operations", []):
            from models.image import BatchOperationResult
            operations.append(BatchOperationResult(**op_data))
        
        return BatchJobStatus(
            batch_id=status["batch_id"],
            status=status["status"],
            created_time=datetime.fromisoformat(status["created_time"]),
            start_time=datetime.fromisoformat(status["start_time"]) if status["start_time"] else None,
            end_time=datetime.fromisoformat(status["end_time"]) if status["end_time"] else None,
            callback_url=status["callback_url"],
            max_concurrent_operations=status["max_concurrent_operations"],
            total_operations=status["total_operations"],
            completed_operations=status["completed_operations"],
            failed_operations=status["failed_operations"],
            progress_percentage=status["progress_percentage"],
            operations=operations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")

@app.get(f"{settings.API_V1_STR}/batch-process/{{batch_id}}/results", response_model=BatchResultsResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def get_batch_results(request: Request, batch_id: str):
    """
    Get aggregated results from a completed batch processing job
    
    Returns detailed results organized by operation type, success/failure statistics,
    and individual operation results.
    """
    try:
        results = await batch_processing_service.get_batch_results(batch_id)
        if not results:
            raise HTTPException(
                status_code=404, 
                detail=f"Batch job {batch_id} not found or not completed"
            )
        
        # Convert operation results to response models
        from models.image import BatchOperationResult
        successful_operations = [BatchOperationResult(**op) for op in results["successful_operations"]]
        failed_operations = [BatchOperationResult(**op) for op in results["failed_operations"]]
        
        return BatchResultsResponse(
            batch_id=results["batch_id"],
            summary=results["summary"],
            results_by_type=results["results_by_type"],
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            batch_metadata=results["batch_metadata"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch results: {str(e)}")

@app.delete(f"{settings.API_V1_STR}/batch-process/{{batch_id}}")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def cancel_batch_job(request: Request, batch_id: str):
    """
    Cancel a running batch processing job
    
    Cancels pending operations and marks the job as cancelled.
    Running operations will complete but no new operations will start.
    """
    try:
        cancelled = await batch_processing_service.cancel_batch_job(batch_id)
        if not cancelled:
            raise HTTPException(
                status_code=404, 
                detail=f"Batch job {batch_id} not found or cannot be cancelled"
            )
        
        return {"message": f"Batch job {batch_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel batch job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch job: {str(e)}")

@app.get(f"{settings.API_V1_STR}/batch-process/statistics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def get_batch_statistics(request: Request):
    """
    Get batch processing service statistics
    
    Returns overall service statistics including job counts, processing times,
    and service health information.
    """
    try:
        stats = batch_processing_service.get_service_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get batch statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch statistics: {str(e)}")

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

# Performance Optimized Endpoints

@app.post(f"{settings.API_V1_STR}/detect-objects-optimized", response_model=EnhancedDetectionResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def detect_objects_optimized(request: Request, detection_request: EnhancedDetectionRequest):
    """
    Performance-optimized object detection endpoint with batching and caching
    
    - Uses Google Vision API call batching for improved efficiency
    - Implements memory optimization for no-GPU environment
    - Advanced caching with TTL management
    - Async processing for better resource utilization
    """
    try:
        optimizer = await get_performance_optimizer()
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(detection_request.image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(detection_request.image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Use performance optimizer for detection
        result = await optimizer.optimize_detection_request(
            image_content=image_content,
            image_hash=detection_request.image_hash,
            confidence_threshold=detection_request.confidence_threshold,
            include_faces=detection_request.include_faces,
            include_labels=detection_request.include_labels,
            use_batching=True
        )
        
        # Convert result to response format
        if isinstance(result, dict) and "success" in result:
            if result["success"]:
                return EnhancedDetectionResponse(
                    image_hash=detection_request.image_hash,
                    objects=result.get("objects", []),
                    faces=result.get("faces", []),
                    labels=result.get("labels", []),
                    detection_time=datetime.fromisoformat(result.get("detection_time", datetime.now().isoformat())),
                    success=True,
                    enabled=result.get("enabled", True),
                    error_message=None,
                    from_cache=result.get("from_cache", False)
                )
            else:
                return EnhancedDetectionResponse(
                    image_hash=detection_request.image_hash,
                    objects=[],
                    faces=[],
                    labels=[],
                    detection_time=datetime.now(),
                    success=False,
                    enabled=result.get("enabled", True),
                    error_message=result.get("error_message", "Detection failed"),
                    from_cache=False
                )
        else:
            # Handle direct EnhancedDetectionResponse
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        return EnhancedDetectionResponse(
            image_hash=detection_request.image_hash,
            objects=[],
            faces=[],
            labels=[],
            detection_time=datetime.now(),
            success=False,
            enabled=True,
            error_message=f"Optimized detection failed: {str(e)}",
            from_cache=False
        )

@app.post(f"{settings.API_V1_STR}/analyze-nature-optimized", response_model=NaturalElementsResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def analyze_nature_optimized(request: Request, analysis_request: NaturalElementsRequest):
    """
    Performance-optimized natural elements analysis with batching
    
    - Optimized Google Vision API call batching and caching
    - Memory usage optimization for image annotation processing
    - Async processing for batch operations
    """
    try:
        start_time = datetime.now()
        optimizer = await get_performance_optimizer()
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(analysis_request.image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")
        
        # Download image content from GCS
        image_content = await gcs_service.download_image(analysis_request.image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")
        
        # Use performance optimizer for natural elements analysis
        result = await optimizer.optimize_natural_elements_analysis(
            image_content=image_content,
            image_hash=analysis_request.image_hash,
            analysis_depth=analysis_request.analysis_depth,
            use_batching=True
        )
        
        # Convert result to response format
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if isinstance(result, dict):
            # Create NaturalElementsResult from the analysis result
            from models.image import NaturalElementsResult
            
            natural_elements = result.get("natural_elements", {})
            color_analysis = result.get("color_analysis", {})
            
            # Extract coverage statistics
            coverage_stats = natural_elements.get("coverage_statistics", {})
            
            # Create the result object
            analysis_result = NaturalElementsResult(
                vegetation_coverage=coverage_stats.get("vegetation_coverage", 0.0),
                sky_coverage=coverage_stats.get("sky_coverage", 0.0),
                water_coverage=coverage_stats.get("water_coverage", 0.0),
                built_environment_coverage=coverage_stats.get("built_environment_coverage", 0.0),
                vegetation_health_score=result.get("vegetation_health_score"),
                dominant_colors=[],  # Simplified for now
                seasonal_indicators=[],  # Simplified for now
                analysis_metadata={
                    "analysis_depth": analysis_request.analysis_depth,
                    "processing_time_ms": processing_time,
                    "optimized": True
                }
            )
            
            return NaturalElementsResponse(
                image_hash=analysis_request.image_hash,
                results=analysis_result,
                processing_time_ms=processing_time,
                success=True,
                from_cache=result.get("from_cache", False),
                error_message=None
            )
        else:
            # Handle direct response
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return NaturalElementsResponse(
            image_hash=analysis_request.image_hash,
            results=None,
            processing_time_ms=processing_time,
            success=False,
            from_cache=False,
            error_message=f"Optimized nature analysis failed: {str(e)}"
        )

@app.post(f"{settings.API_V1_STR}/batch-process-optimized", response_model=BatchProcessingResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("batch"))
async def batch_process_optimized(request: Request, batch_request: BatchProcessingRequest):
    """
    Performance-optimized batch processing with async queue management
    
    - Creates async processing for batch operations
    - Optimizes memory usage during batch processing
    - Implements intelligent concurrency control
    """
    try:
        optimizer = await get_performance_optimizer()
        
        # Validate batch request
        if not batch_request.operations:
            raise HTTPException(status_code=400, detail="No operations provided")
        
        if len(batch_request.operations) > 50:
            raise HTTPException(status_code=400, detail="Too many operations (max 50)")
        
        # Use optimized batch processing
        batch_id = await optimizer.optimize_batch_processing(
            operations=[op.dict() for op in batch_request.operations],
            max_concurrent=min(batch_request.max_concurrent_operations, 10)
        )
        
        # Start the batch job
        from services.batch_processing_service import batch_processing_service
        started = await batch_processing_service.start_batch_job(batch_id)
        
        if not started:
            raise HTTPException(status_code=500, detail="Failed to start batch job")
        
        return BatchProcessingResponse(
            batch_id=batch_id,
            status="started",
            message="Optimized batch processing started successfully",
            total_operations=len(batch_request.operations),
            estimated_completion_time=None,
            callback_url=batch_request.callback_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimized batch processing failed: {str(e)}")

@app.get(f"{settings.API_V1_STR}/performance-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_performance_metrics(request: Request):
    """
    Get comprehensive performance optimization metrics
    
    - API call batching efficiency
    - Memory optimization statistics
    - Cache performance metrics
    - Async processing queue status
    """
    try:
        optimizer = await get_performance_optimizer()
        metrics = optimizer.get_performance_metrics()
        
        # Add cache service metrics
        cache_stats = cache_service.get_stats()
        
        # Combine metrics
        comprehensive_metrics = {
            "timestamp": datetime.now().isoformat(),
            "optimization_metrics": metrics,
            "cache_metrics": cache_stats,
            "system_info": {
                "redis_enabled": settings.REDIS_ENABLED,
                "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
                "vision_api_enabled": vision_service.is_enabled()
            }
        }
        
        return comprehensive_metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@app.post(f"{settings.API_V1_STR}/optimize-performance")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("admin"))
async def trigger_performance_optimization(request: Request):
    """
    Manually trigger performance optimization cycle
    
    - Memory cleanup and optimization
    - Cache eviction and cleanup
    - Performance metrics reset
    """
    try:
        optimizer = await get_performance_optimizer()
        optimization_results = await optimizer.perform_optimization_cycle()
        
        return {
            "message": "Performance optimization cycle completed",
            "results": optimization_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance optimization failed: {str(e)}")

# Production Monitoring and Health Check Endpoints

@app.get(f"{settings.API_V1_STR}/health-detailed")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_detailed_health_status(request: Request):
    """
    Comprehensive health check endpoint for production monitoring
    
    - Checks all critical services (database, cache, Vision API, storage)
    - Provides detailed health status with response times
    - Includes performance optimization status
    - Returns overall system health assessment
    """
    try:
        monitoring = await get_monitoring_service()
        health_status = await monitoring.get_health_status()
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": f"Health check failed: {str(e)}",
            "checks": {},
            "uptime_seconds": 0
        }

@app.get(f"{settings.API_V1_STR}/metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_system_metrics(request: Request):
    """
    System and API metrics endpoint for monitoring
    
    - Provides comprehensive system metrics (CPU, memory, disk)
    - Includes API performance metrics (requests, response times)
    - Shows Google Vision API usage statistics
    - Returns performance optimization metrics
    """
    try:
        monitoring = await get_monitoring_service()
        metrics = await monitoring.get_metrics()
        
        return metrics
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": f"Metrics collection failed: {str(e)}",
            "system": {},
            "api": {},
            "performance": {}
        }

@app.get(f"{settings.API_V1_STR}/vision-api-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_vision_api_metrics(request: Request):
    """
    Google Cloud Vision API usage metrics
    
    - Tracks API call frequency and success rates
    - Monitors API response times and error rates
    - Provides quota usage information
    - Shows optimization effectiveness
    """
    try:
        monitoring = await get_monitoring_service()
        api_metrics = monitoring.metrics_collector.get_api_metrics()
        
        # Get performance optimizer metrics for Vision API
        optimizer = await get_performance_optimizer()
        performance_metrics = optimizer.get_performance_metrics()
        
        vision_metrics = {
            "timestamp": datetime.now().isoformat(),
            "vision_api_calls": api_metrics.vision_api_calls,
            "api_optimization": {
                "batched_calls": performance_metrics["api_calls"]["batched"],
                "individual_calls": performance_metrics["api_calls"]["individual"],
                "batch_efficiency_ratio": performance_metrics["api_calls"]["batch_efficiency_ratio"]
            },
            "cache_performance": {
                "hit_rate": api_metrics.cache_hit_rate,
                "cache_enabled": cache_service.is_enabled()
            },
            "service_status": {
                "vision_api_enabled": vision_service.is_enabled(),
                "enhanced_vision_enabled": True,
                "performance_optimization_active": True
            }
        }
        
        return vision_metrics
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": f"Vision API metrics collection failed: {str(e)}",
            "vision_api_calls": 0,
            "service_status": {
                "vision_api_enabled": False,
                "enhanced_vision_enabled": False,
                "performance_optimization_active": False
            }
        }

@app.get(f"{settings.API_V1_STR}/cache-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_cache_metrics(request: Request):
    """
    Cache performance metrics endpoint
    
    - Provides detailed cache statistics and performance
    - Shows hit rates and memory usage
    - Includes cache optimization metrics
    - Returns cache health status
    """
    try:
        # Get basic cache stats
        cache_stats = cache_service.get_stats()
        
        # Get detailed cache statistics if available
        detailed_stats = {}
        if hasattr(cache_service, 'get_detailed_cache_statistics'):
            detailed_stats = await cache_service.get_detailed_cache_statistics()
        
        # Get performance optimizer cache metrics
        optimizer = await get_performance_optimizer()
        performance_metrics = optimizer.get_performance_metrics()
        cache_performance = performance_metrics.get("cache_performance", {})
        
        combined_metrics = {
            "timestamp": datetime.now().isoformat(),
            "basic_stats": cache_stats,
            "detailed_stats": detailed_stats,
            "performance_metrics": cache_performance,
            "optimization_status": {
                "lru_eviction_active": cache_service.is_enabled(),
                "memory_optimization_enabled": True,
                "cache_warming_available": True
            }
        }
        
        return combined_metrics
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": f"Cache metrics collection failed: {str(e)}",
            "basic_stats": {"enabled": False},
            "optimization_status": {
                "lru_eviction_active": False,
                "memory_optimization_enabled": False,
                "cache_warming_available": False
            }
        }

@app.get(f"{settings.API_V1_STR}/batch-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_batch_processing_metrics(request: Request):
    """
    Batch processing metrics endpoint
    
    - Shows active batch operations and queue status
    - Provides batch processing performance statistics
    - Includes async processing queue metrics
    - Returns batch optimization effectiveness
    """
    try:
        # Get performance optimizer async queue stats
        optimizer = await get_performance_optimizer()
        performance_metrics = optimizer.get_performance_metrics()
        async_processing = performance_metrics.get("async_processing", {})
        
        # Get batch processing service stats if available
        batch_stats = {}
        if hasattr(batch_processing_service, 'get_stats'):
            batch_stats = batch_processing_service.get_stats()
        
        # Get monitoring service batch metrics
        monitoring = await get_monitoring_service()
        api_metrics = monitoring.metrics_collector.get_api_metrics()
        
        batch_metrics = {
            "timestamp": datetime.now().isoformat(),
            "active_batch_operations": api_metrics.batch_operations_active,
            "async_processing": async_processing,
            "batch_service_stats": batch_stats,
            "optimization_status": {
                "async_queue_active": async_processing.get("is_running", False),
                "concurrent_processing_enabled": True,
                "batch_optimization_active": True
            }
        }
        
        return batch_metrics
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": f"Batch metrics collection failed: {str(e)}",
            "active_batch_operations": 0,
            "optimization_status": {
                "async_queue_active": False,
                "concurrent_processing_enabled": False,
                "batch_optimization_active": False
            }
        }

@app.post(f"{settings.API_V1_STR}/trigger-optimization")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("admin"))
async def trigger_system_optimization(request: Request):
    """
    Manually trigger system optimization cycle
    
    - Performs memory cleanup and optimization
    - Triggers cache eviction and cleanup
    - Runs performance optimization cycle
    - Returns optimization results and statistics
    """
    try:
        # Get performance optimizer and run optimization cycle
        optimizer = await get_performance_optimizer()
        optimization_results = await optimizer.perform_optimization_cycle()
        
        # Also trigger cache optimization if available
        cache_optimization = {}
        if cache_service.is_enabled() and hasattr(cache_service, 'implement_lru_eviction'):
            cache_optimization = await cache_service.implement_lru_eviction(max_memory_mb=100)
        
        return {
            "message": "System optimization cycle completed successfully",
            "timestamp": datetime.now().isoformat(),
            "optimization_results": optimization_results,
            "cache_optimization": cache_optimization,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "message": "System optimization cycle failed",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "failed"
        }

# Initialize monitoring service on startup
@app.on_event("startup")
async def initialize_monitoring():
    """Initialize monitoring service on startup"""
    try:
        # Initialize monitoring service
        monitoring = await get_monitoring_service()
        print("✅ 监控服务初始化完成")
        
        # Record startup metrics
        monitoring.metrics_collector.record_request(success=True, response_time_ms=0.0)
        
    except Exception as e:
        print(f"❌ 监控服务初始化失败: {e}")

@app.on_event("shutdown")
async def shutdown_monitoring():
    """Shutdown monitoring service"""
    try:
        # Get monitoring service and stop it
        monitoring = await get_monitoring_service()
        await monitoring.stop_monitoring()
        print("✅ 监控服务已关闭")
        
    except Exception as e:
        print(f"❌ 监控服务关闭失败: {e}")

# Middleware to record API metrics
@app.middleware("http")
async def record_api_metrics(request: Request, call_next):
    """Middleware to record API request metrics"""
    start_time = time.time()
    
    try:
        # Get monitoring service
        monitoring = await get_monitoring_service()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        success = 200 <= response.status_code < 400
        monitoring.metrics_collector.record_request(
            success=success,
            response_time_ms=response_time_ms
        )
        
        # Record Vision API calls if this was a Vision API endpoint
        if "/detect-objects" in str(request.url) or "/analyze" in str(request.url):
            monitoring.metrics_collector.record_vision_api_call()
        
        return response
        
    except Exception as e:
        # Record failed request
        response_time_ms = (time.time() - start_time) * 1000
        try:
            monitoring = await get_monitoring_service()
            monitoring.metrics_collector.record_request(
                success=False,
                response_time_ms=response_time_ms
            )
        except:
            pass  # Don't fail if monitoring fails
        
        # Re-raise the original exception
        raise e