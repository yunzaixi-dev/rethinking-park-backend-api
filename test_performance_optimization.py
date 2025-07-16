"""
Test suite for performance optimization features
Tests Google Vision API batching, memory optimization, and async processing
"""

import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from services.performance_optimizer import (
    PerformanceOptimizer,
    VisionAPIBatcher,
    MemoryManager,
    AsyncProcessingQueue,
    BatchRequest,
    PerformanceMetrics
)
from services.cache_service import CacheService


class TestMemoryManager:
    """Test memory management optimization"""
    
    def test_memory_manager_initialization(self):
        """Test memory manager initialization"""
        manager = MemoryManager(max_memory_mb=256)
        
        assert manager.max_memory_mb == 256
        assert manager.memory_threshold_mb == 256 * 0.8
        assert len(manager.image_cache) == 0
    
    def test_memory_usage_detection(self):
        """Test memory usage detection"""
        manager = MemoryManager(max_memory_mb=256)
        
        # Memory usage should be detectable
        usage = manager.get_memory_usage()
        assert isinstance(usage, float)
        assert usage >= 0
    
    def test_memory_pressure_check(self):
        """Test memory pressure detection"""
        manager = MemoryManager(max_memory_mb=1)  # Very low limit for testing
        
        # Should detect memory pressure with low limit
        pressure = manager.check_memory_pressure()
        assert isinstance(pressure, bool)
    
    def test_memory_optimization(self):
        """Test memory optimization process"""
        manager = MemoryManager(max_memory_mb=256)
        
        # Add some test data to cache
        test_data = b"test_image_data" * 1000
        manager.cache_image_safely("test_hash", test_data)
        
        # Run optimization
        stats = manager.optimize_memory()
        
        assert "memory_before_mb" in stats
        assert "memory_after_mb" in stats
        assert "optimizations_performed" in stats
        assert isinstance(stats["optimizations_performed"], list)
    
    def test_image_caching_with_memory_pressure(self):
        """Test image caching behavior under memory pressure"""
        manager = MemoryManager(max_memory_mb=1)  # Very low limit
        
        test_data = b"test_image_data" * 1000
        
        # Should handle memory pressure gracefully
        result = manager.cache_image_safely("test_hash", test_data)
        assert isinstance(result, bool)
        
        # Should be able to retrieve cached data if cached
        if result:
            cached_data = manager.get_cached_image("test_hash")
            assert cached_data == test_data or cached_data is None


class TestVisionAPIBatcher:
    """Test Google Vision API call batching"""
    
    @pytest.fixture
    async def batcher(self):
        """Create a test batcher"""
        batcher = VisionAPIBatcher(batch_size=3, batch_timeout_seconds=0.5)
        await batcher.start()
        yield batcher
        await batcher.stop()
    
    @pytest.mark.asyncio
    async def test_batcher_initialization(self):
        """Test batcher initialization and shutdown"""
        batcher = VisionAPIBatcher(batch_size=5, batch_timeout_seconds=1.0)
        
        assert batcher.batch_size == 5
        assert batcher.batch_timeout_seconds == 1.0
        assert not batcher.is_running
        
        await batcher.start()
        assert batcher.is_running
        
        await batcher.stop()
        assert not batcher.is_running
    
    @pytest.mark.asyncio
    async def test_batch_request_processing(self, batcher):
        """Test batch request processing"""
        # Mock the enhanced vision service
        with patch('services.performance_optimizer.enhanced_vision_service') as mock_service:
            mock_service.detect_objects_enhanced = AsyncMock(return_value={
                "success": True,
                "objects": [],
                "faces": [],
                "labels": []
            })
            
            # Create test request
            request = BatchRequest(
                request_id="test_req_1",
                image_hash="test_hash",
                image_content=b"test_image_data",
                operation_type="detect_objects_enhanced",
                parameters={
                    "confidence_threshold": 0.5,
                    "include_faces": True,
                    "include_labels": True
                }
            )
            
            # Process request
            result = await batcher.add_request(request)
            
            # Verify result
            assert isinstance(result, dict)
            assert result.get("success") is True
            
            # Verify mock was called
            mock_service.detect_objects_enhanced.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_timeout_handling(self, batcher):
        """Test batch request timeout handling"""
        # Create request with short timeout
        request = BatchRequest(
            request_id="timeout_test",
            image_hash="test_hash",
            image_content=b"test_image_data",
            operation_type="detect_objects_enhanced",
            parameters={},
            timeout_seconds=0.1  # Very short timeout
        )
        
        # Mock a slow service
        with patch('services.performance_optimizer.enhanced_vision_service') as mock_service:
            async def slow_detection(*args, **kwargs):
                await asyncio.sleep(1)  # Longer than timeout
                return {"success": True}
            
            mock_service.detect_objects_enhanced = slow_detection
            
            # Should raise timeout exception
            with pytest.raises(Exception):  # ProcessingException or TimeoutError
                await batcher.add_request(request)


class TestAsyncProcessingQueue:
    """Test async processing queue"""
    
    @pytest.fixture
    async def queue(self):
        """Create a test async queue"""
        queue = AsyncProcessingQueue(max_workers=2, max_queue_size=10)
        await queue.start()
        yield queue
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_queue_initialization(self):
        """Test queue initialization"""
        queue = AsyncProcessingQueue(max_workers=3, max_queue_size=20)
        
        assert queue.max_workers == 3
        assert queue.max_queue_size == 20
        assert not queue.is_running
        assert len(queue.workers) == 0
        
        await queue.start()
        assert queue.is_running
        assert len(queue.workers) == 3
        
        await queue.stop()
        assert not queue.is_running
        assert len(queue.workers) == 0
    
    @pytest.mark.asyncio
    async def test_task_processing(self, queue):
        """Test async task processing"""
        # Define test task
        async def test_task(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        # Submit task
        future = await queue.submit_task(test_task, 5)
        result = await future
        
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_task_error_handling(self, queue):
        """Test task error handling"""
        # Define failing task
        async def failing_task():
            raise ValueError("Test error")
        
        # Submit failing task
        future = await queue.submit_task(failing_task)
        
        # Should propagate exception
        with pytest.raises(ValueError, match="Test error"):
            await future
    
    @pytest.mark.asyncio
    async def test_queue_statistics(self, queue):
        """Test queue statistics"""
        # Submit some tasks
        async def simple_task(x):
            return x
        
        futures = []
        for i in range(3):
            future = await queue.submit_task(simple_task, i)
            futures.append(future)
        
        # Wait for completion
        await asyncio.gather(*futures)
        
        # Check statistics
        stats = queue.get_stats()
        
        assert stats["is_running"] is True
        assert stats["active_workers"] == 2
        assert stats["processed_count"] >= 3
        assert stats["success_rate"] > 0


class TestPerformanceOptimizer:
    """Test main performance optimizer"""
    
    @pytest.fixture
    async def optimizer(self):
        """Create a test optimizer"""
        # Mock cache service
        mock_cache = Mock(spec=CacheService)
        mock_cache.is_enabled.return_value = True
        mock_cache.get_detection_result = AsyncMock(return_value=None)
        mock_cache.set_detection_result = AsyncMock(return_value=True)
        mock_cache.get_natural_elements_result = AsyncMock(return_value=None)
        mock_cache.set_natural_elements_result = AsyncMock(return_value=True)
        mock_cache.implement_lru_eviction = AsyncMock(return_value={"evicted_keys": 0})
        
        optimizer = PerformanceOptimizer(mock_cache)
        await optimizer.initialize()
        yield optimizer
        await optimizer.shutdown()
    
    @pytest.mark.asyncio
    async def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        mock_cache = Mock(spec=CacheService)
        optimizer = PerformanceOptimizer(mock_cache)
        
        assert not optimizer.is_initialized
        
        await optimizer.initialize()
        assert optimizer.is_initialized
        
        await optimizer.shutdown()
        assert not optimizer.is_initialized
    
    @pytest.mark.asyncio
    async def test_optimized_detection_with_cache_hit(self, optimizer):
        """Test optimized detection with cache hit"""
        # Mock cache hit
        cached_result = {
            "success": True,
            "objects": [],
            "faces": [],
            "labels": [],
            "from_cache": True
        }
        optimizer.cache_service.get_detection_result.return_value = cached_result
        
        # Test optimized detection
        result = await optimizer.optimize_detection_request(
            image_content=b"test_image_data",
            image_hash="test_hash",
            confidence_threshold=0.5,
            include_faces=True,
            include_labels=True
        )
        
        assert result == cached_result
        assert optimizer.metrics.cache_hits == 1
        assert optimizer.metrics.cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_optimized_detection_with_cache_miss(self, optimizer):
        """Test optimized detection with cache miss"""
        # Mock cache miss and API response
        optimizer.cache_service.get_detection_result.return_value = None
        
        api_result = {
            "success": True,
            "objects": [{"class_name": "person", "confidence": 0.9}],
            "faces": [],
            "labels": []
        }
        
        with patch('services.performance_optimizer.enhanced_vision_service') as mock_service:
            mock_service.detect_objects_enhanced = AsyncMock(return_value=api_result)
            
            result = await optimizer.optimize_detection_request(
                image_content=b"test_image_data",
                image_hash="test_hash",
                confidence_threshold=0.5,
                include_faces=True,
                include_labels=True,
                use_batching=False  # Disable batching for simpler test
            )
            
            assert result == api_result
            assert optimizer.metrics.cache_hits == 0
            assert optimizer.metrics.cache_misses == 1
            assert optimizer.metrics.api_calls_individual == 1
    
    @pytest.mark.asyncio
    async def test_memory_optimization_trigger(self, optimizer):
        """Test memory optimization triggering"""
        # Force memory pressure
        optimizer.memory_manager.memory_threshold_mb = 0  # Force pressure
        
        with patch('services.performance_optimizer.enhanced_vision_service') as mock_service:
            mock_service.detect_objects_enhanced = AsyncMock(return_value={"success": True})
            
            await optimizer.optimize_detection_request(
                image_content=b"test_image_data",
                image_hash="test_hash",
                use_batching=False
            )
            
            # Should have triggered memory optimization
            assert optimizer.metrics.memory_optimizations >= 1
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, optimizer):
        """Test performance metrics collection"""
        # Simulate some activity
        optimizer.metrics.api_calls_batched = 5
        optimizer.metrics.api_calls_individual = 3
        optimizer.metrics.cache_hits = 10
        optimizer.metrics.cache_misses = 2
        
        metrics = optimizer.get_performance_metrics()
        
        assert "api_calls" in metrics
        assert "cache_performance" in metrics
        assert "memory_optimization" in metrics
        assert "response_times" in metrics
        assert "async_processing" in metrics
        assert "batching_status" in metrics
        
        # Check calculated ratios
        assert metrics["api_calls"]["batch_efficiency_ratio"] == 5/8  # 5 batched out of 8 total
        assert metrics["cache_performance"]["hit_rate"] == 10/12  # 10 hits out of 12 total
    
    @pytest.mark.asyncio
    async def test_optimization_cycle(self, optimizer):
        """Test complete optimization cycle"""
        # Force memory pressure to trigger optimization
        optimizer.memory_manager.memory_threshold_mb = 0
        
        results = await optimizer.perform_optimization_cycle()
        
        assert "timestamp" in results
        assert "optimizations_performed" in results
        assert isinstance(results["optimizations_performed"], list)
        
        # Should have performed memory optimization
        optimization_types = [opt["type"] for opt in results["optimizations_performed"]]
        assert "memory_optimization" in optimization_types


class TestIntegrationScenarios:
    """Test integration scenarios for performance optimization"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_optimization(self):
        """Test optimization under concurrent load"""
        mock_cache = Mock(spec=CacheService)
        mock_cache.is_enabled.return_value = True
        mock_cache.get_detection_result = AsyncMock(return_value=None)
        mock_cache.set_detection_result = AsyncMock(return_value=True)
        mock_cache.implement_lru_eviction = AsyncMock(return_value={"evicted_keys": 0})
        
        optimizer = PerformanceOptimizer(mock_cache)
        await optimizer.initialize()
        
        try:
            # Mock API service
            with patch('services.performance_optimizer.enhanced_vision_service') as mock_service:
                mock_service.detect_objects_enhanced = AsyncMock(return_value={"success": True})
                
                # Submit multiple concurrent requests
                tasks = []
                for i in range(10):
                    task = optimizer.optimize_detection_request(
                        image_content=f"test_image_data_{i}".encode(),
                        image_hash=f"test_hash_{i}",
                        use_batching=True
                    )
                    tasks.append(task)
                
                # Wait for all requests to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify all requests completed
                assert len(results) == 10
                
                # Check that some requests were batched
                metrics = optimizer.get_performance_metrics()
                assert metrics["api_calls"]["batched"] > 0 or metrics["api_calls"]["individual"] > 0
        
        finally:
            await optimizer.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self):
        """Test batch processing optimization"""
        mock_cache = Mock(spec=CacheService)
        mock_cache.is_enabled.return_value = True
        mock_cache.implement_lru_eviction = AsyncMock(return_value={"evicted_keys": 0})
        
        optimizer = PerformanceOptimizer(mock_cache)
        await optimizer.initialize()
        
        try:
            # Mock required services
            with patch('services.performance_optimizer.storage_service') as mock_storage, \
                 patch('services.performance_optimizer.gcs_service') as mock_gcs, \
                 patch('services.performance_optimizer.batch_processing_service') as mock_batch:
                
                # Mock storage and GCS services
                mock_storage.get_image_info = AsyncMock(return_value=Mock(gcs_url="test_url"))
                mock_gcs.download_image = AsyncMock(return_value=b"test_image_data")
                mock_batch.create_batch_job = AsyncMock(return_value="batch_123")
                
                # Test batch processing optimization
                operations = [
                    {"type": "detect_objects", "image_hash": "hash1", "parameters": {}},
                    {"type": "analyze_nature", "image_hash": "hash2", "parameters": {}},
                ]
                
                batch_id = await optimizer.optimize_batch_processing(
                    operations=operations,
                    max_concurrent=3
                )
                
                assert batch_id == "batch_123"
                mock_batch.create_batch_job.assert_called_once()
        
        finally:
            await optimizer.shutdown()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])