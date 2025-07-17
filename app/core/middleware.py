"""
中间件配置模块
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from services.monitoring_service import get_monitoring_service


def setup_middleware(app: FastAPI):
    """
    设置应用中间件

    Args:
        app: FastAPI应用实例
    """
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加API指标记录中间件
    app.middleware("http")(record_api_metrics)


async def record_api_metrics(request: Request, call_next):
    """
    记录API请求指标的中间件

    Args:
        request: HTTP请求对象
        call_next: 下一个中间件或路由处理器

    Returns:
        HTTP响应对象
    """
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
            success=success, response_time_ms=response_time_ms
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
                success=False, response_time_ms=response_time_ms
            )
        except:
            pass  # Don't fail if monitoring fails

        # Re-raise the original exception
        raise e
