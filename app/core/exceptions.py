"""
统一异常处理模块

提供完整的异常处理系统，包括：
- 自定义异常类层次结构
- 统一的异常处理器
- 标准化错误响应格式
- 错误日志和监控
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI):
    """
    设置应用异常处理器

    Args:
        app: FastAPI应用实例
    """
    # 添加自定义异常处理器
    app.add_exception_handler(APIException, api_exception_handler)

    # 添加HTTP异常处理器
    app.add_exception_handler(HTTPException, http_exception_handler)

    # 添加限流异常处理器
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

    # 添加通用异常处理器
    app.add_exception_handler(Exception, general_exception_handler)


async def api_exception_handler(request: Request, exc: "APIException"):
    """
    自定义API异常处理器

    Args:
        request: HTTP请求对象
        exc: API异常对象

    Returns:
        JSON响应
    """
    error_id = str(uuid.uuid4())

    # 记录错误日志
    logger.error(
        f"API Exception [{error_id}]: {exc.message}",
        extra={
            "error_id": error_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(error_id=error_id, path=str(request.url)),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP异常处理器

    Args:
        request: HTTP请求对象
        exc: HTTP异常对象

    Returns:
        JSON响应
    """
    error_id = str(uuid.uuid4())

    logger.warning(
        f"HTTP Exception [{error_id}]: {exc.detail}",
        extra={
            "error_id": error_id,
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "id": error_id,
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url),
            }
        },
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """
    限流异常处理器

    Args:
        request: HTTP请求对象
        exc: 限流异常对象

    Returns:
        JSON响应
    """
    error_id = str(uuid.uuid4())

    logger.warning(
        f"Rate Limit Exceeded [{error_id}]: {exc.detail}",
        extra={
            "error_id": error_id,
            "path": str(request.url),
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "id": error_id,
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please try again later.",
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url),
                "retry_after": getattr(exc, "retry_after", None),
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    通用异常处理器

    Args:
        request: HTTP请求对象
        exc: 异常对象

    Returns:
        JSON响应
    """
    error_id = str(uuid.uuid4())

    logger.error(
        f"Unhandled Exception [{error_id}]: {str(exc)}",
        extra={
            "error_id": error_id,
            "exception_type": type(exc).__name__,
            "path": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "id": error_id,
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url),
            }
        },
    )


# ============================================================================
# 异常类层次结构
# ============================================================================


class APIException(Exception):
    """
    API基础异常类

    所有自定义异常的基类，提供统一的错误处理接口
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)

    def to_dict(self, error_id: str = None, path: str = None) -> Dict[str, Any]:
        """
        将异常转换为字典格式

        Args:
            error_id: 错误ID
            path: 请求路径

        Returns:
            错误信息字典
        """
        error_dict = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp,
            }
        }

        if error_id:
            error_dict["error"]["id"] = error_id

        if path:
            error_dict["error"]["path"] = path

        if self.details:
            error_dict["error"]["details"] = self.details

        return error_dict


# ============================================================================
# 客户端错误异常 (4xx)
# ============================================================================


class ClientError(APIException):
    """客户端错误基类"""

    def __init__(self, message: str, status_code: int = 400, **kwargs):
        super().__init__(message, status_code, **kwargs)


class ValidationError(ClientError):
    """验证异常 - 400"""

    def __init__(self, message: str, field: str = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        super().__init__(
            f"Validation failed: {message}", 400, details=details, **kwargs
        )


class AuthenticationError(ClientError):
    """认证异常 - 401"""

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, 401, **kwargs)


class AuthorizationError(ClientError):
    """授权异常 - 403"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, 403, **kwargs)


class NotFoundError(ClientError):
    """资源未找到异常 - 404"""

    def __init__(self, resource: str = "Resource", resource_id: str = None, **kwargs):
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        else:
            message = f"{resource} not found"
        super().__init__(message, 404, **kwargs)


class ImageNotFoundError(NotFoundError):
    """图像未找到异常 - 404"""

    def __init__(self, image_id: str = None, image_hash: str = None, **kwargs):
        details = kwargs.get("details", {})
        if image_hash:
            message = f"Image with hash '{image_hash}' not found"
            details["image_hash"] = image_hash
        elif image_id:
            message = f"Image with ID '{image_id}' not found"
            details["image_id"] = image_id
        else:
            message = "Image not found"
        super().__init__(message, 404, details=details, **kwargs)


class ConflictError(ClientError):
    """冲突异常 - 409"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, 409, **kwargs)


class RateLimitError(ClientError):
    """限流异常 - 429"""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int = None, **kwargs
    ):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, 429, details=details, **kwargs)


# ============================================================================
# 服务器错误异常 (5xx)
# ============================================================================


class ServerError(APIException):
    """服务器错误基类"""

    def __init__(self, message: str, status_code: int = 500, **kwargs):
        super().__init__(message, status_code, **kwargs)


class ProcessingError(ServerError):
    """处理异常 - 500"""

    def __init__(self, message: str, operation: str = None, **kwargs):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
            message = f"Processing failed during {operation}: {message}"
        else:
            message = f"Processing failed: {message}"
        super().__init__(message, 500, details=details, **kwargs)


class ServiceError(ServerError):
    """服务错误异常 - 500"""

    def __init__(self, message: str, service_name: str = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details["service"] = service_name
            message = f"Service '{service_name}' error: {message}"
        else:
            message = f"Service error: {message}"
        super().__init__(message, 500, details=details, **kwargs)


class ServiceUnavailableError(ServerError):
    """服务不可用异常 - 503"""

    def __init__(self, service_name: str = None, message: str = None, **kwargs):
        if not message:
            if service_name:
                message = f"Service '{service_name}' is currently unavailable"
            else:
                message = "Service is currently unavailable"

        details = kwargs.get("details", {})
        if service_name:
            details["service"] = service_name

        super().__init__(message, 503, details=details, **kwargs)


class ExternalServiceError(ServerError):
    """外部服务错误异常 - 502"""

    def __init__(self, service_name: str, message: str = None, **kwargs):
        if not message:
            message = f"External service '{service_name}' returned an error"

        details = kwargs.get("details", {})
        details["external_service"] = service_name

        super().__init__(message, 502, details=details, **kwargs)


class TimeoutError(ServerError):
    """超时异常 - 504"""

    def __init__(self, operation: str = None, timeout: float = None, **kwargs):
        details = kwargs.get("details", {})

        if operation:
            message = f"Operation '{operation}' timed out"
            details["operation"] = operation
        else:
            message = "Request timed out"

        if timeout:
            details["timeout_seconds"] = timeout

        super().__init__(message, 504, details=details, **kwargs)


# ============================================================================
# 业务特定异常
# ============================================================================


class ImageProcessingError(ProcessingError):
    """图像处理异常"""

    def __init__(self, message: str, image_id: str = None, **kwargs):
        details = kwargs.get("details", {})
        if image_id:
            details["image_id"] = image_id
        super().__init__(
            message, operation="image_processing", details=details, **kwargs
        )


class VisionServiceError(ExternalServiceError):
    """视觉服务异常"""

    def __init__(self, message: str = None, **kwargs):
        super().__init__("Google Vision API", message, **kwargs)


class StorageError(ExternalServiceError):
    """存储服务异常"""

    def __init__(self, message: str = None, **kwargs):
        super().__init__("Google Cloud Storage", message, **kwargs)


class CacheError(ServiceError):
    """缓存服务异常"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, service_name="cache", **kwargs)


class DatabaseError(ServiceError):
    """数据库异常"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, service_name="database", **kwargs)


# ============================================================================
# 异常工厂函数
# ============================================================================


def create_validation_error(
    field: str, message: str, value: Any = None
) -> ValidationError:
    """
    创建验证错误异常

    Args:
        field: 字段名
        message: 错误消息
        value: 字段值

    Returns:
        ValidationError实例
    """
    details = {"field": field}
    if value is not None:
        details["value"] = str(value)

    return ValidationError(message, details=details)


def create_not_found_error(resource_type: str, identifier: str) -> NotFoundError:
    """
    创建资源未找到异常

    Args:
        resource_type: 资源类型
        identifier: 资源标识符

    Returns:
        NotFoundError实例
    """
    return NotFoundError(resource_type, identifier)
