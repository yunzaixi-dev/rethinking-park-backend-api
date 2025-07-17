"""
Enhanced error handling and retry mechanisms for image processing services
"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union

from fastapi import HTTPException
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)

# Custom Exception Classes


class VisionAPIException(Exception):
    """Exception raised for Google Cloud Vision API failures"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.retry_after = retry_after
        super().__init__(self.message)


class ProcessingException(Exception):
    """Exception raised for image processing failures"""

    def __init__(self, message: str, operation: str, recoverable: bool = True):
        self.message = message
        self.operation = operation
        self.recoverable = recoverable
        super().__init__(self.message)


class BatchProcessingException(Exception):
    """Exception raised for batch processing failures"""

    def __init__(
        self,
        message: str,
        failed_items: List[Dict[str, Any]],
        partial_results: Optional[List[Dict[str, Any]]] = None,
    ):
        self.message = message
        self.failed_items = failed_items
        self.partial_results = partial_results or []
        super().__init__(self.message)


class AnnotationRenderingException(Exception):
    """Exception raised for image annotation rendering failures"""

    def __init__(
        self, message: str, annotation_type: str, fallback_available: bool = True
    ):
        self.message = message
        self.annotation_type = annotation_type
        self.fallback_available = fallback_available
        super().__init__(self.message)


class CacheException(Exception):
    """Exception raised for cache operation failures"""

    def __init__(self, message: str, operation: str, cache_type: str):
        self.message = message
        self.operation = operation
        self.cache_type = cache_type
        super().__init__(self.message)


# Retry Strategies


class RetryStrategy:
    """Base class for retry strategies"""

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay

    def get_delay(self, attempt: int) -> float:
        """Get delay for the given attempt number"""
        raise NotImplementedError


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff retry strategy"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        super().__init__(max_attempts, base_delay)
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with optional jitter"""
        delay = self.base_delay * (2 ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


class LinearBackoffStrategy(RetryStrategy):
    """Linear backoff retry strategy"""

    def __init__(
        self, max_attempts: int = 3, base_delay: float = 1.0, increment: float = 1.0
    ):
        super().__init__(max_attempts, base_delay)
        self.increment = increment

    def get_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay"""
        return self.base_delay + (self.increment * (attempt - 1))


# Retry Decorators


def retry_on_exception(
    exceptions: Union[Type[Exception], tuple] = (Exception,),
    strategy: Optional[RetryStrategy] = None,
    on_retry: Optional[Callable] = None,
    on_failure: Optional[Callable] = None,
):
    """
    Decorator for retrying functions on specific exceptions

    Args:
        exceptions: Exception types to retry on
        strategy: Retry strategy to use
        on_retry: Callback function called on each retry
        on_failure: Callback function called on final failure
    """
    if strategy is None:
        strategy = ExponentialBackoffStrategy()

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, strategy.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == strategy.max_attempts:
                        # Final attempt failed
                        if on_failure:
                            on_failure(e, attempt)
                        raise

                    # Calculate delay and wait
                    delay = strategy.get_delay(attempt)

                    if on_retry:
                        on_retry(e, attempt, delay)

                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, strategy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == strategy.max_attempts:
                        # Final attempt failed
                        if on_failure:
                            on_failure(e, attempt)
                        raise

                    # Calculate delay and wait
                    delay = strategy.get_delay(attempt)

                    if on_retry:
                        on_retry(e, attempt, delay)

                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Specific retry decorators for common scenarios


def retry_vision_api(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator specifically for Google Vision API calls"""
    return retry_on_exception(
        exceptions=(GoogleCloudError, VisionAPIException),
        strategy=ExponentialBackoffStrategy(max_attempts, base_delay, max_delay=30.0),
        on_retry=lambda e, attempt, delay: logger.warning(
            f"Vision API retry {attempt}: {e}"
        ),
    )


def retry_processing(max_attempts: int = 2, base_delay: float = 0.5):
    """Retry decorator for image processing operations"""
    return retry_on_exception(
        exceptions=(ProcessingException,),
        strategy=LinearBackoffStrategy(max_attempts, base_delay),
        on_retry=lambda e, attempt, delay: logger.warning(
            f"Processing retry {attempt}: {e}"
        ),
    )


# Error Handler Classes


class ErrorHandler:
    """Base error handler class"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an error and return error information"""
        raise NotImplementedError


class VisionAPIErrorHandler(ErrorHandler):
    """Error handler for Google Vision API errors"""

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Vision API errors with appropriate responses"""
        error_info = {
            "error_type": "vision_api_error",
            "message": str(error),
            "context": context,
            "timestamp": time.time(),
            "recoverable": True,
        }

        if isinstance(error, GoogleCloudError):
            # Handle specific Google Cloud errors
            if hasattr(error, "code"):
                error_info["error_code"] = error.code

                # Determine if error is recoverable
                if error.code in [
                    429,
                    503,
                    500,
                ]:  # Rate limit, service unavailable, internal error
                    error_info["recoverable"] = True
                    error_info["retry_after"] = 5
                elif error.code in [
                    400,
                    401,
                    403,
                ]:  # Bad request, unauthorized, forbidden
                    error_info["recoverable"] = False
                else:
                    error_info["recoverable"] = True

            self.logger.error(f"Google Cloud Vision API error: {error}")

        elif isinstance(error, DefaultCredentialsError):
            error_info.update(
                {
                    "error_type": "credentials_error",
                    "message": "Google Cloud credentials not found or invalid",
                    "recoverable": False,
                    "suggestion": "Check Google Cloud credentials configuration",
                }
            )
            self.logger.error("Google Cloud credentials error")

        elif isinstance(error, VisionAPIException):
            error_info.update(
                {
                    "error_code": error.error_code,
                    "retry_after": error.retry_after,
                    "recoverable": True,
                }
            )
            self.logger.error(f"Vision API exception: {error}")

        return error_info


class ProcessingErrorHandler(ErrorHandler):
    """Error handler for image processing errors"""

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle image processing errors"""
        error_info = {
            "error_type": "processing_error",
            "message": str(error),
            "context": context,
            "timestamp": time.time(),
            "recoverable": True,
        }

        if isinstance(error, ProcessingException):
            error_info.update(
                {"operation": error.operation, "recoverable": error.recoverable}
            )

            # Provide specific handling based on operation type
            if error.operation == "extraction":
                error_info["fallback_suggestion"] = (
                    "Try with different bounding box coordinates"
                )
            elif error.operation == "annotation":
                error_info["fallback_suggestion"] = (
                    "Return original image without annotations"
                )

        elif isinstance(error, AnnotationRenderingException):
            error_info.update(
                {
                    "error_type": "annotation_error",
                    "annotation_type": error.annotation_type,
                    "fallback_available": error.fallback_available,
                }
            )

        self.logger.error(f"Processing error: {error}")
        return error_info


class BatchProcessingErrorHandler(ErrorHandler):
    """Error handler for batch processing errors"""

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch processing errors with partial results"""
        error_info = {
            "error_type": "batch_processing_error",
            "message": str(error),
            "context": context,
            "timestamp": time.time(),
            "recoverable": True,
        }

        if isinstance(error, BatchProcessingException):
            error_info.update(
                {
                    "failed_items": error.failed_items,
                    "partial_results": error.partial_results,
                    "success_count": len(error.partial_results),
                    "failure_count": len(error.failed_items),
                }
            )

            # Determine if batch can be retried
            if len(error.partial_results) > 0:
                error_info["partial_success"] = True
                error_info["retry_suggestion"] = "Retry only failed items"

        self.logger.error(f"Batch processing error: {error}")
        return error_info


# Fallback Strategies


class FallbackStrategy:
    """Base class for fallback strategies"""

    def execute_fallback(
        self, original_error: Exception, context: Dict[str, Any]
    ) -> Any:
        """Execute fallback strategy"""
        raise NotImplementedError


class GracefulDegradationStrategy(FallbackStrategy):
    """Fallback strategy that provides graceful degradation"""

    def __init__(self, fallback_response: Any = None):
        self.fallback_response = fallback_response

    def execute_fallback(
        self, original_error: Exception, context: Dict[str, Any]
    ) -> Any:
        """Return a graceful fallback response"""
        if self.fallback_response is not None:
            return self.fallback_response

        # Default fallback responses based on context
        operation = context.get("operation", "unknown")

        if operation == "detection":
            return {
                "objects": [],
                "faces": [],
                "labels": [],
                "success": False,
                "error": str(original_error),
                "fallback_used": True,
            }
        elif operation == "extraction":
            return {
                "extracted_image_url": None,
                "success": False,
                "error": str(original_error),
                "fallback_used": True,
            }
        else:
            return {
                "success": False,
                "error": str(original_error),
                "fallback_used": True,
            }


# Error Recovery Manager


class ErrorRecoveryManager:
    """Manages error recovery strategies and fallbacks"""

    def __init__(self):
        self.error_handlers = {
            "vision_api": VisionAPIErrorHandler(),
            "processing": ProcessingErrorHandler(),
            "batch_processing": BatchProcessingErrorHandler(),
        }
        self.fallback_strategies = {}

    def register_fallback(self, error_type: str, strategy: FallbackStrategy):
        """Register a fallback strategy for a specific error type"""
        self.fallback_strategies[error_type] = strategy

    def handle_error_with_recovery(
        self, error: Exception, context: Dict[str, Any], attempt_recovery: bool = True
    ) -> Dict[str, Any]:
        """Handle error with recovery attempt"""
        # Determine error type
        error_type = self._classify_error(error)

        # Get appropriate error handler
        handler = self.error_handlers.get(error_type, ErrorHandler())
        error_info = handler.handle_error(error, context)

        # Attempt recovery if enabled and error is recoverable
        if attempt_recovery and error_info.get("recoverable", False):
            fallback_strategy = self.fallback_strategies.get(error_type)
            if fallback_strategy:
                try:
                    fallback_result = fallback_strategy.execute_fallback(error, context)
                    error_info["fallback_result"] = fallback_result
                    error_info["recovery_attempted"] = True
                except Exception as fallback_error:
                    error_info["fallback_error"] = str(fallback_error)
                    error_info["recovery_failed"] = True

        return error_info

    def _classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate handling"""
        if isinstance(
            error, (GoogleCloudError, VisionAPIException, DefaultCredentialsError)
        ):
            return "vision_api"
        elif isinstance(error, (ProcessingException, AnnotationRenderingException)):
            return "processing"
        elif isinstance(error, BatchProcessingException):
            return "batch_processing"
        else:
            return "generic"


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()

# Register default fallback strategies
error_recovery_manager.register_fallback("vision_api", GracefulDegradationStrategy())
error_recovery_manager.register_fallback("processing", GracefulDegradationStrategy())
error_recovery_manager.register_fallback(
    "batch_processing", GracefulDegradationStrategy()
)

# Utility functions for common error scenarios


def handle_vision_api_error(error: Exception, image_hash: str) -> Dict[str, Any]:
    """Utility function to handle Vision API errors"""
    context = {
        "operation": "vision_api_call",
        "image_hash": image_hash,
        "service": "google_cloud_vision",
    }
    return error_recovery_manager.handle_error_with_recovery(error, context)


def handle_processing_error(
    error: Exception, operation: str, **kwargs
) -> Dict[str, Any]:
    """Utility function to handle processing errors"""
    context = {"operation": operation, **kwargs}
    return error_recovery_manager.handle_error_with_recovery(error, context)


def handle_batch_error(
    error: Exception, batch_id: str, items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Utility function to handle batch processing errors"""
    context = {
        "operation": "batch_processing",
        "batch_id": batch_id,
        "total_items": len(items),
    }
    return error_recovery_manager.handle_error_with_recovery(error, context)


# HTTP Exception converters


def convert_to_http_exception(error_info: Dict[str, Any]) -> HTTPException:
    """Convert error info to appropriate HTTP exception"""
    error_type = error_info.get("error_type", "generic")
    message = error_info.get("message", "An error occurred")

    if error_type == "vision_api_error":
        error_code = error_info.get("error_code")
        if error_code == 429:
            return HTTPException(
                status_code=429, detail="Rate limit exceeded. Please try again later."
            )
        elif error_code in [401, 403]:
            return HTTPException(
                status_code=503, detail="Vision service temporarily unavailable"
            )
        else:
            return HTTPException(status_code=500, detail=f"Vision API error: {message}")

    elif error_type == "credentials_error":
        return HTTPException(
            status_code=503, detail="Vision service configuration error"
        )

    elif error_type == "processing_error":
        if error_info.get("recoverable", True):
            return HTTPException(status_code=422, detail=f"Processing error: {message}")
        else:
            return HTTPException(status_code=400, detail=f"Invalid request: {message}")

    elif error_type == "batch_processing_error":
        if error_info.get("partial_success", False):
            return HTTPException(status_code=207, detail=f"Partial success: {message}")
        else:
            return HTTPException(
                status_code=500, detail=f"Batch processing failed: {message}"
            )

    else:
        return HTTPException(status_code=500, detail=f"Internal error: {message}")
