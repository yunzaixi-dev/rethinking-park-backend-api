"""
图像分析相关API端点
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.core.error_monitoring import error_handler
from models.image import (
    EnhancedDetectionRequest,
    EnhancedDetectionResponse,
    HashAnalysisRequest,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    LabelAnalysisRequest,
    LabelAnalysisResponse,
    NaturalElementsRequest,
    NaturalElementsResponse,
    SimpleExtractionRequest,
    SimpleExtractionResponse,
)
from services.cache_service import cache_service
from services.enhanced_vision_service import enhanced_vision_service
from services.gcs_service import gcs_service
from services.image_processing_service import image_processing_service
from services.label_analysis_service import label_analysis_service
from services.natural_element_analyzer import natural_element_analyzer
from services.performance_optimizer import get_performance_optimizer
from services.rate_limiter import limiter, rate_limiter_service
from services.storage_service import storage_service
from services.vision_service import vision_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze", response_model=ImageAnalysisResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
@error_handler("analyze_image", reraise=True)
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
            cached_result = await cache_service.get_analysis_result(
                image_hash, analysis_type
            )
            if cached_result:
                return ImageAnalysisResponse(
                    image_hash=image_hash,
                    analysis_type=analysis_type,
                    results=cached_result["result"],
                    processed_time=datetime.fromisoformat(cached_result["cached_at"]),
                    success=True,
                    from_cache=True,
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
            image_content, analysis_type
        )

        # 缓存分析结果
        await cache_service.set_analysis_result(
            image_hash, analysis_type, analysis_results
        )

        # 更新存储的分析结果
        await storage_service.update_analysis_results(image_hash, analysis_results)

        return ImageAnalysisResponse(
            image_hash=image_hash,
            analysis_type=analysis_type,
            results=analysis_results,
            processed_time=datetime.now(),
            success=True,
            from_cache=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze-by-id", response_model=ImageAnalysisResponse)
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
            force_refresh=False,
        )

        return await analyze_image(request, hash_request)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/detect-objects-enhanced", response_model=EnhancedDetectionResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def detect_objects_enhanced(
    request: Request, detection_request: EnhancedDetectionRequest
):
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
            max_results=detection_request.max_results,
        )

        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, detection_response.dict(), ttl=3600  # Cache for 1 hour
        )

        return detection_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Enhanced detection failed: {str(e)}"
        )


@router.post("/extract-object-simple", response_model=SimpleExtractionResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def extract_object_simple(
    request: Request, extraction_request: SimpleExtractionRequest
):
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
            image_content,
            extraction_request.bounding_box,
            extraction_request.add_padding,
        )

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid extraction request: {'; '.join(validation_result['errors'])}",
            )

        # Perform simple object extraction
        extraction_result = image_processing_service.extract_by_bounding_box(
            image_content=image_content,
            bounding_box=extraction_request.bounding_box,
            padding=extraction_request.add_padding,
            output_format=extraction_request.output_format.upper(),
            background_removal=False,  # Simple extraction without background removal for now
        )

        # Upload extracted object to GCS
        extracted_filename = (
            f"extracted_{extraction_id}.{extraction_request.output_format.lower()}"
        )
        content_type = f"image/{extraction_request.output_format.lower()}"
        if extraction_request.output_format.lower() == "jpg":
            content_type = "image/jpeg"

        # Upload to GCS with a specific path for extracted objects
        extracted_image_id, extracted_hash, extracted_gcs_url, _ = (
            await gcs_service.upload_image(
                extraction_result.extracted_image_bytes,
                extracted_filename,
                content_type,
                folder_prefix="extracted/",
            )
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
            format=extraction_request.output_format.lower(),
        )

        response = SimpleExtractionResponse(
            image_hash=image_hash,
            extraction_id=extraction_id,
            result=response_result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None,
        )

        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, response.dict(), ttl=7200  # Cache for 2 hours
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
            error_message=f"Extraction failed: {str(e)}",
        )


@router.post("/analyze-by-labels", response_model=LabelAnalysisResponse)
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
            raise HTTPException(
                status_code=500, detail="Failed to get labels from Vision API"
            )

        # Filter labels by confidence threshold
        all_labels = labels_response["labels"]
        filtered_labels = [
            label
            for label in all_labels
            if label.get("confidence", 0) >= analysis_request.confidence_threshold
        ][: analysis_request.max_labels]

        # Perform label-based analysis
        analysis_result = label_analysis_service.analyze_by_labels(
            labels=filtered_labels,
            image_content=image_content,
            analysis_depth="comprehensive",
            include_confidence=analysis_request.include_confidence,
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
                total_confidence = sum(
                    label.get("confidence", 0) for label in matched_labels
                )
                average_confidence = total_confidence / len(matched_labels)
                coverage_estimate = min(
                    100.0, total_confidence * 20
                )  # Simple coverage estimation

                from models.image import LabelCategoryResult

                category_result = LabelCategoryResult(
                    category_name=target_category,
                    matched_labels=matched_labels,
                    total_confidence=total_confidence,
                    average_confidence=average_confidence,
                    coverage_estimate=coverage_estimate,
                    label_count=len(matched_labels),
                )
                category_results.append(category_result)

        # Extract coverage statistics
        coverage_stats = analysis_result.get("coverage_statistics", {})
        natural_elements_summary = {
            "vegetation": coverage_stats.get("vegetation_coverage", 0.0),
            "sky": coverage_stats.get("sky_coverage", 0.0),
            "water": coverage_stats.get("water_coverage", 0.0),
            "built_environment": coverage_stats.get("built_environment_coverage", 0.0),
        }

        # Create confidence distribution
        confidence_analysis = analysis_result.get("confidence_analysis", {})
        confidence_distribution = confidence_analysis.get(
            "confidence_distribution",
            {"high_confidence": 0, "medium_confidence": 0, "low_confidence": 0},
        )

        # Get top categories
        top_categories = sorted(
            natural_elements_summary.items(), key=lambda x: x[1], reverse=True
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
                "analysis_time": datetime.now().isoformat(),
            },
        )

        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response = LabelAnalysisResponse(
            image_hash=image_hash,
            results=result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None,
        )

        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, response.dict(), ttl=3600  # Cache for 1 hour
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
            error_message=f"Label analysis failed: {str(e)}",
        )


@router.post("/analyze-nature", response_model=NaturalElementsResponse)
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
                detail="Vision service is not available - Google Cloud credentials not found",
            )

        # Perform comprehensive natural elements analysis
        analysis_result = await natural_element_analyzer.analyze_natural_elements(
            image_content=image_content,
            vision_client=vision_service.client,
            analysis_depth=analysis_request.analysis_depth,
            include_health_assessment=analysis_request.include_health_assessment,
            include_seasonal_analysis=analysis_request.include_seasonal_analysis,
            include_color_analysis=analysis_request.include_color_analysis,
            confidence_threshold=analysis_request.confidence_threshold,
        )

        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response = NaturalElementsResponse(
            image_hash=image_hash,
            results=analysis_result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None,
        )

        # Cache the result for future requests
        await cache_service.set(
            cache_key, response.dict(), ttl=3600  # Cache for 1 hour
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
        )


@router.post("/detect-objects-optimized", response_model=EnhancedDetectionResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def detect_objects_optimized(
    request: Request, detection_request: EnhancedDetectionRequest
):
    """
    Performance-optimized object detection endpoint with batching and caching

    - Uses Google Vision API call batching for improved efficiency
    - Implements intelligent caching strategies for better performance
    - Optimizes memory usage and processing speed
    - Provides enhanced error handling and recovery
    """
    try:
        start_time = datetime.now()
        image_hash = detection_request.image_hash

        # Get performance optimizer
        optimizer = await get_performance_optimizer()

        # Check cache first with optimized cache key
        cache_key = f"optimized_detection:{image_hash}:{detection_request.confidence_threshold}:{detection_request.include_faces}:{detection_request.include_labels}"
        cached_result = await cache_service.get_cached_data(cache_key)

        if cached_result:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cached_response = EnhancedDetectionResponse(**cached_result)
            cached_response.from_cache = True
            cached_response.processing_time_ms = processing_time
            return cached_response

        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise HTTPException(status_code=404, detail="图像未找到")

        # Download image content from GCS with optimization
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise HTTPException(status_code=404, detail="无法获取图像内容")

        # Use optimized detection with performance enhancements
        detection_response = await optimizer.optimize_object_detection(
            image_content=image_content,
            image_hash=image_hash,
            include_faces=detection_request.include_faces,
            include_labels=detection_request.include_labels,
            confidence_threshold=detection_request.confidence_threshold,
            max_results=detection_request.max_results,
        )

        # Cache the result with extended TTL for optimized results
        await cache_service.set_cached_data(
            cache_key,
            detection_response.dict(),
            ttl=7200,  # Cache for 2 hours for optimized results
        )

        return detection_response

    except HTTPException:
        raise
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return EnhancedDetectionResponse(
            image_hash=detection_request.image_hash,
            objects=[],
            faces=[],
            labels=[],
            processing_time_ms=processing_time,
            success=False,
            enabled=True,
            error_message=f"Optimized detection failed: {str(e)}",
            metadata={},
            from_cache=False,
        )


@router.post("/analyze-nature-optimized", response_model=NaturalElementsResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def analyze_nature_optimized(
    request: Request, analysis_request: NaturalElementsRequest
):
    """
    Performance-optimized natural elements analysis with batching

    - Optimized Google Vision API call batching and caching
    - Enhanced performance through intelligent resource management
    - Memory usage optimization for image annotation processing
    - Async processing for batch operations
    """
    try:
        start_time = datetime.now()
        image_hash = analysis_request.image_hash

        # Get performance optimizer
        optimizer = await get_performance_optimizer()

        # Check cache first with optimized cache strategy
        cache_key = f"optimized_nature:{image_hash}:{analysis_request.analysis_depth}:{analysis_request.include_health_assessment}:{analysis_request.include_seasonal_analysis}:{analysis_request.include_color_analysis}:{analysis_request.confidence_threshold}"
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
                detail="Vision service is not available - Google Cloud credentials not found",
            )

        # Perform optimized natural elements analysis
        analysis_result = await optimizer.optimize_natural_elements_analysis(
            image_content=image_content,
            vision_client=vision_service.client,
            analysis_depth=analysis_request.analysis_depth,
            include_health_assessment=analysis_request.include_health_assessment,
            include_seasonal_analysis=analysis_request.include_seasonal_analysis,
            include_color_analysis=analysis_request.include_color_analysis,
            confidence_threshold=analysis_request.confidence_threshold,
        )

        # Create response with optimization metadata
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        response = NaturalElementsResponse(
            image_hash=image_hash,
            results=analysis_result,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            error_message=None,
            metadata={
                "analysis_depth": analysis_request.analysis_depth,
                "processing_time_ms": processing_time,
                "optimized": True,
            },
        )

        # Cache the result with extended TTL
        await cache_service.set(
            cache_key,
            response.dict(),
            ttl=7200,  # Cache for 2 hours for optimized results
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
            error_message=f"Optimized nature analysis failed: {str(e)}",
        )
