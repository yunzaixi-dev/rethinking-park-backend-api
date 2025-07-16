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
    NaturalElementsResponse
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