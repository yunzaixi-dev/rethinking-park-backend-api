"""
Redis cache service module.

This module provides Redis caching capabilities based on the base service architecture.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import redis

from app.config.settings import get_settings
from app.services.base import AsyncService, ServiceConfig

logger = logging.getLogger(__name__)


class RedisCacheService(AsyncService):
    """Enhanced Redis caching service for image processing results"""

    def __init__(self, config: ServiceConfig = None):
        if config is None:
            config = ServiceConfig(name="redis_cache", enabled=True, timeout=10.0)
        super().__init__(config)

        self.redis_client = None
        self._redis_enabled = False
        self._lock = None  # Will be initialized in async context

        # Cache configuration for different result types
        self.cache_config = {
            "detection_results": {"ttl_hours": 24, "prefix": "detect"},
            "segmentation_masks": {"ttl_hours": 168, "prefix": "segment"},  # 7 days
            "extraction_results": {"ttl_hours": 720, "prefix": "extract"},  # 30 days
            "batch_processing": {"ttl_hours": 1, "prefix": "batch"},
            "natural_elements": {"ttl_hours": 48, "prefix": "nature"},
            "face_detection": {"ttl_hours": 24, "prefix": "faces"},
            "annotations": {"ttl_hours": 72, "prefix": "annotate"},  # 3 days
        }

        # LRU cache statistics
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_operations": 0,
        }

    async def _initialize(self):
        """Initialize Redis cache service"""
        try:
            settings = get_settings()

            if not getattr(settings, "REDIS_ENABLED", False):
                self.log_operation(
                    "Redis caching functionality disabled by configuration"
                )
                self._redis_enabled = False
                return

            self.log_operation("Initializing Redis cache service")

            # Parse Redis URL
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)

            # Test connection
            self.redis_client.ping()
            self._redis_enabled = True

            self.log_operation(
                "Enhanced Redis caching service initialized successfully"
            )

        except Exception as e:
            self.log_error("_initialize", e)
            self._redis_enabled = False
            # Don't raise exception - service can work in disabled mode

    async def _health_check(self):
        """Health check for Redis cache service"""
        if not self._redis_enabled:
            # Service is healthy but disabled
            return

        try:
            # Test Redis connection
            self.redis_client.ping()
        except Exception as e:
            raise Exception(f"Redis connection failed: {e}")

    def is_enabled(self) -> bool:
        """Check if cache service is available"""
        return self._redis_enabled

    async def get(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        if not self._redis_enabled:
            return None

        async with self.ensure_initialized():
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as e:
                self.log_error("get", e, key=key)
                return None

    async def set(self, key: str, value: Any, ttl_hours: int = None) -> bool:
        """Set cache data"""
        if not self._redis_enabled:
            return False

        async with self.ensure_initialized():
            try:
                settings = get_settings()
                ttl_hours = ttl_hours or getattr(settings, "CACHE_TTL_HOURS", 24)
                ttl = timedelta(hours=ttl_hours)

                serialized_value = json.dumps(value, ensure_ascii=False)
                self.redis_client.setex(key, ttl, serialized_value)
                return True
            except Exception as e:
                self.log_error("set", e, key=key)
                return False

    async def delete(self, key: str) -> bool:
        """Delete cache data"""
        if not self._redis_enabled:
            return False

        async with self.ensure_initialized():
            try:
                result = self.redis_client.delete(key)
                return result > 0
            except Exception as e:
                self.log_error("delete", e, key=key)
                return False

    async def clear_pattern(self, pattern: str) -> int:
        """Delete cache by pattern"""
        if not self._redis_enabled:
            return 0

        async with self.ensure_initialized():
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            except Exception as e:
                self.log_error("clear_pattern", e, pattern=pattern)
                return 0

    async def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self._redis_enabled:
            return {"enabled": False}

        async with self.ensure_initialized():
            try:
                info = self.redis_client.info()
                enhanced_stats = {
                    "enabled": True,
                    "used_memory": info.get("used_memory_human", "Unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "cache_stats": self.cache_stats.copy(),
                    "cache_config": self.cache_config.copy(),
                }

                # Add hit rate calculation
                total_ops = self.cache_stats["hits"] + self.cache_stats["misses"]
                if total_ops > 0:
                    enhanced_stats["hit_rate"] = self.cache_stats["hits"] / total_ops
                else:
                    enhanced_stats["hit_rate"] = 0.0

                return enhanced_stats
            except Exception as e:
                self.log_error("get_stats", e)
                return {"enabled": True, "error": str(e)}

    def _generate_cache_key(self, result_type: str, image_hash: str, **kwargs) -> str:
        """Generate versioned cache key for processing results"""
        config = self.cache_config.get(result_type, {"prefix": "unknown"})
        prefix = config["prefix"]

        # Create parameter hash for unique identification
        param_str = json.dumps(kwargs, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]

        # Include version for cache invalidation
        version = "v1"

        return f"{prefix}:{version}:{image_hash}:{param_hash}"

    async def get_detection_result(
        self,
        image_hash: str,
        confidence_threshold: float = 0.5,
        include_faces: bool = True,
        include_labels: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get cached detection results with TTL management"""
        if not self._redis_enabled:
            return None

        try:
            # Initialize lock if not already done
            if self._lock is None:
                self._lock = asyncio.Lock()

            async with self._lock:
                self.cache_stats["total_operations"] += 1

            cache_key = self._generate_cache_key(
                "detection_results",
                image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels,
            )

            result = await self.get(cache_key)

            async with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    self.logger.debug(f"Cache hit for detection result: {cache_key}")
                else:
                    self.cache_stats["misses"] += 1
                    self.logger.debug(f"Cache miss for detection result: {cache_key}")

            return result

        except Exception as e:
            self.log_error("get_detection_result", e, image_hash=image_hash)
            return None

    async def set_detection_result(
        self,
        image_hash: str,
        result: Dict[str, Any],
        confidence_threshold: float = 0.5,
        include_faces: bool = True,
        include_labels: bool = True,
    ) -> bool:
        """Cache detection results with appropriate TTL"""
        if not self._redis_enabled:
            return False

        try:
            cache_key = self._generate_cache_key(
                "detection_results",
                image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels,
            )

            config = self.cache_config["detection_results"]
            success = await self.set(cache_key, result, config["ttl_hours"])

            if success:
                self.logger.debug(f"Cached detection result: {cache_key}")

            return success

        except Exception as e:
            self.log_error("set_detection_result", e, image_hash=image_hash)
            return False

    async def get_analysis_result(
        self, image_hash: str, analysis_type: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Generic method: get analysis result cache"""
        if not self._redis_enabled:
            return None

        try:
            # Initialize lock if not already done
            if self._lock is None:
                self._lock = asyncio.Lock()

            async with self._lock:
                self.cache_stats["total_operations"] += 1

            # Choose appropriate cache method based on analysis type
            if (
                analysis_type == "labels"
                or analysis_type == "objects"
                or analysis_type == "faces"
            ):
                result = await self.get_detection_result(
                    image_hash,
                    confidence_threshold=kwargs.get("confidence_threshold", 0.5),
                    include_faces=analysis_type == "faces"
                    or kwargs.get("include_faces", True),
                    include_labels=analysis_type == "labels"
                    or kwargs.get("include_labels", True),
                )
            else:
                # Generic cache lookup
                cache_key = self._generate_cache_key(
                    "detection_results",
                    image_hash,
                    analysis_type=analysis_type,
                    **kwargs,
                )
                result = await self.get(cache_key)

            async with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    self.logger.debug(f"Cache hit for analysis result: {analysis_type}")
                else:
                    self.cache_stats["misses"] += 1
                    self.logger.debug(
                        f"Cache miss for analysis result: {analysis_type}"
                    )

            return result

        except Exception as e:
            self.log_error(
                "get_analysis_result",
                e,
                image_hash=image_hash,
                analysis_type=analysis_type,
            )
            return None

    async def set_analysis_result(
        self, image_hash: str, analysis_type: str, result: Dict[str, Any], **kwargs
    ) -> bool:
        """Generic method: set analysis result cache"""
        if not self._redis_enabled:
            return False

        try:
            # Choose appropriate cache method based on analysis type
            if (
                analysis_type == "labels"
                or analysis_type == "objects"
                or analysis_type == "faces"
            ):
                success = await self.set_detection_result(
                    image_hash,
                    result,
                    confidence_threshold=kwargs.get("confidence_threshold", 0.5),
                    include_faces=analysis_type == "faces"
                    or kwargs.get("include_faces", True),
                    include_labels=analysis_type == "labels"
                    or kwargs.get("include_labels", True),
                )
            else:
                # Generic cache storage
                cache_key = self._generate_cache_key(
                    "detection_results",
                    image_hash,
                    analysis_type=analysis_type,
                    **kwargs,
                )
                config = self.cache_config.get("detection_results", {"ttl_hours": 24})
                success = await self.set(cache_key, result, config["ttl_hours"])

            if success:
                self.logger.debug(f"Cached analysis result: {analysis_type}")

            return success

        except Exception as e:
            self.log_error(
                "set_analysis_result",
                e,
                image_hash=image_hash,
                analysis_type=analysis_type,
            )
            return False

    async def invalidate_cache_version(
        self, result_type: str, version: str = "v1"
    ) -> int:
        """Invalidate all cached results of a specific type and version"""
        if not self._redis_enabled:
            return 0

        try:
            config = self.cache_config.get(result_type, {"prefix": "unknown"})
            prefix = config["prefix"]
            pattern = f"{prefix}:{version}:*"

            deleted_count = await self.clear_pattern(pattern)
            self.log_operation(
                "invalidate_cache_version",
                result_type=result_type,
                version=version,
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            self.log_error(
                "invalidate_cache_version", e, result_type=result_type, version=version
            )
            return 0
