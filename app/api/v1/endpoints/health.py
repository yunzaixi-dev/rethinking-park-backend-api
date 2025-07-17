"""
健康检查和监控相关API端点
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from services.cache_service import cache_service
from services.monitoring_service import get_monitoring_service
from services.performance_optimizer import get_performance_optimizer
from services.rate_limiter import limiter, rate_limiter_service
from services.storage_service import storage_service
from services.vision_service import vision_service

router = APIRouter()


@router.get("/detailed")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_detailed_health_status(request: Request):
    """
    Get detailed health status of all system components

    - Checks status of all critical services
    - Returns detailed health information
    - Includes performance metrics and resource usage
    """
    try:
        # Check storage service health
        storage_stats = await storage_service.get_stats()
        storage_healthy = storage_stats.get("status") == "healthy"

        # Check cache service health
        cache_stats = cache_service.get_stats()
        cache_healthy = cache_stats.get("status") == "healthy"

        # Check vision service health
        vision_healthy = vision_service.is_enabled()

        # Get monitoring service status
        monitoring = await get_monitoring_service()
        monitoring_healthy = monitoring.is_running()

        # Overall health status
        overall_healthy = all(
            [storage_healthy, cache_healthy, vision_healthy, monitoring_healthy]
        )

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "storage": {
                    "status": "healthy" if storage_healthy else "unhealthy",
                    "stats": storage_stats,
                },
                "cache": {
                    "status": "healthy" if cache_healthy else "unhealthy",
                    "stats": cache_stats,
                },
                "vision": {
                    "status": "healthy" if vision_healthy else "unhealthy",
                    "enabled": vision_healthy,
                },
                "monitoring": {
                    "status": "healthy" if monitoring_healthy else "unhealthy",
                    "running": monitoring_healthy,
                },
            },
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


@router.get("/metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_system_metrics(request: Request):
    """
    Get comprehensive system metrics

    - Returns performance metrics from all services
    - Includes resource usage statistics
    - Provides system health indicators
    """
    try:
        # Get monitoring service
        monitoring = await get_monitoring_service()

        # Collect metrics from all services
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "api_metrics": monitoring.get_api_metrics(),
            "storage_metrics": await storage_service.get_stats(),
            "cache_metrics": cache_service.get_stats(),
            "system_metrics": {
                "uptime": monitoring.get_uptime(),
                "memory_usage": monitoring.get_memory_usage(),
                "cpu_usage": monitoring.get_cpu_usage(),
            },
        }

        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system metrics: {str(e)}"
        )


@router.get("/vision-api-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_vision_api_metrics(request: Request):
    """
    Get Google Vision API usage metrics

    - Returns Vision API call statistics
    - Includes quota usage and rate limiting info
    - Provides performance metrics for Vision API calls
    """
    try:
        # Get monitoring service
        monitoring = await get_monitoring_service()

        # Get Vision API specific metrics
        vision_metrics = monitoring.get_vision_api_metrics()

        # Add current Vision API status
        vision_status = {
            "enabled": vision_service.is_enabled(),
            "quota_remaining": (
                vision_service.get_quota_remaining()
                if hasattr(vision_service, "get_quota_remaining")
                else None
            ),
            "rate_limit_status": (
                vision_service.get_rate_limit_status()
                if hasattr(vision_service, "get_rate_limit_status")
                else None
            ),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "vision_api_status": vision_status,
            "metrics": vision_metrics,
            "performance": {
                "average_response_time": vision_metrics.get(
                    "average_response_time_ms", 0
                ),
                "success_rate": vision_metrics.get("success_rate", 0),
                "total_calls": vision_metrics.get("total_calls", 0),
                "failed_calls": vision_metrics.get("failed_calls", 0),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Vision API metrics: {str(e)}"
        )


@router.get("/cache-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_cache_metrics(request: Request):
    """
    Get cache system metrics

    - Returns cache hit/miss statistics
    - Includes memory usage and performance metrics
    - Provides cache optimization recommendations
    """
    try:
        # Get cache statistics
        cache_stats = cache_service.get_stats()

        # Get detailed cache metrics
        detailed_metrics = {
            "timestamp": datetime.now().isoformat(),
            "basic_stats": cache_stats,
            "performance": {
                "hit_rate": cache_stats.get("hit_rate", 0),
                "miss_rate": cache_stats.get("miss_rate", 0),
                "average_get_time_ms": cache_stats.get("average_get_time_ms", 0),
                "average_set_time_ms": cache_stats.get("average_set_time_ms", 0),
            },
            "memory": {
                "used_memory": cache_stats.get("used_memory", 0),
                "max_memory": cache_stats.get("max_memory", 0),
                "memory_usage_percentage": cache_stats.get(
                    "memory_usage_percentage", 0
                ),
            },
            "operations": {
                "total_gets": cache_stats.get("total_gets", 0),
                "total_sets": cache_stats.get("total_sets", 0),
                "total_deletes": cache_stats.get("total_deletes", 0),
                "total_evictions": cache_stats.get("total_evictions", 0),
            },
        }

        # Add optimization recommendations
        if cache_stats.get("hit_rate", 0) < 0.7:
            detailed_metrics["recommendations"] = [
                "Consider increasing cache TTL for frequently accessed data",
                "Review cache key patterns for optimization opportunities",
            ]

        if cache_stats.get("memory_usage_percentage", 0) > 0.8:
            detailed_metrics["recommendations"] = detailed_metrics.get(
                "recommendations", []
            ) + [
                "Consider increasing cache memory limit",
                "Implement more aggressive cache eviction policies",
            ]

        return detailed_metrics

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache metrics: {str(e)}"
        )


@router.get("/batch-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_batch_processing_metrics(request: Request):
    """
    Get batch processing metrics

    - Returns batch job statistics and performance metrics
    - Includes queue status and processing rates
    - Provides batch processing optimization insights
    """
    try:
        from services.batch_processing_service import batch_processing_service

        # Get batch processing statistics
        batch_stats = await batch_processing_service.get_batch_statistics()

        # Get current queue status
        queue_status = await batch_processing_service.get_queue_status()

        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": batch_stats,
            "queue_status": queue_status,
            "performance": {
                "average_job_completion_time": batch_stats.get(
                    "average_processing_time_ms", 0
                ),
                "throughput_per_hour": batch_stats.get("throughput_per_hour", 0),
                "success_rate": batch_stats.get("success_rate", 0),
                "current_load": queue_status.get("current_load", 0),
            },
            "resource_usage": {
                "active_workers": queue_status.get("active_workers", 0),
                "max_workers": queue_status.get("max_workers", 0),
                "queue_length": queue_status.get("queue_length", 0),
                "memory_usage": queue_status.get("memory_usage", 0),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch processing metrics: {str(e)}"
        )


@router.get("/stats")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_stats(request: Request):
    """获取系统统计信息"""
    storage_stats = await storage_service.get_stats()
    cache_stats = cache_service.get_stats()

    from app.config.settings import settings

    return {
        "storage": storage_stats,
        "cache": cache_stats,
        "system": {
            "duplicate_detection": settings.ENABLE_DUPLICATE_DETECTION,
            "cache_enabled": settings.REDIS_ENABLED,
            "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        },
    }
