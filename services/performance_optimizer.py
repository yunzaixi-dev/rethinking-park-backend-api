"""
Performance optimization service for no-GPU environment
Implements Google Vision API call batching, memory optimization, and async processing
"""

import asyncio
import gc
import logging
import threading
import time
import uuid
import weakref
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None
import os

from services.cache_service import CacheService
from services.enhanced_vision_service import enhanced_vision_service
from services.error_handling import (
    ProcessingException,
    VisionAPIException,
    handle_processing_error,
    retry_processing,
)

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """Batched API request for optimization"""

    request_id: str
    image_hash: str
    image_content: bytes
    operation_type: str
    parameters: Dict[str, Any]
    callback: Optional[Callable] = None
    priority: int = 1  # 1=low, 2=medium, 3=high
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 30


@dataclass
class PerformanceMetrics:
    """Performance monitoring metrics"""

    api_calls_batched: int = 0
    api_calls_individual: int = 0
    memory_optimizations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_response_time_ms: float = 0.0
    peak_memory_usage_mb: float = 0.0
    concurrent_operations: int = 0
    batch_efficiency_ratio: float = 0.0


class MemoryManager:
    """Memory optimization manager for image processing"""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.current_memory_mb = 0.0
        self.memory_threshold_mb = max_memory_mb * 0.8  # 80% threshold
        self.image_cache = weakref.WeakValueDictionary()
        self._lock = threading.Lock()

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            if psutil:
                process = psutil.Process(os.getpid())
                return process.memory_info().rss / (1024 * 1024)
            else:
                # Fallback: use a simple estimation based on garbage collection
                import sys

                return sys.getsizeof(gc.get_objects()) / (1024 * 1024)
        except Exception:
            return 0.0

    def check_memory_pressure(self) -> bool:
        """Check if memory usage is approaching limits"""
        current_memory = self.get_memory_usage()
        return current_memory > self.memory_threshold_mb

    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization when under pressure"""
        optimization_stats = {
            "memory_before_mb": self.get_memory_usage(),
            "optimizations_performed": [],
            "memory_freed_mb": 0.0,
        }

        try:
            # Force garbage collection
            collected = gc.collect()
            optimization_stats["optimizations_performed"].append(
                f"garbage_collection: {collected} objects"
            )

            # Clear weak references cache
            with self._lock:
                cache_size_before = len(self.image_cache)
                self.image_cache.clear()
                optimization_stats["optimizations_performed"].append(
                    f"cleared_image_cache: {cache_size_before} items"
                )

            # Force another garbage collection after cache clear
            gc.collect()

            memory_after = self.get_memory_usage()
            optimization_stats["memory_after_mb"] = memory_after
            optimization_stats["memory_freed_mb"] = (
                optimization_stats["memory_before_mb"] - memory_after
            )

            logger.info(
                f"Memory optimization completed: freed {optimization_stats['memory_freed_mb']:.2f}MB"
            )

        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            optimization_stats["error"] = str(e)

        return optimization_stats

    def cache_image_safely(self, image_hash: str, image_content: bytes) -> bool:
        """Cache image content with memory pressure checks"""
        if self.check_memory_pressure():
            self.optimize_memory()

        # Only cache if we have memory headroom
        if not self.check_memory_pressure():
            with self._lock:
                self.image_cache[image_hash] = image_content
                return True

        return False

    def get_cached_image(self, image_hash: str) -> Optional[bytes]:
        """Get cached image content"""
        with self._lock:
            return self.image_cache.get(image_hash)


class VisionAPIBatcher:
    """Batches Google Vision API calls for improved efficiency"""

    def __init__(self, batch_size: int = 5, batch_timeout_seconds: float = 2.0):
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.pending_requests: Dict[str, List[BatchRequest]] = defaultdict(list)
        self.request_futures: Dict[str, asyncio.Future] = {}
        self._lock = threading.Lock()
        self.batch_processor_task = None
        self.is_running = False

    async def start(self):
        """Start the batch processor"""
        if not self.is_running:
            self.is_running = True
            self.batch_processor_task = asyncio.create_task(
                self._batch_processor_loop()
            )
            logger.info("Vision API batcher started")

    async def stop(self):
        """Stop the batch processor"""
        self.is_running = False
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
            try:
                await self.batch_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Vision API batcher stopped")

    async def add_request(self, request: BatchRequest) -> Any:
        """Add a request to the batch queue"""
        future = asyncio.Future()

        with self._lock:
            self.pending_requests[request.operation_type].append(request)
            self.request_futures[request.request_id] = future

        # Trigger immediate processing if batch is full
        if len(self.pending_requests[request.operation_type]) >= self.batch_size:
            asyncio.create_task(self._process_batch(request.operation_type))

        try:
            # Wait for result with timeout
            return await asyncio.wait_for(future, timeout=request.timeout_seconds)
        except asyncio.TimeoutError:
            # Clean up on timeout
            with self._lock:
                if request.request_id in self.request_futures:
                    del self.request_futures[request.request_id]
            raise ProcessingException(
                f"Batch request timed out after {request.timeout_seconds}s",
                operation="batch_timeout",
                recoverable=True,
            )

    async def _batch_processor_loop(self):
        """Main batch processing loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.batch_timeout_seconds)

                # Process all pending batches
                operation_types = list(self.pending_requests.keys())
                for operation_type in operation_types:
                    if self.pending_requests[operation_type]:
                        await self._process_batch(operation_type)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processor loop error: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

    async def _process_batch(self, operation_type: str):
        """Process a batch of requests for a specific operation type"""
        with self._lock:
            if not self.pending_requests[operation_type]:
                return

            # Get batch of requests (up to batch_size)
            batch = self.pending_requests[operation_type][: self.batch_size]
            self.pending_requests[operation_type] = self.pending_requests[
                operation_type
            ][self.batch_size :]

        if not batch:
            return

        logger.debug(f"Processing batch of {len(batch)} {operation_type} requests")

        try:
            # Process batch based on operation type
            if operation_type == "detect_objects_enhanced":
                await self._process_detection_batch(batch)
            elif operation_type == "analyze_natural_elements":
                await self._process_natural_elements_batch(batch)
            elif operation_type == "detect_labels":
                await self._process_labels_batch(batch)
            else:
                # Fallback to individual processing
                await self._process_individual_batch(batch)

        except Exception as e:
            logger.error(f"Batch processing failed for {operation_type}: {e}")
            # Set error for all requests in batch
            for request in batch:
                future = self.request_futures.get(request.request_id)
                if future and not future.done():
                    future.set_exception(e)

    async def _process_detection_batch(self, batch: List[BatchRequest]):
        """Process a batch of object detection requests"""
        # Group by similar parameters for more efficient batching
        param_groups = defaultdict(list)

        for request in batch:
            params = request.parameters
            key = (
                params.get("confidence_threshold", 0.5),
                params.get("include_faces", True),
                params.get("include_labels", True),
            )
            param_groups[key].append(request)

        # Process each parameter group
        for param_key, group_requests in param_groups.items():
            confidence_threshold, include_faces, include_labels = param_key

            # Process requests in parallel within the group
            tasks = []
            for request in group_requests:
                task = self._process_single_detection_request(
                    request, confidence_threshold, include_faces, include_labels
                )
                tasks.append(task)

            # Wait for all tasks in the group
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_detection_request(
        self,
        request: BatchRequest,
        confidence_threshold: float,
        include_faces: bool,
        include_labels: bool,
    ):
        """Process a single detection request within a batch"""
        try:
            result = await enhanced_vision_service.detect_objects_enhanced(
                image_content=request.image_content,
                image_hash=request.image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels,
            )

            # Set result for the request
            future = self.request_futures.get(request.request_id)
            if future and not future.done():
                future.set_result(result)

        except Exception as e:
            future = self.request_futures.get(request.request_id)
            if future and not future.done():
                future.set_exception(e)
        finally:
            # Clean up
            if request.request_id in self.request_futures:
                del self.request_futures[request.request_id]

    async def _process_natural_elements_batch(self, batch: List[BatchRequest]):
        """Process a batch of natural elements analysis requests"""
        tasks = []
        for request in batch:
            task = self._process_single_natural_elements_request(request)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_natural_elements_request(self, request: BatchRequest):
        """Process a single natural elements request within a batch"""
        try:
            result = await enhanced_vision_service.analyze_natural_elements(
                image_content=request.image_content
            )

            future = self.request_futures.get(request.request_id)
            if future and not future.done():
                future.set_result(result)

        except Exception as e:
            future = self.request_futures.get(request.request_id)
            if future and not future.done():
                future.set_exception(e)
        finally:
            if request.request_id in self.request_futures:
                del self.request_futures[request.request_id]

    async def _process_labels_batch(self, batch: List[BatchRequest]):
        """Process a batch of label detection requests"""
        tasks = []
        for request in batch:
            task = self._process_single_labels_request(request)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_labels_request(self, request: BatchRequest):
        """Process a single label detection request within a batch"""
        try:
            from services.vision_service import vision_service

            result = await vision_service.detect_labels(request.image_content)

            future = self.request_futures.get(request.request_id)
            if future and not future.done():
                future.set_result(result)

        except Exception as e:
            future = self.request_futures.get(request.request_id)
            if future and not future.done():
                future.set_exception(e)
        finally:
            if request.request_id in self.request_futures:
                del self.request_futures[request.request_id]

    async def _process_individual_batch(self, batch: List[BatchRequest]):
        """Fallback to individual processing for unsupported batch operations"""
        for request in batch:
            try:
                # This is a fallback - in practice, all operations should have batch handlers
                logger.warning(
                    f"No batch handler for operation type: {request.operation_type}"
                )

                future = self.request_futures.get(request.request_id)
                if future and not future.done():
                    future.set_exception(
                        ProcessingException(
                            f"Batch processing not supported for {request.operation_type}",
                            operation="batch_fallback",
                            recoverable=False,
                        )
                    )
            finally:
                if request.request_id in self.request_futures:
                    del self.request_futures[request.request_id]


class AsyncProcessingQueue:
    """Async processing queue for batch operations"""

    def __init__(self, max_workers: int = 5, max_queue_size: int = 100):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.workers = []
        self.is_running = False
        self.processed_count = 0
        self.failed_count = 0

    async def start(self):
        """Start the async processing workers"""
        if not self.is_running:
            self.is_running = True
            self.workers = [
                asyncio.create_task(self._worker(f"worker-{i}"))
                for i in range(self.max_workers)
            ]
            logger.info(f"Started {self.max_workers} async processing workers")

    async def stop(self):
        """Stop the async processing workers"""
        self.is_running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("Stopped async processing workers")

    async def submit_task(self, task_func: Callable, *args, **kwargs) -> asyncio.Future:
        """Submit a task for async processing"""
        if self.queue.full():
            raise ProcessingException(
                "Processing queue is full", operation="queue_submit", recoverable=True
            )

        future = asyncio.Future()
        task_item = (task_func, args, kwargs, future)

        await self.queue.put(task_item)
        return future

    async def _worker(self, worker_name: str):
        """Worker coroutine for processing tasks"""
        logger.debug(f"Started async worker: {worker_name}")

        while self.is_running:
            try:
                # Get task from queue with timeout
                task_item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                task_func, args, kwargs, future = task_item

                try:
                    # Execute the task
                    if asyncio.iscoroutinefunction(task_func):
                        result = await task_func(*args, **kwargs)
                    else:
                        result = task_func(*args, **kwargs)

                    # Set the result
                    if not future.done():
                        future.set_result(result)

                    self.processed_count += 1

                except Exception as e:
                    # Set the exception
                    if not future.done():
                        future.set_exception(e)

                    self.failed_count += 1
                    logger.error(f"Task failed in {worker_name}: {e}")

                finally:
                    self.queue.task_done()

            except asyncio.TimeoutError:
                # Normal timeout, continue
                continue
            except asyncio.CancelledError:
                # Worker cancelled
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.debug(f"Stopped async worker: {worker_name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get processing queue statistics"""
        return {
            "is_running": self.is_running,
            "active_workers": len(self.workers),
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.failed_count)
                if (self.processed_count + self.failed_count) > 0
                else 0.0
            ),
        }


class PerformanceOptimizer:
    """Main performance optimization service"""

    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.memory_manager = MemoryManager(max_memory_mb=512)
        self.api_batcher = VisionAPIBatcher(batch_size=5, batch_timeout_seconds=2.0)
        self.async_queue = AsyncProcessingQueue(max_workers=5, max_queue_size=100)
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()
        self.is_initialized = False

        # Performance monitoring
        self.response_times = deque(maxlen=100)  # Keep last 100 response times
        self.last_optimization_time = datetime.now()

    async def initialize(self):
        """Initialize the performance optimizer"""
        if not self.is_initialized:
            await self.api_batcher.start()
            await self.async_queue.start()
            self.is_initialized = True
            logger.info("Performance optimizer initialized")

    async def shutdown(self):
        """Shutdown the performance optimizer"""
        if self.is_initialized:
            await self.api_batcher.stop()
            await self.async_queue.stop()
            self.is_initialized = False
            logger.info("Performance optimizer shutdown")

    async def optimize_detection_request(
        self,
        image_content: bytes,
        image_hash: str,
        confidence_threshold: float = 0.5,
        include_faces: bool = True,
        include_labels: bool = True,
        use_batching: bool = True,
    ) -> Dict[str, Any]:
        """Optimized object detection with caching and batching"""
        start_time = time.time()

        try:
            # Check cache first
            cached_result = await self.cache_service.get_detection_result(
                image_hash=image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels,
            )

            if cached_result:
                with self._lock:
                    self.metrics.cache_hits += 1

                self._record_response_time(time.time() - start_time)
                return cached_result

            with self._lock:
                self.metrics.cache_misses += 1

            # Memory optimization check
            if self.memory_manager.check_memory_pressure():
                self.memory_manager.optimize_memory()
                with self._lock:
                    self.metrics.memory_optimizations += 1

            # Use batching if enabled and beneficial
            if use_batching and self._should_use_batching():
                result = await self._process_with_batching(
                    image_content,
                    image_hash,
                    "detect_objects_enhanced",
                    {
                        "confidence_threshold": confidence_threshold,
                        "include_faces": include_faces,
                        "include_labels": include_labels,
                    },
                )
                with self._lock:
                    self.metrics.api_calls_batched += 1
            else:
                # Direct API call
                result = await enhanced_vision_service.detect_objects_enhanced(
                    image_content=image_content,
                    image_hash=image_hash,
                    confidence_threshold=confidence_threshold,
                    include_faces=include_faces,
                    include_labels=include_labels,
                )
                with self._lock:
                    self.metrics.api_calls_individual += 1

            # Cache the result
            await self.cache_service.set_detection_result(
                image_hash=image_hash,
                result=result,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels,
            )

            self._record_response_time(time.time() - start_time)
            return result

        except Exception as e:
            self._record_response_time(time.time() - start_time)
            raise

    async def optimize_natural_elements_analysis(
        self,
        image_content: bytes,
        image_hash: str,
        analysis_depth: str = "comprehensive",
        use_batching: bool = True,
    ) -> Dict[str, Any]:
        """Optimized natural elements analysis"""
        start_time = time.time()

        try:
            # Check cache first
            cached_result = await self.cache_service.get_natural_elements_result(
                image_hash=image_hash, analysis_depth=analysis_depth
            )

            if cached_result:
                with self._lock:
                    self.metrics.cache_hits += 1

                self._record_response_time(time.time() - start_time)
                return cached_result

            with self._lock:
                self.metrics.cache_misses += 1

            # Memory optimization check
            if self.memory_manager.check_memory_pressure():
                self.memory_manager.optimize_memory()
                with self._lock:
                    self.metrics.memory_optimizations += 1

            # Use batching if enabled
            if use_batching and self._should_use_batching():
                result = await self._process_with_batching(
                    image_content,
                    image_hash,
                    "analyze_natural_elements",
                    {"analysis_depth": analysis_depth},
                )
                with self._lock:
                    self.metrics.api_calls_batched += 1
            else:
                # Direct API call
                result = await enhanced_vision_service.analyze_natural_elements(
                    image_content=image_content
                )
                with self._lock:
                    self.metrics.api_calls_individual += 1

            # Cache the result
            await self.cache_service.set_natural_elements_result(
                image_hash=image_hash, result=result, analysis_depth=analysis_depth
            )

            self._record_response_time(time.time() - start_time)
            return result

        except Exception as e:
            self._record_response_time(time.time() - start_time)
            raise

    async def optimize_batch_processing(
        self, operations: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> str:
        """Optimized batch processing with async queue"""
        try:
            # Use async queue for better resource management
            batch_tasks = []

            for operation in operations:
                task_future = await self.async_queue.submit_task(
                    self._process_batch_operation, operation
                )
                batch_tasks.append(task_future)

            # Process with concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_semaphore(task_future):
                async with semaphore:
                    return await task_future

            # Wait for all tasks
            results = await asyncio.gather(
                *[process_with_semaphore(task) for task in batch_tasks],
                return_exceptions=True,
            )

            # Create batch job using existing batch processing service
            from services.batch_processing_service import batch_processing_service

            batch_id = await batch_processing_service.create_batch_job(
                operations=operations, max_concurrent_operations=max_concurrent
            )

            return batch_id

        except Exception as e:
            logger.error(f"Optimized batch processing failed: {e}")
            raise

    async def _process_with_batching(
        self,
        image_content: bytes,
        image_hash: str,
        operation_type: str,
        parameters: Dict[str, Any],
    ) -> Any:
        """Process request using API batching"""
        request = BatchRequest(
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            image_hash=image_hash,
            image_content=image_content,
            operation_type=operation_type,
            parameters=parameters,
            priority=2,  # Medium priority
            timeout_seconds=30,
        )

        return await self.api_batcher.add_request(request)

    async def _process_batch_operation(
        self, operation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single batch operation with optimization"""
        operation_type = operation.get("type")
        image_hash = operation.get("image_hash")
        parameters = operation.get("parameters", {})

        # Get image content
        from services.gcs_service import gcs_service
        from services.storage_service import storage_service

        image_info = await storage_service.get_image_info(image_hash)
        if not image_info:
            raise ValueError(f"Image not found: {image_hash}")

        image_content = await gcs_service.download_image(image_info.gcs_url)

        # Process based on operation type with optimization
        if operation_type == "detect_objects":
            return await self.optimize_detection_request(
                image_content=image_content, image_hash=image_hash, **parameters
            )
        elif operation_type == "analyze_nature":
            return await self.optimize_natural_elements_analysis(
                image_content=image_content, image_hash=image_hash, **parameters
            )
        else:
            # Fallback to non-optimized processing
            from services.batch_processing_service import batch_processing_service

            handler = batch_processing_service.operation_handlers.get(operation_type)
            if handler:
                return await handler(image_hash, parameters)
            else:
                raise ValueError(f"Unknown operation type: {operation_type}")

    def _should_use_batching(self) -> bool:
        """Determine if batching should be used based on current load"""
        # Use batching if we have multiple concurrent operations
        with self._lock:
            concurrent_ops = self.metrics.concurrent_operations

        # Also consider recent response times
        if len(self.response_times) > 10:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            # Use batching if average response time is high (> 2 seconds)
            return concurrent_ops > 1 or avg_response_time > 2.0

        return concurrent_ops > 1

    def _record_response_time(self, response_time: float):
        """Record response time for performance monitoring"""
        with self._lock:
            self.response_times.append(response_time)

            # Update average response time
            if self.response_times:
                self.metrics.average_response_time_ms = (
                    sum(self.response_times) / len(self.response_times) * 1000
                )

            # Update peak memory usage
            current_memory = self.memory_manager.get_memory_usage()
            if current_memory > self.metrics.peak_memory_usage_mb:
                self.metrics.peak_memory_usage_mb = current_memory

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        with self._lock:
            metrics_dict = {
                "api_calls": {
                    "batched": self.metrics.api_calls_batched,
                    "individual": self.metrics.api_calls_individual,
                    "batch_efficiency_ratio": (
                        self.metrics.api_calls_batched
                        / max(
                            1,
                            self.metrics.api_calls_batched
                            + self.metrics.api_calls_individual,
                        )
                    ),
                },
                "cache_performance": {
                    "hits": self.metrics.cache_hits,
                    "misses": self.metrics.cache_misses,
                    "hit_rate": (
                        self.metrics.cache_hits
                        / max(1, self.metrics.cache_hits + self.metrics.cache_misses)
                    ),
                },
                "memory_optimization": {
                    "optimizations_performed": self.metrics.memory_optimizations,
                    "current_usage_mb": self.memory_manager.get_memory_usage(),
                    "peak_usage_mb": self.metrics.peak_memory_usage_mb,
                    "memory_pressure": self.memory_manager.check_memory_pressure(),
                },
                "response_times": {
                    "average_ms": self.metrics.average_response_time_ms,
                    "recent_samples": len(self.response_times),
                    "current_concurrent_operations": self.metrics.concurrent_operations,
                },
                "async_processing": self.async_queue.get_stats(),
                "batching_status": {
                    "is_active": self.api_batcher.is_running,
                    "pending_requests": sum(
                        len(reqs) for reqs in self.api_batcher.pending_requests.values()
                    ),
                },
            }

        return metrics_dict

    async def perform_optimization_cycle(self) -> Dict[str, Any]:
        """Perform a complete optimization cycle"""
        optimization_results = {
            "timestamp": datetime.now().isoformat(),
            "optimizations_performed": [],
        }

        try:
            # Memory optimization
            if self.memory_manager.check_memory_pressure():
                memory_stats = self.memory_manager.optimize_memory()
                optimization_results["optimizations_performed"].append(
                    {"type": "memory_optimization", "stats": memory_stats}
                )

            # Cache optimization
            if self.cache_service.is_enabled():
                cache_stats = await self.cache_service.implement_lru_eviction(
                    max_memory_mb=100
                )
                optimization_results["optimizations_performed"].append(
                    {"type": "cache_eviction", "stats": cache_stats}
                )

            # Update last optimization time
            self.last_optimization_time = datetime.now()

            logger.info(
                f"Optimization cycle completed: {len(optimization_results['optimizations_performed'])} optimizations"
            )

        except Exception as e:
            logger.error(f"Optimization cycle failed: {e}")
            optimization_results["error"] = str(e)

        return optimization_results


# Global performance optimizer instance
performance_optimizer = None


async def get_performance_optimizer() -> PerformanceOptimizer:
    """Get or create the global performance optimizer instance"""
    global performance_optimizer

    if performance_optimizer is None:
        from services.cache_service import cache_service

        performance_optimizer = PerformanceOptimizer(cache_service)
        await performance_optimizer.initialize()

    return performance_optimizer
