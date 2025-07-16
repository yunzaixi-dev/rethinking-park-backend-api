"""
Simple test for performance optimization functionality
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

def test_memory_manager_basic():
    """Test basic memory manager functionality"""
    from services.performance_optimizer import MemoryManager
    
    manager = MemoryManager(max_memory_mb=256)
    
    # Test initialization
    assert manager.max_memory_mb == 256
    assert manager.memory_threshold_mb == 256 * 0.8
    
    # Test memory usage detection
    usage = manager.get_memory_usage()
    assert isinstance(usage, float)
    assert usage >= 0
    
    # Test memory optimization
    stats = manager.optimize_memory()
    assert "memory_before_mb" in stats
    assert "optimizations_performed" in stats
    assert isinstance(stats["optimizations_performed"], list)

def test_performance_metrics():
    """Test performance metrics data structure"""
    from services.performance_optimizer import PerformanceMetrics
    
    metrics = PerformanceMetrics()
    
    # Test default values
    assert metrics.api_calls_batched == 0
    assert metrics.api_calls_individual == 0
    assert metrics.cache_hits == 0
    assert metrics.cache_misses == 0
    assert metrics.average_response_time_ms == 0.0

@pytest.mark.asyncio
async def test_async_processing_queue():
    """Test async processing queue basic functionality"""
    from services.performance_optimizer import AsyncProcessingQueue
    
    queue = AsyncProcessingQueue(max_workers=2, max_queue_size=10)
    
    # Test initialization
    assert queue.max_workers == 2
    assert queue.max_queue_size == 10
    assert not queue.is_running
    
    # Start queue
    await queue.start()
    assert queue.is_running
    assert len(queue.workers) == 2
    
    # Test simple task
    async def simple_task(value):
        return value * 2
    
    future = await queue.submit_task(simple_task, 5)
    result = await future
    assert result == 10
    
    # Stop queue
    await queue.stop()
    assert not queue.is_running

@pytest.mark.asyncio
async def test_vision_api_batcher():
    """Test Vision API batcher basic functionality"""
    from services.performance_optimizer import VisionAPIBatcher
    
    batcher = VisionAPIBatcher(batch_size=3, batch_timeout_seconds=0.5)
    
    # Test initialization
    assert batcher.batch_size == 3
    assert batcher.batch_timeout_seconds == 0.5
    assert not batcher.is_running
    
    # Start batcher
    await batcher.start()
    assert batcher.is_running
    
    # Stop batcher
    await batcher.stop()
    assert not batcher.is_running

@pytest.mark.asyncio
async def test_performance_optimizer_basic():
    """Test performance optimizer basic functionality"""
    from services.performance_optimizer import PerformanceOptimizer
    from services.cache_service import CacheService
    
    # Mock cache service
    mock_cache = Mock(spec=CacheService)
    mock_cache.is_enabled.return_value = True
    mock_cache.get_detection_result = AsyncMock(return_value=None)
    mock_cache.set_detection_result = AsyncMock(return_value=True)
    mock_cache.implement_lru_eviction = AsyncMock(return_value={"evicted_keys": 0})
    
    optimizer = PerformanceOptimizer(mock_cache)
    
    # Test initialization
    assert not optimizer.is_initialized
    
    await optimizer.initialize()
    assert optimizer.is_initialized
    
    # Test metrics collection
    metrics = optimizer.get_performance_metrics()
    assert "api_calls" in metrics
    assert "cache_performance" in metrics
    assert "memory_optimization" in metrics
    
    await optimizer.shutdown()
    assert not optimizer.is_initialized

if __name__ == "__main__":
    # Run simple tests
    import sys
    import traceback
    
    def run_test(test_func):
        try:
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func())
            else:
                test_func()
            print(f"✅ {test_func.__name__} passed")
            return True
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            traceback.print_exc()
            return False
    
    tests = [
        test_memory_manager_basic,
        test_performance_metrics,
        test_async_processing_queue,
        test_vision_api_batcher,
        test_performance_optimizer_basic
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if run_test(test):
            passed += 1
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All performance optimization tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)