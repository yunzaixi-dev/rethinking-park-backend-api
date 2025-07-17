"""
Base service classes and interfaces for the application.

This module provides the foundation for all services in the application,
including common functionality like logging, error handling, and dependency injection.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from app.core.exceptions import ServiceError, ServiceNotAvailableError

# Type variable for service types
T = TypeVar("T")


@dataclass
class ServiceConfig:
    """Configuration for services"""

    name: str
    enabled: bool = True
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    health_check_interval: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceStatus:
    """Service status tracking"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ServiceHealth:
    """Service health information"""

    status: str
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseService(ABC):
    """
    Abstract base class for all services.

    Provides common functionality including:
    - Logging
    - Error handling
    - Health checking
    - Configuration management
    - Lifecycle management
    """

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self._health = ServiceHealth(
            status=ServiceStatus.STOPPED, last_check=datetime.now()
        )
        self._initialized = False
        self._lock = None  # Will be initialized in async context

    @property
    def name(self) -> str:
        """Service name"""
        return self.config.name

    @property
    def enabled(self) -> bool:
        """Whether service is enabled"""
        return self.config.enabled

    @property
    def health(self) -> ServiceHealth:
        """Current service health"""
        return self._health

    async def initialize(self) -> None:
        """Initialize the service"""
        if self._initialized:
            return

        # Initialize lock if not already done
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._initialized:
                return

            try:
                self._health.status = ServiceStatus.STARTING
                self.logger.info(f"Initializing service: {self.name}")

                await self._initialize()

                self._initialized = True
                self._health.status = ServiceStatus.HEALTHY
                self._health.last_check = datetime.now()
                self._health.error_message = None

                self.logger.info(f"Service initialized successfully: {self.name}")

            except Exception as e:
                self._health.status = ServiceStatus.UNHEALTHY
                self._health.error_message = str(e)
                self._health.last_check = datetime.now()

                self.logger.error(f"Failed to initialize service {self.name}: {e}")
                raise ServiceError(f"Service initialization failed: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the service"""
        if not self._initialized:
            return

        # Initialize lock if not already done
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if not self._initialized:
                return

            try:
                self._health.status = ServiceStatus.STOPPING
                self.logger.info(f"Shutting down service: {self.name}")

                await self._shutdown()

                self._initialized = False
                self._health.status = ServiceStatus.STOPPED
                self._health.last_check = datetime.now()
                self._health.error_message = None

                self.logger.info(f"Service shutdown successfully: {self.name}")

            except Exception as e:
                self._health.status = ServiceStatus.UNHEALTHY
                self._health.error_message = str(e)
                self._health.last_check = datetime.now()

                self.logger.error(f"Failed to shutdown service {self.name}: {e}")
                raise ServiceError(f"Service shutdown failed: {e}") from e

    async def health_check(self) -> ServiceHealth:
        """Perform health check"""
        try:
            if not self._initialized:
                self._health.status = ServiceStatus.STOPPED
                self._health.error_message = "Service not initialized"
            else:
                await self._health_check()
                if self._health.status != ServiceStatus.UNHEALTHY:
                    self._health.status = ServiceStatus.HEALTHY
                    self._health.error_message = None

            self._health.last_check = datetime.now()

        except Exception as e:
            self._health.status = ServiceStatus.UNHEALTHY
            self._health.error_message = str(e)
            self._health.last_check = datetime.now()
            self.logger.error(f"Health check failed for service {self.name}: {e}")

        return self._health

    @asynccontextmanager
    async def ensure_initialized(self):
        """Context manager to ensure service is initialized"""
        if not self.enabled:
            raise ServiceNotAvailableError(f"Service {self.name} is disabled")

        if not self._initialized:
            await self.initialize()

        if self._health.status == ServiceStatus.UNHEALTHY:
            raise ServiceNotAvailableError(
                f"Service {self.name} is unhealthy: {self._health.error_message}"
            )

        try:
            yield self
        except Exception as e:
            self.logger.error(f"Error in service {self.name}: {e}")
            raise

    def log_operation(self, operation: str, **kwargs):
        """Log service operation"""
        self.logger.info(f"Service {self.name} - {operation}", extra=kwargs)

    def log_error(self, operation: str, error: Exception, **kwargs):
        """Log service error"""
        self.logger.error(
            f"Service {self.name} - {operation} failed: {error}", extra=kwargs
        )

    @abstractmethod
    async def _initialize(self) -> None:
        """Service-specific initialization logic"""
        pass

    async def _shutdown(self) -> None:
        """Service-specific shutdown logic (optional override)"""
        pass

    async def _health_check(self) -> None:
        """Service-specific health check logic (optional override)"""
        pass


class AsyncService(BaseService):
    """Base class for asynchronous services"""

    async def execute_with_timeout(self, coro, timeout: Optional[float] = None):
        """Execute coroutine with timeout"""
        timeout = timeout or self.config.timeout
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise ServiceError(f"Operation timed out after {timeout} seconds")


class CacheableService(AsyncService):
    """Base class for services that support caching"""

    def __init__(self, config: ServiceConfig, cache_service=None):
        super().__init__(config)
        self.cache_service = cache_service

    def get_cache_key(self, operation: str, **params) -> str:
        """Generate cache key for operation"""
        import hashlib
        import json

        key_data = {"service": self.name, "operation": operation, "params": params}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result"""
        if not self.cache_service:
            return None

        try:
            return await self.cache_service.get(cache_key)
        except Exception as e:
            self.logger.warning(f"Cache get failed: {e}")
            return None

    async def cache_result(
        self, cache_key: str, result: Any, ttl: Optional[int] = None
    ):
        """Cache operation result"""
        if not self.cache_service:
            return

        try:
            await self.cache_service.set(cache_key, result, ttl=ttl)
        except Exception as e:
            self.logger.warning(f"Cache set failed: {e}")


class ServiceRegistry:
    """Registry for managing service instances and dependencies"""

    def __init__(self):
        self._services: Dict[str, BaseService] = {}
        self._service_types: Dict[Type, str] = {}
        self._dependencies: Dict[str, List[str]] = {}

    def register(self, service: BaseService, dependencies: Optional[List[str]] = None):
        """Register a service"""
        service_name = service.name
        service_type = type(service)

        self._services[service_name] = service
        self._service_types[service_type] = service_name
        self._dependencies[service_name] = dependencies or []

        logging.getLogger(__name__).info(f"Registered service: {service_name}")

    def get(self, service_name: str) -> Optional[BaseService]:
        """Get service by name"""
        return self._services.get(service_name)

    def get_by_type(self, service_type: Type[T]) -> Optional[T]:
        """Get service by type"""
        service_name = self._service_types.get(service_type)
        if service_name:
            return self._services.get(service_name)
        return None

    def list_services(self) -> List[str]:
        """List all registered services"""
        return list(self._services.keys())

    async def initialize_all(self):
        """Initialize all services in dependency order"""
        initialized = set()

        async def init_service(service_name: str):
            if service_name in initialized:
                return

            # Initialize dependencies first
            for dep_name in self._dependencies.get(service_name, []):
                await init_service(dep_name)

            service = self._services.get(service_name)
            if service and service.enabled:
                await service.initialize()

            initialized.add(service_name)

        for service_name in self._services:
            await init_service(service_name)

    async def shutdown_all(self):
        """Shutdown all services"""
        for service in self._services.values():
            if service._initialized:
                await service.shutdown()

    async def health_check_all(self) -> Dict[str, ServiceHealth]:
        """Perform health check on all services"""
        results = {}
        for service_name, service in self._services.items():
            results[service_name] = await service.health_check()
        return results


# Global service registry instance
service_registry = ServiceRegistry()


def get_service(service_name: str) -> Optional[BaseService]:
    """Get service from global registry"""
    return service_registry.get(service_name)


def get_service_by_type(service_type: Type[T]) -> Optional[T]:
    """Get service by type from global registry"""
    return service_registry.get_by_type(service_type)


def register_service(service: BaseService, dependencies: Optional[List[str]] = None):
    """Register service in global registry"""
    service_registry.register(service, dependencies)
