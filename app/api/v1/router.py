"""
API v1 路由聚合器
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, analysis, batch, health, images

api_router = APIRouter()

# 包含各个功能模块的路由
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(batch.router, prefix="/batch", tags=["batch"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
