"""
图像相关API端点
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.error_monitoring import error_context, error_handler, log_error
from app.core.exceptions import (
    ImageNotFoundError,
    ProcessingError,
    StorageError,
    ValidationError,
)
from models.image import (
    AnnotatedImageRequest,
    AnnotatedImageResponse,
    DuplicateCheckResponse,
    ImageInfo,
    ImageUploadResponse,
)
from services.cache_service import cache_service
from services.gcs_service import gcs_service
from services.hash_service import hash_service
from services.image_annotation_service import image_annotation_service
from services.rate_limiter import limiter, rate_limiter_service
from services.storage_service import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=ImageUploadResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("upload"))
@error_handler("upload_image", reraise=True)
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
        is_valid, validation_message = gcs_service.validate_image(
            file_content, file.filename
        )
        if not is_valid:
            raise ValidationError(validation_message)

        # 计算图像哈希
        md5_hash, perceptual_hash = hash_service.calculate_combined_hash(file_content)

        # 检查重复图像
        duplicate_check = await storage_service.check_duplicates(
            md5_hash, perceptual_hash
        )

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
                    similar_images=[
                        img["image_hash"] for img in duplicate_check.similar_images
                    ],
                )

        # 上传到GCS
        image_id, image_hash, gcs_url, _ = await gcs_service.upload_image(
            file_content, file.filename, file.content_type
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
            processed=False,
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
            similar_images=[
                img["image_hash"] for img in duplicate_check.similar_images
            ],
        )

    except (ValidationError, StorageError, ProcessingError):
        # Re-raise our custom exceptions - they will be handled by the unified exception handler
        raise
    except Exception as e:
        log_error(logger, e, {"operation": "upload_image", "filename": file.filename})
        raise ProcessingError(f"Image upload failed: {str(e)}", operation="upload")


@router.get("/{image_hash}", response_model=ImageInfo)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
@error_handler("get_image_info_by_hash", reraise=True)
async def get_image_info_by_hash(request: Request, image_hash: str):
    """根据哈希值获取图像信息"""
    image_info = await storage_service.get_image_info_by_hash(image_hash)
    if not image_info:
        raise ImageNotFoundError(image_hash=image_hash)
    return image_info


@router.get("/check-duplicate/{image_hash}", response_model=DuplicateCheckResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def check_duplicate(request: Request, image_hash: str):
    """检查图像是否重复"""
    # 首先尝试获取图像信息以获取感知哈希
    image_info = await storage_service.get_image_info_by_hash(image_hash)
    perceptual_hash = image_info.perceptual_hash if image_info else None

    return await storage_service.check_duplicates(image_hash, perceptual_hash)


@router.get("/", response_model=List[ImageInfo])
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def list_images(
    request: Request,
    limit: int = Query(default=10, le=100, description="返回的图像数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
):
    """列出图像"""
    return await storage_service.list_images(limit=limit, offset=offset)


@router.delete("/{image_hash}")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("delete"))
@error_handler("delete_image_by_hash", reraise=True)
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
            raise ImageNotFoundError(image_hash=image_hash)

    except (ImageNotFoundError, StorageError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        log_error(logger, e, {"operation": "delete_image", "image_hash": image_hash})
        raise ProcessingError(f"Image deletion failed: {str(e)}", operation="delete")


@router.post("/download-annotated", response_model=AnnotatedImageResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("analyze"))
async def download_annotated(
    request: Request, annotation_request: AnnotatedImageRequest
):
    """
    Download annotated image with bounding boxes and labels

    - Draws bounding boxes around detected objects
    - Adds labels and confidence scores
    - Supports customizable annotation styles
    - Returns annotated image URL and metadata
    """
    try:
        start_time = datetime.now()
        image_hash = annotation_request.image_hash

        # Check cache first
        cache_key = (
            f"annotated_image:{image_hash}:{hash(str(annotation_request.dict()))}"
        )
        cached_result = await cache_service.get_cached_data(cache_key)

        if cached_result and not annotation_request.force_refresh:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            cached_response = AnnotatedImageResponse(**cached_result)
            cached_response.from_cache = True
            cached_response.processing_time_ms = processing_time
            return cached_response

        # Get image information
        image_info = await storage_service.get_image_info_by_hash(image_hash)
        if not image_info:
            raise ImageNotFoundError(image_hash=image_hash)

        # Download image content from GCS
        image_content = await gcs_service.download_image(image_hash)
        if not image_content:
            raise StorageError("Unable to retrieve image content from storage")

        # Create annotated image
        annotation_result = await image_annotation_service.create_annotated_image(
            image_content=image_content,
            image_hash=image_hash,
            annotation_types=annotation_request.annotation_types,
            style_options=annotation_request.style_options,
            confidence_threshold=annotation_request.confidence_threshold,
            max_annotations=annotation_request.max_annotations,
        )

        # Upload annotated image to GCS
        annotated_filename = f"annotated_{image_hash[:8]}_{uuid.uuid4().hex[:8]}.png"
        annotated_image_id, annotated_hash, annotated_gcs_url, _ = (
            await gcs_service.upload_image(
                annotation_result.annotated_image_bytes,
                annotated_filename,
                "image/png",
                folder_prefix="annotated/",
            )
        )

        # Create response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        response = AnnotatedImageResponse(
            image_hash=image_hash,
            annotated_image_url=annotated_gcs_url,
            annotation_count=annotation_result.annotation_count,
            annotation_types_applied=annotation_result.annotation_types_applied,
            style_options_used=annotation_request.style_options,
            processing_time_ms=processing_time,
            success=True,
            from_cache=False,
            metadata={
                "original_image_size": annotation_result.original_image_size,
                "annotated_image_size": len(annotation_result.annotated_image_bytes),
                "confidence_threshold": annotation_request.confidence_threshold,
                "max_annotations": annotation_request.max_annotations,
                "processing_timestamp": datetime.now().isoformat(),
            },
        )

        # Cache the result for future requests
        await cache_service.set_cached_data(
            cache_key, response.dict(), ttl=3600  # Cache for 1 hour
        )

        return response

    except (ImageNotFoundError, StorageError, ProcessingError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        log_error(
            logger,
            e,
            {
                "operation": "download_annotated",
                "image_hash": annotation_request.image_hash,
            },
        )
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return AnnotatedImageResponse(
            image_hash=annotation_request.image_hash,
            annotated_image_url="",
            annotation_count=0,
            annotation_types_applied=[],
            style_options_used=annotation_request.style_options,
            processing_time_ms=processing_time,
            success=False,
            from_cache=False,
            metadata={"error": str(e)},
        )
