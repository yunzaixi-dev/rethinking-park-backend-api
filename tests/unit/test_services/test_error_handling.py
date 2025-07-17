#!/usr/bin/env python3
"""
Test script for enhanced error handling and retry mechanisms
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.error_handling import (
    BatchProcessingException,
    ErrorRecoveryManager,
    ProcessingException,
    VisionAPIException,
    handle_processing_error,
    handle_vision_api_error,
    retry_processing,
    retry_vision_api,
)


async def test_retry_decorators():
    """Test retry decorators"""
    print("Testing retry decorators...")

    # Test vision API retry
    attempt_count = 0

    @retry_vision_api(max_attempts=3, base_delay=0.1)
    async def failing_vision_call():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise VisionAPIException("Temporary API failure", retry_after=1)
        return {"success": True, "attempt": attempt_count}

    try:
        result = await failing_vision_call()
        print(f"✅ Vision API retry succeeded after {result['attempt']} attempts")
    except Exception as e:
        print(f"❌ Vision API retry failed: {e}")

    # Test processing retry
    attempt_count = 0

    @retry_processing(max_attempts=2, base_delay=0.1)
    async def failing_processing():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise ProcessingException("Temporary processing failure", "test_operation")
        return {"success": True, "attempt": attempt_count}

    try:
        result = await failing_processing()
        print(f"✅ Processing retry succeeded after {result['attempt']} attempts")
    except Exception as e:
        print(f"❌ Processing retry failed: {e}")


def test_error_classification():
    """Test error classification and handling"""
    print("\nTesting error classification...")

    # Test Vision API error handling
    vision_error = VisionAPIException(
        "Rate limit exceeded", error_code="429", retry_after=5
    )
    error_info = handle_vision_api_error(vision_error, "test_image_hash")

    print(f"Vision API Error Info:")
    print(f"  Type: {error_info.get('error_type')}")
    print(f"  Recoverable: {error_info.get('recoverable')}")
    print(f"  Retry After: {error_info.get('retry_after')}")

    # Test processing error handling
    processing_error = ProcessingException(
        "Image extraction failed", "extraction", recoverable=True
    )
    error_info = handle_processing_error(
        processing_error, "extraction", image_hash="test_hash"
    )

    print(f"\nProcessing Error Info:")
    print(f"  Type: {error_info.get('error_type')}")
    print(f"  Operation: {error_info.get('operation')}")
    print(f"  Recoverable: {error_info.get('recoverable')}")


def test_error_recovery_manager():
    """Test error recovery manager"""
    print("\nTesting error recovery manager...")

    manager = ErrorRecoveryManager()

    # Test with different error types
    test_errors = [
        VisionAPIException("API quota exceeded"),
        ProcessingException("Memory allocation failed", "image_processing"),
        BatchProcessingException(
            "Partial batch failure",
            [{"id": "1", "error": "timeout"}],
            [{"id": "2", "result": "success"}],
        ),
    ]

    for error in test_errors:
        context = {"operation": "test", "timestamp": "2024-01-01"}
        error_info = manager.handle_error_with_recovery(error, context)

        print(f"Error: {type(error).__name__}")
        print(f"  Classified as: {error_info.get('error_type')}")
        print(f"  Recoverable: {error_info.get('recoverable')}")
        print(f"  Recovery attempted: {error_info.get('recovery_attempted', False)}")


def test_batch_error_handling():
    """Test batch processing error handling"""
    print("\nTesting batch error handling...")

    # Simulate batch processing with partial failures
    failed_items = [
        {"operation_id": "op_1", "error": "Vision API timeout"},
        {"operation_id": "op_3", "error": "Invalid image format"},
    ]

    partial_results = [
        {"operation_id": "op_2", "result": {"objects": [], "faces": []}},
        {
            "operation_id": "op_4",
            "result": {"objects": [{"name": "tree"}], "faces": []},
        },
    ]

    batch_error = BatchProcessingException(
        "Batch processing completed with errors", failed_items, partial_results
    )

    context = {"batch_id": "batch_123", "total_items": 4}
    error_info = handle_processing_error(batch_error, "batch_processing", **context)

    print(f"Batch Error Info:")
    print(f"  Success count: {len(partial_results)}")
    print(f"  Failure count: {len(failed_items)}")
    print(f"  Partial success: {len(partial_results) > 0}")


async def main():
    """Run all error handling tests"""
    print("🧪 Testing Enhanced Error Handling System")
    print("=" * 50)

    try:
        await test_retry_decorators()
        test_error_classification()
        test_error_recovery_manager()
        test_batch_error_handling()

        print("\n" + "=" * 50)
        print("✅ All error handling tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
