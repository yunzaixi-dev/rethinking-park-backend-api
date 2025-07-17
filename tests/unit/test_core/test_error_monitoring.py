"""
测试错误监控系统
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.error_monitoring import (
    ErrorMonitor,
    ErrorRecovery,
    clear_error_stats,
    error_context,
    error_handler,
    error_monitor,
    get_error_stats,
    log_error,
    setup_logging,
)
from app.core.exceptions import ProcessingError, ServiceUnavailableError


class TestErrorMonitor:
    """测试错误监控器"""

    def test_error_monitor_initialization(self):
        """测试错误监控器初始化"""
        monitor = ErrorMonitor()

        assert monitor.error_counts == {}
        assert monitor.error_history == []
        assert monitor.max_history_size == 1000

    def test_record_error(self):
        """测试记录错误"""
        monitor = ErrorMonitor()

        monitor.record_error("ValueError", "Test error message", {"key": "value"})

        assert monitor.error_counts["ValueError"] == 1
        assert len(monitor.error_history) == 1

        error_record = monitor.error_history[0]
        assert error_record["type"] == "ValueError"
        assert error_record["message"] == "Test error message"
        assert error_record["context"]["key"] == "value"
        assert error_record["count"] == 1

    def test_multiple_errors_same_type(self):
        """测试记录多个相同类型错误"""
        monitor = ErrorMonitor()

        monitor.record_error("ValueError", "Error 1")
        monitor.record_error("ValueError", "Error 2")
        monitor.record_error("TypeError", "Error 3")

        assert monitor.error_counts["ValueError"] == 2
        assert monitor.error_counts["TypeError"] == 1
        assert len(monitor.error_history) == 3

    def test_get_error_stats(self):
        """测试获取错误统计"""
        monitor = ErrorMonitor()

        monitor.record_error("ValueError", "Error 1")
        monitor.record_error("TypeError", "Error 2")

        stats = monitor.get_error_stats()

        assert stats["total_errors"] == 2
        assert stats["error_types"] == 2
        assert stats["error_counts"]["ValueError"] == 1
        assert stats["error_counts"]["TypeError"] == 1
        assert len(stats["recent_errors"]) == 2

    def test_clear_stats(self):
        """测试清除统计信息"""
        monitor = ErrorMonitor()

        monitor.record_error("ValueError", "Error 1")
        monitor.clear_stats()

        assert monitor.error_counts == {}
        assert monitor.error_history == []

    def test_history_size_limit(self):
        """测试历史记录大小限制"""
        monitor = ErrorMonitor()
        monitor.max_history_size = 3

        for i in range(5):
            monitor.record_error("ValueError", f"Error {i}")

        assert len(monitor.error_history) == 3
        # 应该保留最后3个记录
        assert monitor.error_history[0]["message"] == "Error 2"
        assert monitor.error_history[-1]["message"] == "Error 4"


class TestLoggingSetup:
    """测试日志设置"""

    def test_setup_logging_with_defaults(self):
        """测试默认日志设置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")

            setup_logging("DEBUG", log_file)

            logger = logging.getLogger("test")
            logger.error("Test error message")

            # 检查日志文件是否创建
            assert os.path.exists(log_file)

    def test_log_error_function(self):
        """测试错误日志记录函数"""
        logger = Mock(spec=logging.Logger)
        error = ValueError("Test error")
        context = {"operation": "test"}

        with patch("app.core.error_monitoring.error_monitor") as mock_monitor:
            log_error(logger, error, context, "Extra message")

        # 验证日志记录
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Extra message - ValueError: Test error" in call_args[0][0]
        assert call_args[1]["exc_info"] is True

        # 验证错误监控器记录
        mock_monitor.record_error.assert_called_once_with(
            "ValueError", "Test error", context
        )


class TestErrorContext:
    """测试错误上下文管理器"""

    @pytest.mark.asyncio
    async def test_error_context_success(self):
        """测试成功执行的错误上下文"""
        logger = Mock(spec=logging.Logger)

        with error_context("test_operation", logger, {"key": "value"}) as ctx:
            assert ctx["operation"] == "test_operation"
            assert ctx["key"] == "value"
            assert "start_time" in ctx

        # 验证日志调用
        assert logger.info.call_count == 2  # 开始和完成

        # 检查开始日志
        start_call = logger.info.call_args_list[0]
        assert "Starting operation: test_operation" in start_call[0][0]

        # 检查完成日志
        end_call = logger.info.call_args_list[1]
        assert "Operation completed: test_operation" in end_call[0][0]

    def test_error_context_with_exception(self):
        """测试异常情况下的错误上下文"""
        logger = Mock(spec=logging.Logger)

        with pytest.raises(ValueError):
            with error_context("test_operation", logger) as ctx:
                raise ValueError("Test error")

        # 验证错误日志记录
        logger.error.assert_called_once()


class TestErrorHandler:
    """测试错误处理装饰器"""

    @pytest.mark.asyncio
    async def test_async_error_handler_success(self):
        """测试异步错误处理装饰器成功情况"""
        logger = Mock(spec=logging.Logger)

        @error_handler("test_operation", logger=logger)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_error_handler_with_exception(self):
        """测试异步错误处理装饰器异常情况"""
        logger = Mock(spec=logging.Logger)

        @error_handler("test_operation", reraise=True, logger=logger)
        async def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_func()

    @pytest.mark.asyncio
    async def test_async_error_handler_with_default_return(self):
        """测试异步错误处理装饰器默认返回值"""
        logger = Mock(spec=logging.Logger)

        @error_handler(
            "test_operation", reraise=False, default_return="default", logger=logger
        )
        async def test_func():
            raise ValueError("Test error")

        result = await test_func()
        assert result == "default"

    def test_sync_error_handler_success(self):
        """测试同步错误处理装饰器成功情况"""
        logger = Mock(spec=logging.Logger)

        @error_handler("test_operation", logger=logger)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_sync_error_handler_with_exception(self):
        """测试同步错误处理装饰器异常情况"""
        logger = Mock(spec=logging.Logger)

        @error_handler("test_operation", reraise=True, logger=logger)
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_func()


class TestErrorRecovery:
    """测试错误恢复机制"""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """测试重试机制成功情况"""
        call_count = 0

        @ErrorRecovery.retry_with_backoff(max_retries=3, backoff_factor=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_max_retries(self):
        """测试重试机制达到最大重试次数"""
        call_count = 0

        @ErrorRecovery.retry_with_backoff(max_retries=2, backoff_factor=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(ValueError):
            await test_func()

        assert call_count == 3  # 初始调用 + 2次重试

    def test_sync_retry_with_backoff(self):
        """测试同步重试机制"""
        call_count = 0

        @ErrorRecovery.retry_with_backoff(max_retries=2, backoff_factor=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """测试断路器关闭状态"""

        @ErrorRecovery.circuit_breaker(failure_threshold=3, recovery_timeout=1)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"
        assert test_func._state == "CLOSED"
        assert test_func._failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """测试断路器打开状态"""

        @ErrorRecovery.circuit_breaker(failure_threshold=2, recovery_timeout=60)
        async def test_func():
            raise ValueError("Service error")

        # 触发足够的失败来打开断路器
        for _ in range(2):
            with pytest.raises(ValueError):
                await test_func()

        assert test_func._state == "OPEN"

        # 下一次调用应该立即失败
        with pytest.raises(ServiceUnavailableError):
            await test_func()

    def test_sync_circuit_breaker(self):
        """测试同步断路器"""

        @ErrorRecovery.circuit_breaker(failure_threshold=2, recovery_timeout=60)
        def test_func():
            raise ValueError("Service error")

        # 触发足够的失败来打开断路器
        for _ in range(2):
            with pytest.raises(ValueError):
                test_func()

        assert test_func._state == "OPEN"

        # 下一次调用应该立即失败
        with pytest.raises(ServiceUnavailableError):
            test_func()


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_error_stats(self):
        """测试获取全局错误统计"""
        # 清除之前的统计
        clear_error_stats()

        # 记录一些错误
        error_monitor.record_error("TestError", "Test message")

        stats = get_error_stats()
        assert stats["total_errors"] == 1
        assert "TestError" in stats["error_counts"]

    def test_clear_error_stats(self):
        """测试清除全局错误统计"""
        # 记录一些错误
        error_monitor.record_error("TestError", "Test message")

        # 清除统计
        clear_error_stats()

        stats = get_error_stats()
        assert stats["total_errors"] == 0
        assert stats["error_counts"] == {}


if __name__ == "__main__":
    pytest.main([__file__])
