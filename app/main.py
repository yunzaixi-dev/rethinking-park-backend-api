"""
FastAPI应用入口点
"""

import logging
from datetime import datetime

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.config.settings import settings
from app.core.error_monitoring import get_error_stats, log_error, setup_logging
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middleware
from services.cache_service import cache_service
from services.gcs_service import gcs_service
from services.monitoring_service import get_monitoring_service
from services.performance_optimizer import get_performance_optimizer
from services.rate_limiter import limiter, rate_limiter_service


def create_application() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 配置好的FastAPI应用实例
    """
    # 创建FastAPI应用
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="智能公园图像分析API - 支持哈希去重、缓存和速率限制的Google Cloud Vision图像分析服务",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 设置中间件
    setup_middleware(app)

    # 设置异常处理器
    setup_exception_handlers(app)

    # 添加速率限制支持
    if settings.RATE_LIMIT_ENABLED:
        app.state.limiter = limiter
        app.add_exception_handler(
            RateLimitExceeded, rate_limiter_service.create_rate_limit_handler()
        )

    # 添加API路由
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # 添加根路径和健康检查
    setup_root_endpoints(app)

    # 设置启动和关闭事件
    setup_event_handlers(app)

    return app


def setup_root_endpoints(app: FastAPI):
    """设置根路径和健康检查端点"""

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
                "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            },
        }

    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        from services.storage_service import storage_service

        stats = await storage_service.get_stats()
        cache_stats = cache_service.get_stats()
        error_stats = get_error_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "storage_stats": stats,
            "cache_stats": cache_stats,
            "error_stats": error_stats,
        }

    @app.get("/errors/stats")
    async def error_statistics():
        """错误统计端点"""
        return {
            "timestamp": datetime.now().isoformat(),
            "error_statistics": get_error_stats(),
        }


def setup_event_handlers(app: FastAPI):
    """设置应用启动和关闭事件处理器"""

    @app.on_event("startup")
    async def startup_event():
        """应用启动时的初始化"""
        logger = logging.getLogger(__name__)

        try:
            # 初始化日志系统
            setup_logging(
                log_level=getattr(settings, "LOG_LEVEL", "INFO"),
                log_file=getattr(settings, "LOG_FILE", "logs/app.log"),
            )
            logger.info("✅ 错误监控和日志系统初始化完成")

            await gcs_service.initialize()
            logger.info("✅ Google Cloud Storage 初始化成功")

            await cache_service.initialize()
            logger.info("✅ 缓存服务初始化完成")

            # Initialize performance optimizer
            await get_performance_optimizer()
            logger.info("✅ 性能优化器初始化完成")

            # Initialize monitoring service
            monitoring = await get_monitoring_service()
            logger.info("✅ 监控服务初始化完成")

            # Record startup metrics
            monitoring.metrics_collector.record_request(
                success=True, response_time_ms=0.0
            )

            logger.info("🚀 应用启动完成")

        except Exception as e:
            logger.error(f"❌ 服务初始化失败: {e}", exc_info=True)
            log_error(logger, e, {"phase": "startup"}, "Application startup failed")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时的清理"""
        try:
            # Shutdown performance optimizer
            optimizer = await get_performance_optimizer()
            await optimizer.shutdown()
            print("✅ 性能优化器已关闭")

            # Shutdown monitoring service
            monitoring = await get_monitoring_service()
            await monitoring.stop_monitoring()
            print("✅ 监控服务已关闭")

            await cache_service.close()
            print("✅ 缓存服务已关闭")
        except Exception as e:
            print(f"❌ 服务关闭失败: {e}")


# 创建应用实例
app = create_application()
