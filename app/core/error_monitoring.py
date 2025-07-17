"""
错误监控和日志模块

提供错误监控、日志记录和错误恢复机制
"""

import functools
import json
import logging
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 配置日志格式
LOG_FORMAT = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d"
        },
        "json": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {"": {"level": "INFO", "handlers": ["console", "file"]}},
}


class ErrorMonitor:
    """错误监控器"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        记录错误

        Args:
            error_type: 错误类型
            error_message: 错误消息
            context: 错误上下文
        """
        # 更新错误计数
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # 记录错误历史
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message,
            "context": context or {},
            "count": self.error_counts[error_type],
        }

        self.error_history.append(error_record)

        # 限制历史记录大小
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size :]

    def get_error_stats(self) -> Dict[str, Any]:
        """
        获取错误统计信息

        Returns:
            错误统计字典
        """
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": len(self.error_counts),
            "error_counts": self.error_counts.copy(),
            "recent_errors": self.error_history[-10:] if self.error_history else [],
        }

    def clear_stats(self):
        """清除统计信息"""
        self.error_counts.clear()
        self.error_history.clear()


# 全局错误监控器实例
error_monitor = ErrorMonitor()


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    设置日志配置

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
    """
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file or "logs/app.log"),
        ],
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    extra_message: str = None,
):
    """
    记录错误日志

    Args:
        logger: 日志记录器
        error: 异常对象
        context: 错误上下文
        extra_message: 额外消息
    """
    error_type = type(error).__name__
    error_message = str(error)

    # 构建日志消息
    log_message = f"{error_type}: {error_message}"
    if extra_message:
        log_message = f"{extra_message} - {log_message}"

    # 构建额外信息
    extra_info = {
        "error_type": error_type,
        "error_message": error_message,
        "traceback": traceback.format_exc(),
        "context": context or {},
    }

    # 记录日志
    logger.error(log_message, extra=extra_info, exc_info=True)

    # 记录到错误监控器
    error_monitor.record_error(error_type, error_message, context)


@contextmanager
def error_context(
    operation: str, logger: logging.Logger, context: Optional[Dict[str, Any]] = None
):
    """
    错误上下文管理器

    Args:
        operation: 操作名称
        logger: 日志记录器
        context: 上下文信息
    """
    start_time = datetime.now()
    operation_context = {
        "operation": operation,
        "start_time": start_time.isoformat(),
        **(context or {}),
    }

    try:
        logger.info(f"Starting operation: {operation}", extra=operation_context)
        yield operation_context

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            f"Operation completed: {operation} (duration: {duration:.2f}s)",
            extra={**operation_context, "duration": duration, "status": "success"},
        )

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        operation_context.update(
            {"duration": duration, "status": "failed", "error": str(e)}
        )

        log_error(logger, e, operation_context, f"Operation failed: {operation}")
        raise


def error_handler(
    operation: str = None,
    reraise: bool = True,
    default_return: Any = None,
    logger: logging.Logger = None,
):
    """
    错误处理装饰器

    Args:
        operation: 操作名称
        reraise: 是否重新抛出异常
        default_return: 默认返回值
        logger: 日志记录器
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation or f"{func.__module__}.{func.__name__}"
            func_logger = logger or logging.getLogger(func.__module__)

            try:
                with error_context(op_name, func_logger):
                    return await func(*args, **kwargs)
            except Exception as e:
                if reraise:
                    raise
                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation or f"{func.__module__}.{func.__name__}"
            func_logger = logger or logging.getLogger(func.__module__)

            try:
                with error_context(op_name, func_logger):
                    return func(*args, **kwargs)
            except Exception as e:
                if reraise:
                    raise
                return default_return

        # 检查函数是否是协程函数
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ErrorRecovery:
    """错误恢复机制"""

    @staticmethod
    def retry_with_backoff(
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        exceptions: tuple = (Exception,),
    ):
        """
        带退避的重试装饰器

        Args:
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            exceptions: 需要重试的异常类型
        """

        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                import asyncio

                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == max_retries:
                            raise

                        wait_time = backoff_factor * (2**attempt)
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                import time

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == max_retries:
                            raise

                        wait_time = backoff_factor * (2**attempt)
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)

            # 检查函数是否是协程函数
            if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    @staticmethod
    def circuit_breaker(
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        断路器装饰器

        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期异常类型
        """

        def decorator(func):
            func._failure_count = 0
            func._last_failure_time = None
            func._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                import asyncio

                now = datetime.now()

                # 检查断路器状态
                if func._state == "OPEN":
                    if (now - func._last_failure_time).seconds < recovery_timeout:
                        raise ServiceUnavailableError(
                            f"Circuit breaker is OPEN for {func.__name__}"
                        )
                    else:
                        func._state = "HALF_OPEN"

                try:
                    result = await func(*args, **kwargs)

                    # 成功时重置计数器
                    if func._state == "HALF_OPEN":
                        func._state = "CLOSED"
                    func._failure_count = 0

                    return result

                except expected_exception as e:
                    func._failure_count += 1
                    func._last_failure_time = now

                    if func._failure_count >= failure_threshold:
                        func._state = "OPEN"
                        logging.error(
                            f"Circuit breaker opened for {func.__name__} "
                            f"after {func._failure_count} failures"
                        )

                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                now = datetime.now()

                # 检查断路器状态
                if func._state == "OPEN":
                    if (now - func._last_failure_time).seconds < recovery_timeout:
                        raise ServiceUnavailableError(
                            f"Circuit breaker is OPEN for {func.__name__}"
                        )
                    else:
                        func._state = "HALF_OPEN"

                try:
                    result = func(*args, **kwargs)

                    # 成功时重置计数器
                    if func._state == "HALF_OPEN":
                        func._state = "CLOSED"
                    func._failure_count = 0

                    return result

                except expected_exception as e:
                    func._failure_count += 1
                    func._last_failure_time = now

                    if func._failure_count >= failure_threshold:
                        func._state = "OPEN"
                        logging.error(
                            f"Circuit breaker opened for {func.__name__} "
                            f"after {func._failure_count} failures"
                        )

                    raise

            # 检查函数是否是协程函数
            if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


# 导入必要的异常类
from .exceptions import ServiceUnavailableError


def get_error_stats() -> Dict[str, Any]:
    """
    获取全局错误统计信息

    Returns:
        错误统计字典
    """
    return error_monitor.get_error_stats()


def clear_error_stats():
    """清除全局错误统计信息"""
    error_monitor.clear_stats()
