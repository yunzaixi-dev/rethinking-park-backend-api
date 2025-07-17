"""
Production monitoring and health check service
Implements comprehensive monitoring for no-GPU environment
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None
import os

from config import settings
from services.cache_service import CacheService
from services.performance_optimizer import get_performance_optimizer

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Health check result"""

    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None


@dataclass
class SystemMetrics:
    """System performance metrics"""

    cpu_usage_percent: float
    memory_usage_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_connections: int
    load_average: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class APIMetrics:
    """API performance metrics"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    requests_per_minute: float = 0.0
    active_connections: int = 0
    vision_api_calls: int = 0
    cache_hit_rate: float = 0.0
    batch_operations_active: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class HealthChecker:
    """Comprehensive health checking system"""

    def __init__(self):
        self.checks = {}
        self.last_results = {}
        self._lock = threading.Lock()

    def register_check(self, name: str, check_func, timeout: float = 10.0):
        """Register a health check function"""
        self.checks[name] = {"func": check_func, "timeout": timeout}

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                service=name,
                status="unhealthy",
                response_time_ms=0.0,
                error_message=f"Health check '{name}' not found",
            )

        check_config = self.checks[name]
        start_time = time.time()

        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                check_config["func"](), timeout=check_config["timeout"]
            )

            response_time = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                return HealthCheckResult(
                    service=name,
                    status=result.get("status", "healthy"),
                    response_time_ms=response_time,
                    details=result.get("details", {}),
                    error_message=result.get("error"),
                )
            else:
                return HealthCheckResult(
                    service=name,
                    status="healthy" if result else "unhealthy",
                    response_time_ms=response_time,
                )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                service=name,
                status="unhealthy",
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Health check timed out after {check_config['timeout']}s",
            )
        except Exception as e:
            return HealthCheckResult(
                service=name,
                status="unhealthy",
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        tasks = []
        for name in self.checks:
            task = self.run_check(name)
            tasks.append((name, task))

        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result

                # Store last result
                with self._lock:
                    self.last_results[name] = result

            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = HealthCheckResult(
                    service=name,
                    status="unhealthy",
                    response_time_ms=0.0,
                    error_message=str(e),
                )

        return results

    def get_overall_status(self, results: Dict[str, HealthCheckResult]) -> str:
        """Determine overall system health status"""
        if not results:
            return "unhealthy"

        statuses = [result.status for result in results.values()]

        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"


class MetricsCollector:
    """System and application metrics collector"""

    def __init__(self):
        self.api_metrics = APIMetrics()
        self.request_times = deque(maxlen=1000)
        self.request_counts = defaultdict(int)
        self._lock = threading.Lock()

        # Initialize request tracking
        self.last_minute_requests = deque(maxlen=60)
        self.start_time = datetime.now()

    def record_request(self, success: bool = True, response_time_ms: float = 0.0):
        """Record API request metrics"""
        with self._lock:
            self.api_metrics.total_requests += 1

            if success:
                self.api_metrics.successful_requests += 1
            else:
                self.api_metrics.failed_requests += 1

            # Record response time
            if response_time_ms > 0:
                self.request_times.append(response_time_ms)
                if self.request_times:
                    self.api_metrics.average_response_time_ms = sum(
                        self.request_times
                    ) / len(self.request_times)

            # Track requests per minute
            now = datetime.now()
            self.last_minute_requests.append(now)

            # Clean old requests (older than 1 minute)
            cutoff = now - timedelta(minutes=1)
            while self.last_minute_requests and self.last_minute_requests[0] < cutoff:
                self.last_minute_requests.popleft()

            self.api_metrics.requests_per_minute = len(self.last_minute_requests)
            self.api_metrics.timestamp = now

    def record_vision_api_call(self):
        """Record Google Vision API call"""
        with self._lock:
            self.api_metrics.vision_api_calls += 1

    def update_cache_metrics(self, hit_rate: float):
        """Update cache performance metrics"""
        with self._lock:
            self.api_metrics.cache_hit_rate = hit_rate

    def update_batch_operations(self, active_count: int):
        """Update batch operations count"""
        with self._lock:
            self.api_metrics.batch_operations_active = active_count

    def get_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            if psutil:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)

                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_mb = memory.used / (1024 * 1024)
                memory_available_mb = memory.available / (1024 * 1024)

                # Disk usage
                disk = psutil.disk_usage("/")
                disk_percent = (disk.used / disk.total) * 100
                disk_free_gb = disk.free / (1024 * 1024 * 1024)

                # Network connections
                connections = len(psutil.net_connections())

                # Load average (Unix-like systems)
                load_avg = []
                try:
                    load_avg = list(os.getloadavg())
                except (OSError, AttributeError):
                    load_avg = [0.0, 0.0, 0.0]

                return SystemMetrics(
                    cpu_usage_percent=cpu_percent,
                    memory_usage_percent=memory_percent,
                    memory_used_mb=memory_used_mb,
                    memory_available_mb=memory_available_mb,
                    disk_usage_percent=disk_percent,
                    disk_free_gb=disk_free_gb,
                    network_connections=connections,
                    load_average=load_avg,
                )
            else:
                # Fallback metrics without psutil
                import gc
                import shutil

                # Basic disk usage
                disk_usage = shutil.disk_usage("/")
                disk_percent = (disk_usage.used / disk_usage.total) * 100
                disk_free_gb = disk_usage.free / (1024 * 1024 * 1024)

                # Load average (Unix-like systems)
                load_avg = []
                try:
                    load_avg = list(os.getloadavg())
                except (OSError, AttributeError):
                    load_avg = [0.0, 0.0, 0.0]

                # Estimate memory usage from garbage collection
                gc_objects = len(gc.get_objects())
                estimated_memory_mb = gc_objects / 1000.0  # Rough estimation

                return SystemMetrics(
                    cpu_usage_percent=0.0,  # Not available without psutil
                    memory_usage_percent=0.0,  # Not available without psutil
                    memory_used_mb=estimated_memory_mb,
                    memory_available_mb=1024.0,  # Default assumption
                    disk_usage_percent=disk_percent,
                    disk_free_gb=disk_free_gb,
                    network_connections=0,  # Not available without psutil
                    load_average=load_avg,
                )

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                network_connections=0,
            )

    def get_api_metrics(self) -> APIMetrics:
        """Get current API metrics"""
        with self._lock:
            return APIMetrics(
                total_requests=self.api_metrics.total_requests,
                successful_requests=self.api_metrics.successful_requests,
                failed_requests=self.api_metrics.failed_requests,
                average_response_time_ms=self.api_metrics.average_response_time_ms,
                requests_per_minute=self.api_metrics.requests_per_minute,
                active_connections=self.api_metrics.active_connections,
                vision_api_calls=self.api_metrics.vision_api_calls,
                cache_hit_rate=self.api_metrics.cache_hit_rate,
                batch_operations_active=self.api_metrics.batch_operations_active,
                timestamp=datetime.now(),
            )


class MonitoringService:
    """Main monitoring service"""

    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.is_running = False
        self.monitoring_task = None

        # Register default health checks
        self._register_default_health_checks()

    def _register_default_health_checks(self):
        """Register default health checks"""
        self.health_checker.register_check(
            "database", self._check_database, timeout=5.0
        )
        self.health_checker.register_check("cache", self._check_cache, timeout=3.0)
        self.health_checker.register_check(
            "vision_api", self._check_vision_api, timeout=10.0
        )
        self.health_checker.register_check("storage", self._check_storage, timeout=5.0)
        self.health_checker.register_check(
            "performance", self._check_performance, timeout=2.0
        )

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # For this implementation, we don't have a traditional database
            # Check if storage service is working
            from services.storage_service import storage_service

            # Simple connectivity test
            test_result = (
                await storage_service.health_check()
                if hasattr(storage_service, "health_check")
                else True
            )

            return {
                "status": "healthy" if test_result else "unhealthy",
                "details": {"type": "storage_service", "responsive": test_result},
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"type": "storage_service"},
            }

    async def _check_cache(self) -> Dict[str, Any]:
        """Check cache service health"""
        try:
            if not self.cache_service.is_enabled():
                return {
                    "status": "degraded",
                    "details": {"enabled": False, "message": "Cache service disabled"},
                }

            # Test cache operations
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.now().isoformat()}

            # Test write
            write_success = await self.cache_service.set(
                test_key, test_value, ttl_hours=1
            )
            if not write_success:
                return {
                    "status": "unhealthy",
                    "details": {"operation": "write", "success": False},
                }

            # Test read
            read_value = await self.cache_service.get(test_key)
            if read_value != test_value:
                return {
                    "status": "unhealthy",
                    "details": {"operation": "read", "success": False},
                }

            # Test delete
            delete_success = await self.cache_service.delete(test_key)

            # Get cache stats
            cache_stats = self.cache_service.get_stats()

            return {
                "status": "healthy",
                "details": {
                    "enabled": True,
                    "operations": {
                        "write": write_success,
                        "read": True,
                        "delete": delete_success,
                    },
                    "stats": cache_stats,
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"enabled": self.cache_service.is_enabled()},
            }

    async def _check_vision_api(self) -> Dict[str, Any]:
        """Check Google Vision API connectivity"""
        try:
            from services.vision_service import vision_service

            if not vision_service.is_enabled():
                return {
                    "status": "degraded",
                    "details": {"enabled": False, "message": "Vision API disabled"},
                }

            # Simple API connectivity test
            # Create a minimal test image (1x1 pixel)
            import base64
            import io

            from PIL import Image

            # Create minimal test image
            test_image = Image.new("RGB", (1, 1), color="white")
            img_buffer = io.BytesIO()
            test_image.save(img_buffer, format="JPEG")
            test_image_bytes = img_buffer.getvalue()

            # Test label detection (lightweight operation)
            start_time = time.time()
            labels = await vision_service.detect_labels(test_image_bytes)
            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "details": {
                    "enabled": True,
                    "response_time_ms": response_time,
                    "test_result": "success",
                    "labels_detected": len(labels) if labels else 0,
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"enabled": False},
            }

    async def _check_storage(self) -> Dict[str, Any]:
        """Check storage service health"""
        try:
            from services.gcs_service import gcs_service

            # Test GCS connectivity
            health_status = (
                await gcs_service.health_check()
                if hasattr(gcs_service, "health_check")
                else True
            )

            return {
                "status": "healthy" if health_status else "unhealthy",
                "details": {
                    "type": "google_cloud_storage",
                    "responsive": health_status,
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"type": "google_cloud_storage"},
            }

    async def _check_performance(self) -> Dict[str, Any]:
        """Check performance optimization service"""
        try:
            optimizer = await get_performance_optimizer()
            metrics = optimizer.get_performance_metrics()

            # Determine status based on performance metrics
            memory_pressure = metrics["memory_optimization"]["memory_pressure"]
            hit_rate = metrics["cache_performance"]["hit_rate"]
            avg_response_time = metrics["response_times"]["average_ms"]

            status = "healthy"
            if memory_pressure or hit_rate < 0.5 or avg_response_time > 5000:
                status = "degraded"

            return {
                "status": status,
                "details": {
                    "memory_pressure": memory_pressure,
                    "cache_hit_rate": hit_rate,
                    "average_response_time_ms": avg_response_time,
                    "optimization_active": True,
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": {"optimization_active": False},
            }

    async def start_monitoring(self):
        """Start continuous monitoring"""
        if not self.is_running:
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Monitoring service started")

    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring service stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect system metrics
                system_metrics = self.metrics_collector.get_system_metrics()

                # Update cache metrics
                if self.cache_service.is_enabled():
                    cache_stats = self.cache_service.get_stats()
                    hit_rate = cache_stats.get("hit_rate", 0.0)
                    self.metrics_collector.update_cache_metrics(hit_rate)

                # Log metrics periodically
                if int(time.time()) % 60 == 0:  # Every minute
                    logger.info(
                        f"System metrics: CPU={system_metrics.cpu_usage_percent:.1f}%, "
                        f"Memory={system_metrics.memory_usage_percent:.1f}%, "
                        f"Disk={system_metrics.disk_usage_percent:.1f}%"
                    )

                await asyncio.sleep(30)  # Monitor every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)  # Brief pause before retrying

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_results = await self.health_checker.run_all_checks()
        overall_status = self.health_checker.get_overall_status(health_results)

        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: {
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details,
                    "error": result.error_message,
                }
                for name, result in health_results.items()
            },
            "uptime_seconds": (
                datetime.now() - self.metrics_collector.start_time
            ).total_seconds(),
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system and API metrics"""
        system_metrics = self.metrics_collector.get_system_metrics()
        api_metrics = self.metrics_collector.get_api_metrics()

        # Get performance optimizer metrics
        try:
            optimizer = await get_performance_optimizer()
            performance_metrics = optimizer.get_performance_metrics()
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            performance_metrics = {}

        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_usage_percent": system_metrics.cpu_usage_percent,
                "memory_usage_percent": system_metrics.memory_usage_percent,
                "memory_used_mb": system_metrics.memory_used_mb,
                "memory_available_mb": system_metrics.memory_available_mb,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "disk_free_gb": system_metrics.disk_free_gb,
                "network_connections": system_metrics.network_connections,
                "load_average": system_metrics.load_average,
            },
            "api": {
                "total_requests": api_metrics.total_requests,
                "successful_requests": api_metrics.successful_requests,
                "failed_requests": api_metrics.failed_requests,
                "success_rate": (
                    api_metrics.successful_requests / max(1, api_metrics.total_requests)
                ),
                "average_response_time_ms": api_metrics.average_response_time_ms,
                "requests_per_minute": api_metrics.requests_per_minute,
                "vision_api_calls": api_metrics.vision_api_calls,
                "cache_hit_rate": api_metrics.cache_hit_rate,
                "batch_operations_active": api_metrics.batch_operations_active,
            },
            "performance": performance_metrics,
        }


# Global monitoring service instance
monitoring_service = None


async def get_monitoring_service() -> MonitoringService:
    """Get or create the global monitoring service instance"""
    global monitoring_service

    if monitoring_service is None:
        from services.cache_service import cache_service

        monitoring_service = MonitoringService(cache_service)
        await monitoring_service.start_monitoring()

    return monitoring_service
