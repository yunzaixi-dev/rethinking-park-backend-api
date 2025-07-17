"""
测试统一错误处理系统的集成
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_monitoring import (
    ErrorMonitor,
    clear_error_stats,
    error_context,
    error_handler,
    error_monitor,
    get_error_stats,
    log_error,
)
from app.core.exceptions import (
    APIException,
    CacheError,
    ImageNotFoundError,
    ProcessingError,
    StorageError,
    ValidationError,
    VisionServiceError,
    setup_exception_handlers,
)


class TestUnifiedErrorHandlingIntegration:
    """测试统一错误处理系统集成"""

    @pytest.fixture
    def test_app(self):
        """创建测试应用"""
        app = FastAPI()
        setup_exception_handlers(app)

        @app.get("/test/validation-error")
        async def test_validation_error():
            raise ValidationError("Invalid input", field="test_field")

        @app.get("/test/image-not-found")
        async def test_image_not_found():
            raise ImageNotFoundError(image_hash="test-hash-123")

        @app.get("/test/processing-error")
        async def test_processing_error():
            raise ProcessingError("Processing failed", operation="test_operation")

        @app.get("/test/vision-service-error")
        async def test_vision_service_error():
            raise VisionServiceError("Vision API error")

        @app.get("/test/storage-error")
        async def test_storage_error():
            raise StorageError("Storage operation failed")

        @app.get("/test/cache-error")
        async def test_cache_error():
            raise CacheError("Cache operation failed")

        @app.get("/test/general-exception")
        async def test_general_exception():
            raise ValueError("Unexpected error")

        return app

    def test_validation_error_handling(self, test_app):
        """测试验证错误处理"""
        client = TestClient(test_app)
        response = client.get("/test/validation-error")

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATIONERROR"
        assert "Invalid input" in data["error"]["message"]
        assert data["error"]["details"]["field"] == "test_field"
        assert "id" in data["error"]
        assert "timestamp" in data["error"]

    def test_image_not_found_error_handling(self, test_app):
        """测试图像未找到错误处理"""
        client = TestClient(test_app)
        response = client.get("/test/image-not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "IMAGENOTFOUNDERROR"
        assert "test-hash-123" in data["error"]["message"]
        assert data["error"]["details"]["image_hash"] == "test-hash-123"

    def test_processing_error_handling(self, test_app):
        """测试处理错误处理"""
        client = TestClient(test_app)
        response = client.get("/test/processing-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "PROCESSINGERROR"
        assert "Processing failed" in data["error"]["message"]
        assert data["error"]["details"]["operation"] == "test_operation"

    def test_vision_service_error_handling(self, test_app):
        """测试视觉服务错误处理"""
        client = TestClient(test_app)
        response = client.get("/test/vision-service-error")

        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "VISIONSERVICEERROR"
        assert "Vision API error" in data["error"]["message"]
        assert data["error"]["details"]["external_service"] == "Google Vision API"

    def test_storage_error_handling(self, test_app):
        """测试存储错误处理"""
        client = TestClient(test_app)
        response = client.get("/test/storage-error")

        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "STORAGEERROR"
        assert "Storage operation failed" in data["error"]["message"]
        assert data["error"]["details"]["external_service"] == "Google Cloud Storage"

    def test_cache_error_handling(self, test_app):
        """测试缓存错误处理"""
        client = TestClient(test_app)
        response = client.get("/test/cache-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "CACHEERROR"
        assert "Cache operation failed" in data["error"]["message"]
        assert data["error"]["details"]["service"] == "cache"

    def test_general_exception_handling(self, test_app):
        """测试通用异常处理"""
        client = TestClient(test_app)
        response = client.get("/test/general-exception")

        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error occurred" in data["error"]["message"]
        assert "id" in data["error"]

    def test_error_monitoring_integration(self):
        """测试错误监控集成"""
        # 清除之前的统计
        clear_error_stats()

        # 模拟一些错误
        error_monitor.record_error("ValidationError", "Test validation error")
        error_monitor.record_error("ProcessingError", "Test processing error")
        error_monitor.record_error("ValidationError", "Another validation error")

        # 检查统计信息
        stats = get_error_stats()
        assert stats["total_errors"] == 3
        assert stats["error_types"] == 2
        assert stats["error_counts"]["ValidationError"] == 2
        assert stats["error_counts"]["ProcessingError"] == 1
        assert len(stats["recent_errors"]) == 3

    @pytest.mark.asyncio
    async def test_error_context_integration(self):
        """测试错误上下文集成"""
        import logging
        from unittest.mock import Mock

        logger = Mock(spec=logging.Logger)

        # 测试成功情况
        with error_context("test_operation", logger, {"key": "value"}) as ctx:
            assert ctx["operation"] == "test_operation"
            assert ctx["key"] == "value"

        # 验证日志调用
        assert logger.info.call_count == 2

        # 测试异常情况
        logger.reset_mock()
        with pytest.raises(ValueError):
            with error_context("test_operation", logger):
                raise ValueError("Test error")

        # 验证错误日志
        logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handler_decorator_integration(self):
        """测试错误处理装饰器集成"""
        import logging
        from unittest.mock import Mock

        logger = Mock(spec=logging.Logger)

        @error_handler("test_function", logger=logger)
        async def test_async_function():
            return "success"

        @error_handler("test_function", logger=logger)
        def test_sync_function():
            return "success"

        # 测试异步函数成功
        result = await test_async_function()
        assert result == "success"

        # 测试同步函数成功
        result = test_sync_function()
        assert result == "success"

        # 测试异步函数异常
        @error_handler("test_function", reraise=True, logger=logger)
        async def test_async_function_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_async_function_error()

        # 测试同步函数异常
        @error_handler("test_function", reraise=True, logger=logger)
        def test_sync_function_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_sync_function_error()

    def test_service_integration_with_unified_errors(self):
        """测试服务与统一错误处理的集成"""
        # 这个测试验证服务层是否正确使用统一错误处理

        # 模拟图像处理服务错误
        from app.core.exceptions import ImageProcessingError
        from services.image_processing_service import ImageProcessingService

        service = ImageProcessingService()

        # 测试验证错误
        with pytest.raises(ValidationError):
            # 这应该触发验证错误
            service.validate_extraction_request(b"invalid", None, -1)

    def test_api_endpoint_integration_with_unified_errors(self, test_app):
        """测试API端点与统一错误处理的集成"""
        # 这个测试验证API端点是否正确使用统一错误处理

        client = TestClient(test_app)

        # 测试多个错误类型的响应格式一致性
        error_endpoints = [
            ("/test/validation-error", 400),
            ("/test/image-not-found", 404),
            ("/test/processing-error", 500),
            ("/test/vision-service-error", 502),
            ("/test/storage-error", 502),
            ("/test/cache-error", 500),
        ]

        for endpoint, expected_status in error_endpoints:
            response = client.get(endpoint)
            assert response.status_code == expected_status

            data = response.json()
            # 验证响应格式一致性
            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]
            assert "timestamp" in data["error"]
            assert "id" in data["error"]

    def test_error_recovery_mechanisms(self):
        """测试错误恢复机制"""
        from app.core.error_monitoring import ErrorRecovery

        # 测试重试机制
        call_count = 0

        @ErrorRecovery.retry_with_backoff(max_retries=2, backoff_factor=0.1)
        def test_retry_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = test_retry_function()
        assert result == "success"
        assert call_count == 3

        # 测试断路器机制
        @ErrorRecovery.circuit_breaker(failure_threshold=2, recovery_timeout=1)
        def test_circuit_breaker():
            raise ValueError("Service error")

        # 触发足够的失败来打开断路器
        for _ in range(2):
            with pytest.raises(ValueError):
                test_circuit_breaker()

        # 下一次调用应该立即失败
        from app.core.exceptions import ServiceUnavailableError

        with pytest.raises(ServiceUnavailableError):
            test_circuit_breaker()

    def test_logging_integration(self):
        """测试日志集成"""
        import logging
        from unittest.mock import Mock

        logger = Mock(spec=logging.Logger)
        error = ValueError("Test error")
        context = {"operation": "test", "key": "value"}

        log_error(logger, error, context, "Extra message")

        # 验证日志记录
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Extra message - ValueError: Test error" in call_args[0][0]
        assert call_args[1]["exc_info"] is True

        # 验证错误监控记录
        stats = get_error_stats()
        assert "ValueError" in [error["type"] for error in stats["recent_errors"]]

    def test_performance_impact(self):
        """测试性能影响"""
        import time

        # 测试错误处理对性能的影响
        start_time = time.time()

        # 模拟大量错误处理
        for i in range(100):
            try:
                raise ValidationError(f"Test error {i}")
            except ValidationError:
                pass

        end_time = time.time()
        processing_time = end_time - start_time

        # 确保错误处理不会显著影响性能
        assert processing_time < 1.0  # 应该在1秒内完成

    def test_memory_usage(self):
        """测试内存使用"""
        import gc

        # 清除之前的统计
        clear_error_stats()

        # 模拟大量错误记录
        for i in range(1000):
            error_monitor.record_error("TestError", f"Error {i}")

        # 检查内存使用是否受控
        stats = get_error_stats()
        assert len(stats["recent_errors"]) <= 1000  # 应该有历史记录限制

        # 强制垃圾回收
        gc.collect()

        # 清除统计信息
        clear_error_stats()

        # 验证清除后的状态
        stats = get_error_stats()
        assert stats["total_errors"] == 0
        assert len(stats["recent_errors"]) == 0


if __name__ == "__main__":
    pytest.main([__file__])
