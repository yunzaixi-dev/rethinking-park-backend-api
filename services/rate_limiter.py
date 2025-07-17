import time
from typing import Any, Dict

from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


class RateLimiterService:
    """速率限制服务"""

    def __init__(self):
        # 创建limiter实例
        self.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[
                "100/hour",
                "20/minute",
            ],  # 默认限制：每小时100次，每分钟20次
        )

        # 不同API端点的具体限制
        self.api_limits = {
            "upload": "10/minute",  # 上传API：每分钟10次
            "analyze": "5/minute",  # 分析API：每分钟5次（Vision API比较昂贵）
            "list": "30/minute",  # 列表API：每分钟30次
            "delete": "5/minute",  # 删除API：每分钟5次
            "batch": "2/minute",  # 批处理API：每分钟2次（资源密集型）
            "status": "60/minute",  # 状态查询API：每分钟60次
        }

    def get_limiter(self):
        """获取limiter实例"""
        return self.limiter

    def get_limit_for_endpoint(self, endpoint: str) -> str:
        """获取特定端点的限制"""
        return self.api_limits.get(endpoint, "20/minute")

    def create_rate_limit_handler(self):
        """创建速率限制异常处理器"""

        async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
            response = {
                "error": "rate_limit_exceeded",
                "message": f"请求过于频繁，请稍后再试",
                "details": {
                    "limit": str(exc.detail),
                    "retry_after": exc.retry_after,
                    "timestamp": time.time(),
                },
            }
            raise HTTPException(status_code=429, detail=response)

        return rate_limit_handler


# 创建全局实例
rate_limiter_service = RateLimiterService()
limiter = rate_limiter_service.get_limiter()
