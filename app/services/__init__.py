"""
服务模块

This module provides the service layer architecture including:
- Base service classes
- Service registry and dependency injection
- Service lifecycle management
"""

from .base import (
    AsyncService,
    BaseService,
    CacheableService,
    ServiceConfig,
    ServiceHealth,
    ServiceRegistry,
    ServiceStatus,
    get_service,
    get_service_by_type,
    register_service,
    service_registry,
)
from .dependencies import (
    DependencyInjector,
    ServiceProvider,
    create_service_dependency,
)
from .dependencies import get_service as get_injected_service
from .dependencies import (
    get_service_registry,
    inject,
    injector,
    with_services,
)

__all__ = [
    # Base classes
    "BaseService",
    "AsyncService",
    "CacheableService",
    "ServiceConfig",
    "ServiceHealth",
    "ServiceStatus",
    # Registry
    "ServiceRegistry",
    "service_registry",
    "get_service",
    "get_service_by_type",
    "register_service",
    # Dependency injection
    "DependencyInjector",
    "ServiceProvider",
    "injector",
    "inject",
    "get_injected_service",
    "create_service_dependency",
    "with_services",
    "get_service_registry",
]
