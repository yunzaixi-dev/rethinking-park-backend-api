"""
批处理相关API端点
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from models.image import (
    BatchJobStatus,
    BatchProcessingRequest,
    BatchProcessingResponse,
    BatchResultsResponse,
)
from services.batch_processing_service import batch_processing_service
from services.performance_optimizer import get_performance_optimizer
from services.rate_limiter import limiter, rate_limiter_service

router = APIRouter()


@router.post("/process", response_model=BatchProcessingResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("batch"))
async def create_batch_job(request: Request, batch_request: BatchProcessingRequest):
    """
    Create a new batch processing job

    - Processes multiple images in a single request
    - Supports various analysis types (labels, objects, faces, etc.)
    - Returns batch job ID for status tracking
    - Implements queue-based processing for scalability
    """
    try:
        # Validate batch request
        if not batch_request.image_hashes:
            raise HTTPException(status_code=400, detail="No image hashes provided")

        if len(batch_request.image_hashes) > batch_request.max_concurrent_jobs:
            raise HTTPException(
                status_code=400,
                detail=f"Too many images. Maximum allowed: {batch_request.max_concurrent_jobs}",
            )

        # Create batch processing job
        batch_job = await batch_processing_service.create_batch_job(
            image_hashes=batch_request.image_hashes,
            analysis_types=batch_request.analysis_types,
            processing_options=batch_request.processing_options,
            priority=batch_request.priority,
            callback_url=batch_request.callback_url,
            max_concurrent_jobs=batch_request.max_concurrent_jobs,
            timeout_seconds=batch_request.timeout_seconds,
        )

        # Start processing the batch job
        await batch_processing_service.start_batch_processing(batch_job.batch_id)

        return BatchProcessingResponse(
            batch_id=batch_job.batch_id,
            status=batch_job.status,
            total_images=len(batch_request.image_hashes),
            processed_images=0,
            failed_images=0,
            estimated_completion_time=batch_job.estimated_completion_time,
            created_at=batch_job.created_at,
            processing_options=batch_request.processing_options,
            success=True,
            message="Batch job created and started successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Batch processing failed: {str(e)}"
        )


@router.get("/process/{batch_id}/status", response_model=BatchJobStatus)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def get_batch_status(request: Request, batch_id: str):
    """
    Get batch processing job status

    - Returns current status of batch processing job
    - Includes progress information and timing estimates
    - Provides detailed error information if job failed
    """
    try:
        # Get batch job status
        batch_status = await batch_processing_service.get_batch_status(batch_id)

        if not batch_status:
            raise HTTPException(status_code=404, detail="Batch job not found")

        # Calculate progress percentage
        total_images = batch_status.total_images
        processed_images = batch_status.processed_images
        progress_percentage = (
            (processed_images / total_images * 100) if total_images > 0 else 0
        )

        return BatchJobStatus(
            batch_id=batch_id,
            status=batch_status.status,
            total_images=total_images,
            processed_images=processed_images,
            failed_images=batch_status.failed_images,
            progress_percentage=progress_percentage,
            estimated_completion_time=batch_status.estimated_completion_time,
            actual_completion_time=batch_status.actual_completion_time,
            created_at=batch_status.created_at,
            started_at=batch_status.started_at,
            error_message=batch_status.error_message,
            processing_details={
                "current_image": batch_status.current_image_hash,
                "average_processing_time": batch_status.average_processing_time_ms,
                "remaining_images": total_images - processed_images,
                "success_rate": (
                    (processed_images - batch_status.failed_images)
                    / processed_images
                    * 100
                    if processed_images > 0
                    else 0
                ),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch status: {str(e)}"
        )


@router.get("/process/{batch_id}/results", response_model=BatchResultsResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def get_batch_results(request: Request, batch_id: str):
    """
    Get batch processing results

    - Returns detailed results for completed batch job
    - Includes individual image analysis results
    - Provides summary statistics and performance metrics
    """
    try:
        # Get batch results
        batch_results = await batch_processing_service.get_batch_results(batch_id)

        if not batch_results:
            raise HTTPException(status_code=404, detail="Batch results not found")

        return BatchResultsResponse(
            batch_id=batch_id,
            status=batch_results.status,
            results=batch_results.results,
            summary_statistics=batch_results.summary_statistics,
            performance_metrics=batch_results.performance_metrics,
            created_at=batch_results.created_at,
            completed_at=batch_results.completed_at,
            total_processing_time_ms=batch_results.total_processing_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch results: {str(e)}"
        )


@router.delete("/process/{batch_id}")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def cancel_batch_job(request: Request, batch_id: str):
    """
    Cancel a batch processing job

    - Stops processing of pending images in the batch
    - Returns partial results for already processed images
    - Cleans up resources associated with the batch job
    """
    try:
        # Cancel batch job
        cancellation_result = await batch_processing_service.cancel_batch_job(batch_id)

        if not cancellation_result:
            raise HTTPException(status_code=404, detail="Batch job not found")

        return {
            "message": f"Batch job {batch_id} cancelled successfully",
            "cancelled_at": datetime.now().isoformat(),
            "processed_images": cancellation_result.get("processed_images", 0),
            "cancelled_images": cancellation_result.get("cancelled_images", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel batch job: {str(e)}"
        )


@router.get("/statistics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("status"))
async def get_batch_statistics(request: Request):
    """
    Get batch processing statistics

    - Returns overall batch processing statistics
    - Includes performance metrics and usage patterns
    - Provides insights for system optimization
    """
    try:
        # Get batch processing statistics
        stats = await batch_processing_service.get_batch_statistics()

        return {
            "total_batch_jobs": stats.get("total_batch_jobs", 0),
            "completed_jobs": stats.get("completed_jobs", 0),
            "failed_jobs": stats.get("failed_jobs", 0),
            "active_jobs": stats.get("active_jobs", 0),
            "total_images_processed": stats.get("total_images_processed", 0),
            "average_processing_time_ms": stats.get("average_processing_time_ms", 0),
            "success_rate": stats.get("success_rate", 0),
            "peak_concurrent_jobs": stats.get("peak_concurrent_jobs", 0),
            "resource_utilization": stats.get("resource_utilization", {}),
            "performance_trends": stats.get("performance_trends", {}),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch statistics: {str(e)}"
        )


@router.post("/process-optimized", response_model=BatchProcessingResponse)
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("batch"))
async def batch_process_optimized(
    request: Request, batch_request: BatchProcessingRequest
):
    """
    Optimized batch processing with performance enhancements

    - Uses performance optimizer for resource management
    - Implements intelligent job scheduling and load balancing
    - Provides enhanced error handling and recovery
    - Optimizes memory usage and processing speed
    """
    try:
        # Get performance optimizer
        optimizer = await get_performance_optimizer()

        # Optimize batch processing parameters
        optimized_params = await optimizer.optimize_batch_processing(
            image_count=len(batch_request.image_hashes),
            analysis_types=batch_request.analysis_types,
            current_load=await batch_processing_service.get_current_load(),
        )

        # Update batch request with optimized parameters
        batch_request.max_concurrent_jobs = optimized_params.get(
            "max_concurrent_jobs", batch_request.max_concurrent_jobs
        )
        batch_request.timeout_seconds = optimized_params.get(
            "timeout_seconds", batch_request.timeout_seconds
        )

        # Create and start optimized batch job
        batch_job = await batch_processing_service.create_optimized_batch_job(
            image_hashes=batch_request.image_hashes,
            analysis_types=batch_request.analysis_types,
            processing_options=batch_request.processing_options,
            optimization_params=optimized_params,
            priority=batch_request.priority,
            callback_url=batch_request.callback_url,
        )

        return BatchProcessingResponse(
            batch_id=batch_job.batch_id,
            status=batch_job.status,
            total_images=len(batch_request.image_hashes),
            processed_images=0,
            failed_images=0,
            estimated_completion_time=batch_job.estimated_completion_time,
            created_at=batch_job.created_at,
            processing_options=batch_request.processing_options,
            success=True,
            message="Optimized batch job created and started successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Optimized batch processing failed: {str(e)}"
        )
