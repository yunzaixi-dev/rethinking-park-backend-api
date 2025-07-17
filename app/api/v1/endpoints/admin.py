"""
管理员相关API端点
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from services.cache_service import cache_service
from services.monitoring_service import get_monitoring_service
from services.performance_optimizer import get_performance_optimizer
from services.rate_limiter import limiter, rate_limiter_service

router = APIRouter()


@router.get("/performance-metrics")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("list"))
async def get_performance_metrics(request: Request):
    """
    Get comprehensive performance metrics

    - Returns detailed performance statistics
    - Includes optimization recommendations
    - Provides system health insights
    """
    try:
        # Get performance optimizer
        optimizer = await get_performance_optimizer()

        # Get performance metrics
        metrics = await optimizer.get_performance_metrics()

        # Get monitoring service for additional metrics
        monitoring = await get_monitoring_service()
        monitoring_metrics = monitoring.get_comprehensive_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "performance_metrics": metrics,
            "monitoring_metrics": monitoring_metrics,
            "optimization_recommendations": await optimizer.get_optimization_recommendations(),
            "system_health": {
                "cpu_usage": monitoring.get_cpu_usage(),
                "memory_usage": monitoring.get_memory_usage(),
                "disk_usage": monitoring.get_disk_usage(),
                "network_usage": monitoring.get_network_usage(),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.post("/optimize-performance")
@limiter.limit(rate_limiter_service.get_limit_for_endpoint("admin"))
async def trigger_performance_optimization(request: Request):
    """
    Manually trigger performance optimization

    - Runs comprehensive system optimization
    - Clears unnecessary caches and optimizes memory usage
    - Returns optimization results and recommendations
    """
    try:
        # Get performance optimizer
        optimizer = await get_performance_optimizer()

        # Run optimization cycle
        optimization_results = await optimizer.perform_optimization_cycle()

        return {
            "message": "Performance optimization completed successfully",
            "timestamp": datetime.now().isoformat(),
            "optimization_results": optimization_results,
            "status": "success",
        }

    except Exception as e:
        return {
            "message": "Performance optimization failed",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "failed",
        }


@router.post("/trigger-optimization")
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
        if cache_service.is_enabled() and hasattr(
            cache_service, "implement_lru_eviction"
        ):
            cache_optimization = await cache_service.implement_lru_eviction(
                max_memory_mb=100
            )

        return {
            "message": "System optimization cycle completed successfully",
            "timestamp": datetime.now().isoformat(),
            "optimization_results": optimization_results,
            "cache_optimization": cache_optimization,
            "status": "success",
        }

    except Exception as e:
        return {
            "message": "System optimization cycle failed",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "failed",
        }
