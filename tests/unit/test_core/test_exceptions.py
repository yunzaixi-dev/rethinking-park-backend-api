"""
测试异常处理系统
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.exceptions import (
    APIException,
    AuthenticationError,
    AuthorizationError,
    CacheError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ImageNotFoundError,
    ImageProcessingError,
    NotFoundError,
    ProcessingError,
    RateLimitError,
    ServiceError,
    ServiceUnavailableError,
    StorageError,
    TimeoutError,
    ValidationError,
    VisionServiceError,
    api_exception_handler,
    create_not_found_error,
    create_validation_error,
    general_exception_handler,
    http_exception_handler,
    rate_limit_exception_handler,
    setup_exception_handlers,
)


class TestAPIException:
    """测试API异常基类"""

    def test_basic_exception_creation(self):
        """测试基本异常创建"""
        exc = APIException("Test message", 400, "TEST_ERROR")

        assert exc.message == "Test message"
        assert exc.status_code == 400
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {}
        assert isinstance(exc.timestamp, str)

    def test_exception_with_details(self):
        """测试带详细信息的异常"""
        details = {"field": "email", "value": "invalid"}
        exc = APIException("Test message", 400, "TEST_ERROR", details)

        assert exc.details == details

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        exc = APIException("Test message", 400, "TEST_ERROR")
        result = exc.to_dict("error-123", "/test/path")

        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test message"
        assert result["error"]["id"] == "error-123"
        assert result["error"]["path"] == "/test/path"
        assert "timestamp" in result["error"]


class TestSpecificExceptions:
    """测试特定异常类"""

    def test_validation_error(self):
        """测试验证错误"""
        exc = ValidationError("Invalid email format", field="email")

        assert exc.status_code == 400
        assert "Validation failed" in exc.message
        assert exc.details["field"] == "email"

    def test_authentication_error(self):
        """测试认证错误"""
        exc = AuthenticationError()

        assert exc.status_code == 401
        assert exc.message == "Authentication required"

    def test_authorization_error(self):
        """测试授权错误"""
        exc = AuthorizationError()

        assert exc.status_code == 403
        assert exc.message == "Access denied"

    def test_not_found_error(self):
        """测试资源未找到错误"""
        exc = NotFoundError("User", "123")

        assert exc.status_code == 404
        assert "User with ID '123' not found" in exc.message

    def test_image_not_found_error_with_hash(self):
        """测试图像未找到错误（使用哈希）"""
        exc = ImageNotFoundError(image_hash="abc123")

        assert exc.status_code == 404
        assert "hash 'abc123'" in exc.message
        assert exc.details["image_hash"] == "abc123"

    def test_image_not_found_error_with_id(self):
        """测试图像未找到错误（使用ID）"""
        exc = ImageNotFoundError(image_id="img-123")

        assert exc.status_code == 404
        assert "ID 'img-123'" in exc.message
        assert exc.details["image_id"] == "img-123"

    def test_processing_error(self):
        """测试处理错误"""
        exc = ProcessingError("Failed to resize image", operation="resize")

        assert exc.status_code == 500
        assert "Processing failed during resize" in exc.message
        assert exc.details["operation"] == "resize"

    def test_service_error(self):
        """测试服务错误"""
        exc = ServiceError("Connection failed", service_name="database")

        assert exc.status_code == 500
        assert "Service 'database' error" in exc.message
        assert exc.details["service"] == "database"

    def test_service_unavailable_error(self):
        """测试服务不可用错误"""
        exc = ServiceUnavailableError("redis")

        assert exc.status_code == 503
        assert "Service 'redis' is currently unavailable" in exc.message
        assert exc.details["service"] == "redis"

    def test_external_service_error(self):
        """测试外部服务错误"""
        exc = ExternalServiceError("Google Vision API", "API quota exceeded")

        assert exc.status_code == 502
        assert "API quota exceeded" in exc.message
        assert exc.details["external_service"] == "Google Vision API"

    def test_timeout_error(self):
        """测试超时错误"""
        exc = TimeoutError("image_processing", 30.0)

        assert exc.status_code == 504
        assert "Operation 'image_processing' timed out" in exc.message
        assert exc.details["operation"] == "image_processing"
        assert exc.details["timeout_seconds"] == 30.0


class TestBusinessSpecificExceptions:
    """测试业务特定异常"""

    def test_image_processing_error(self):
        """测试图像处理错误"""
        exc = ImageProcessingError("Failed to detect faces", image_id="img-123")

        assert exc.status_code == 500
        assert "Processing failed" in exc.message
        assert exc.details["operation"] == "image_processing"
        assert exc.details["image_id"] == "img-123"

    def test_vision_service_error(self):
        """测试视觉服务错误"""
        exc = VisionServiceError("API rate limit exceeded")

        assert exc.status_code == 502
        assert exc.details["external_service"] == "Google Vision API"

    def test_storage_error(self):
        """测试存储错误"""
        exc = StorageError("Bucket not found")

        assert exc.status_code == 502
        assert exc.details["external_service"] == "Google Cloud Storage"

    def test_cache_error(self):
        """测试缓存错误"""
        exc = CacheError("Redis connection failed")

        assert exc.status_code == 500
        assert exc.details["service"] == "cache"

    def test_database_error(self):
        """测试数据库错误"""
        exc = DatabaseError("Connection timeout")

        assert exc.status_code == 500
        assert exc.details["service"] == "database"


class TestExceptionFactories:
    """测试异常工厂函数"""

    def test_create_validation_error(self):
        """测试创建验证错误"""
        exc = create_validation_error("email", "Invalid format", "invalid@")

        assert isinstance(exc, ValidationError)
        assert exc.details["field"] == "email"
        assert exc.details["value"] == "invalid@"

    def test_create_not_found_error(self):
        """测试创建未找到错误"""
        exc = create_not_found_error("User", "123")

        assert isinstance(exc, NotFoundError)
        assert "User with ID '123' not found" in exc.message


@pytest.fixture
def test_app():
    """创建测试应用"""
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/test/api-exception")
    async def test_api_exception():
        raise APIException("Test API exception", 400, "TEST_ERROR")

    @app.get("/test/validation-error")
    async def test_validation_error():
        raise ValidationError("Invalid input", field="test_field")

    @app.get("/test/not-found")
    async def test_not_found():
        raise ImageNotFoundError(image_id="test-123")

    @app.get("/test/server-error")
    async def test_server_error():
        raise ProcessingError("Test processing error")

    @app.get("/test/general-exception")
    async def test_general_exception():
        raise ValueError("Unexpected error")

    return app


class TestExceptionHandlers:
    """测试异常处理器"""

    def test_api_exception_handler(self, test_app):
        """测试API异常处理器"""
        client = TestClient(test_app)
        response = client.get("/test/api-exception")

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test API exception"
        assert "id" in data["error"]
        assert "timestamp" in data["error"]

    def test_validation_error_handler(self, test_app):
        """测试验证错误处理器"""
        client = TestClient(test_app)
        response = client.get("/test/validation-error")

        assert response.status_code == 400
        data = response.json()
        assert "Validation failed" in data["error"]["message"]
        assert data["error"]["details"]["field"] == "test_field"

    def test_not_found_error_handler(self, test_app):
        """测试未找到错误处理器"""
        client = TestClient(test_app)
        response = client.get("/test/not-found")

        assert response.status_code == 404
        data = response.json()
        assert "test-123" in data["error"]["message"]
        assert data["error"]["details"]["image_id"] == "test-123"

    def test_server_error_handler(self, test_app):
        """测试服务器错误处理器"""
        client = TestClient(test_app)
        response = client.get("/test/server-error")

        assert response.status_code == 500
        data = response.json()
        assert "Processing failed" in data["error"]["message"]

    def test_general_exception_handler(self, test_app):
        """测试通用异常处理器"""
        client = TestClient(test_app)
        response = client.get("/test/general-exception")

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error occurred" in data["error"]["message"]


@pytest.mark.asyncio
class TestAsyncExceptionHandlers:
    """测试异步异常处理器"""

    async def test_api_exception_handler_async(self):
        """测试异步API异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"

        exc = APIException("Test message", 400, "TEST_ERROR")

        with patch("app.core.exceptions.uuid.uuid4", return_value="test-error-id"):
            response = await api_exception_handler(request, exc)

        assert response.status_code == 400
        content = json.loads(response.body)
        assert content["error"]["id"] == "test-error-id"
        assert content["error"]["code"] == "TEST_ERROR"

    async def test_general_exception_handler_async(self):
        """测试异步通用异常处理器"""
        request = Mock(spec=Request)
        request.url = "http://test.com/api/test"
        request.method = "GET"

        exc = ValueError("Test error")

        with patch("app.core.exceptions.uuid.uuid4", return_value="test-error-id"):
            response = await general_exception_handler(request, exc)

        assert response.status_code == 500
        content = json.loads(response.body)
        assert content["error"]["id"] == "test-error-id"
        assert content["error"]["code"] == "INTERNAL_SERVER_ERROR"


if __name__ == "__main__":
    pytest.main([__file__])
