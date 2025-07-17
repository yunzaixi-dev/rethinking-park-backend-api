"""
Dependency injection system for services.

This module provides dependency injection functionality for services,
allowing for clean separation of concerns and easier testing.
"""

import asyncio
import inspect
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from .base import BaseService, ServiceRegistry, service_registry

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DependencyInjector:
    """Dependency injection container for services"""

    def __init__(self, registry: ServiceRegistry = None):
        self.registry = registry or service_registry
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped: Dict[str, Dict[Type, Any]] = {}

    def register_factory(self, service_type: Type[T], factory: Callable[[], T]):
        """Register a factory function for a service type"""
        self._factories[service_type] = factory
        logger.info(f"Registered factory for {service_type.__name__}")

    def register_singleton(self, service_type: Type[T], instance: T):
        """Register a singleton instance for a service type"""
        self._singletons[service_type] = instance
        logger.info(f"Registered singleton for {service_type.__name__}")

    def get(self, service_type: Type[T], scope: Optional[str] = None) -> Optional[T]:
        """Get service instance by type"""
        # Check scoped instances first
        if scope and scope in self._scoped:
            scoped_instance = self._scoped[scope].get(service_type)
            if scoped_instance:
                return scoped_instance

        # Check singletons
        if service_type in self._singletons:
            return self._singletons[service_type]

        # Check service registry
        service = self.registry.get_by_type(service_type)
        if service:
            return service

        # Use factory if available
        if service_type in self._factories:
            instance = self._factories[service_type]()
            if scope:
                if scope not in self._scoped:
                    self._scoped[scope] = {}
                self._scoped[scope][service_type] = instance
            return instance

        return None

    def create_scope(self, scope_id: str):
        """Create a new dependency scope"""
        if scope_id not in self._scoped:
            self._scoped[scope_id] = {}

    def clear_scope(self, scope_id: str):
        """Clear a dependency scope"""
        if scope_id in self._scoped:
            del self._scoped[scope_id]


# Global dependency injector
injector = DependencyInjector()


def inject(*service_types: Type) -> Callable:
    """
    Decorator for dependency injection.

    Usage:
        @inject(SomeService, AnotherService)
        async def my_function(service1: SomeService, service2: AnotherService):
            # Use services
            pass
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        if len(service_types) > len(param_names):
            raise ValueError("More service types than function parameters")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Inject services as the first parameters
            injected_services = []
            for service_type in service_types:
                service = injector.get(service_type)
                if service is None:
                    raise ValueError(f"Service {service_type.__name__} not found")
                injected_services.append(service)

            # Call function with injected services + original args
            all_args = injected_services + list(args)

            if asyncio.iscoroutinefunction(func):
                return await func(*all_args, **kwargs)
            else:
                return func(*all_args, **kwargs)

        return wrapper

    return decorator


def get_service(service_type: Type[T], scope: Optional[str] = None) -> Optional[T]:
    """Get service instance by type"""
    return injector.get(service_type, scope)


class ServiceProvider:
    """Service provider for managing service lifecycle in specific contexts"""

    def __init__(self, scope_id: str = None):
        self.scope_id = scope_id or f"scope_{id(self)}"
        injector.create_scope(self.scope_id)

    def get_service(self, service_type: Type[T]) -> Optional[T]:
        """Get service in this provider's scope"""
        return injector.get(service_type, self.scope_id)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        injector.clear_scope(self.scope_id)


# FastAPI dependency functions
async def get_service_registry() -> ServiceRegistry:
    """FastAPI dependency to get service registry"""
    return service_registry


def create_service_dependency(service_type: Type[T]) -> Callable[[], T]:
    """Create a FastAPI dependency function for a service type"""

    async def dependency() -> T:
        service = injector.get(service_type)
        if service is None:
            raise ValueError(f"Service {service_type.__name__} not available")

        # Ensure service is initialized
        if isinstance(service, BaseService):
            async with service.ensure_initialized():
                return service

        return service

    return dependency


# Decorator for FastAPI endpoints with service injection
def with_services(*service_types: Type):
    """
    Decorator for FastAPI endpoints that need service injection.

    Usage:
        @app.get("/endpoint")
        @with_services(SomeService, AnotherService)
        async def endpoint(service1: SomeService, service2: AnotherService):
            # Use services
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Get function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        # Create new parameters with service dependencies
        new_params = []
        service_params = []

        for i, service_type in enumerate(service_types):
            param_name = f"_service_{i}"
            dependency_func = create_service_dependency(service_type)

            # Create parameter with dependency
            param = inspect.Parameter(
                param_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=service_type,
                default=dependency_func,
            )
            service_params.append(param)

        # Add original parameters (excluding services)
        for param in params[len(service_types) :]:
            new_params.append(param)

        # Create new signature
        new_sig = sig.replace(parameters=service_params + new_params)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper.__signature__ = new_sig
        return wrapper

    return decorator
