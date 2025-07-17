import json
import redis
import logging
import hashlib
import time
from typing import Any, Optional, Dict, List, Tuple
from datetime import timedelta, datetime
from collections import OrderedDict
import threading

from config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Enhanced Redis caching service for image processing results"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self._lock = threading.Lock()
        
        # Cache configuration for different result types
        self.cache_config = {
            "detection_results": {"ttl_hours": 24, "prefix": "detect"},
            "segmentation_masks": {"ttl_hours": 168, "prefix": "segment"},  # 7 days
            "extraction_results": {"ttl_hours": 720, "prefix": "extract"},  # 30 days
            "batch_processing": {"ttl_hours": 1, "prefix": "batch"},
            "natural_elements": {"ttl_hours": 48, "prefix": "nature"},
            "face_detection": {"ttl_hours": 24, "prefix": "faces"},
            "annotations": {"ttl_hours": 72, "prefix": "annotate"}  # 3 days
        }
        
        # LRU cache statistics
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_operations": 0
        }
        
        if settings.REDIS_ENABLED:
            try:
                # 解析Redis URL
                redis_url = settings.REDIS_URL
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                
                # 测试连接
                self.redis_client.ping()
                self.enabled = True
                logger.info("Enhanced Redis caching service initialized successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e}")
                self.enabled = False
        else:
            logger.info("Redis caching functionality disabled")
    
    def is_enabled(self) -> bool:
        """检查缓存服务是否可用"""
        return self.enabled
    
    async def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.enabled:
            return None
            
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"缓存读取失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_hours: int = None) -> bool:
        """设置缓存数据"""
        if not self.enabled:
            return False
            
        try:
            ttl_hours = ttl_hours or settings.CACHE_TTL_HOURS
            ttl = timedelta(hours=ttl_hours)
            
            serialized_value = json.dumps(value, ensure_ascii=False)
            self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"缓存写入失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存数据"""
        if not self.enabled:
            return False
            
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """根据模式删除缓存"""
        if not self.enabled:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"缓存模式删除失败: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.enabled:
            return {"enabled": False}
            
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
                "cache_config": self.cache_config.copy()
            }
            
            # Add hit rate calculation
            total_ops = self.cache_stats["hits"] + self.cache_stats["misses"]
            if total_ops > 0:
                enhanced_stats["hit_rate"] = self.cache_stats["hits"] / total_ops
            else:
                enhanced_stats["hit_rate"] = 0.0
                
            return enhanced_stats
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"enabled": True, "error": str(e)}
    
    # Enhanced caching methods for image processing results
    
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
        include_labels: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get cached detection results with TTL management"""
        if not self.enabled:
            return None
            
        try:
            with self._lock:
                self.cache_stats["total_operations"] += 1
            
            cache_key = self._generate_cache_key(
                "detection_results", 
                image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels
            )
            
            result = await self.get(cache_key)
            
            with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    logger.debug(f"Cache hit for detection result: {cache_key}")
                else:
                    self.cache_stats["misses"] += 1
                    logger.debug(f"Cache miss for detection result: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get detection result from cache: {e}")
            return None
    
    async def set_detection_result(
        self, 
        image_hash: str, 
        result: Dict[str, Any],
        confidence_threshold: float = 0.5,
        include_faces: bool = True,
        include_labels: bool = True
    ) -> bool:
        """Cache detection results with appropriate TTL"""
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(
                "detection_results", 
                image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_faces,
                include_labels=include_labels
            )
            
            config = self.cache_config["detection_results"]
            success = await self.set(cache_key, result, config["ttl_hours"])
            
            if success:
                logger.debug(f"Cached detection result: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache detection result: {e}")
            return False
    
    async def get_segmentation_mask(
        self, 
        image_hash: str, 
        object_id: str,
        algorithm: str = "basic"
    ) -> Optional[Dict[str, Any]]:
        """Get cached segmentation mask with extended TTL"""
        if not self.enabled:
            return None
            
        try:
            with self._lock:
                self.cache_stats["total_operations"] += 1
            
            cache_key = self._generate_cache_key(
                "segmentation_masks", 
                image_hash,
                object_id=object_id,
                algorithm=algorithm
            )
            
            result = await self.get(cache_key)
            
            with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    logger.debug(f"Cache hit for segmentation mask: {cache_key}")
                else:
                    self.cache_stats["misses"] += 1
                    logger.debug(f"Cache miss for segmentation mask: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get segmentation mask from cache: {e}")
            return None
    
    async def set_segmentation_mask(
        self, 
        image_hash: str, 
        object_id: str,
        mask_data: Dict[str, Any],
        algorithm: str = "basic"
    ) -> bool:
        """Cache segmentation mask with extended TTL (7 days)"""
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(
                "segmentation_masks", 
                image_hash,
                object_id=object_id,
                algorithm=algorithm
            )
            
            config = self.cache_config["segmentation_masks"]
            success = await self.set(cache_key, mask_data, config["ttl_hours"])
            
            if success:
                logger.debug(f"Cached segmentation mask: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache segmentation mask: {e}")
            return False
    
    async def get_extraction_result(
        self, 
        image_hash: str, 
        object_id: str,
        extraction_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached extraction result with long TTL (30 days)"""
        if not self.enabled:
            return None
            
        try:
            with self._lock:
                self.cache_stats["total_operations"] += 1
            
            cache_key = self._generate_cache_key(
                "extraction_results", 
                image_hash,
                object_id=object_id,
                **extraction_params
            )
            
            result = await self.get(cache_key)
            
            with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    logger.debug(f"Cache hit for extraction result: {cache_key}")
                else:
                    self.cache_stats["misses"] += 1
                    logger.debug(f"Cache miss for extraction result: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get extraction result from cache: {e}")
            return None
    
    async def set_extraction_result(
        self, 
        image_hash: str, 
        object_id: str,
        result: Dict[str, Any],
        extraction_params: Dict[str, Any]
    ) -> bool:
        """Cache extraction result with long TTL (30 days)"""
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(
                "extraction_results", 
                image_hash,
                object_id=object_id,
                **extraction_params
            )
            
            config = self.cache_config["extraction_results"]
            success = await self.set(cache_key, result, config["ttl_hours"])
            
            if success:
                logger.debug(f"Cached extraction result: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache extraction result: {e}")
            return False
    
    async def get_natural_elements_result(
        self, 
        image_hash: str,
        analysis_depth: str = "comprehensive"
    ) -> Optional[Dict[str, Any]]:
        """Get cached natural elements analysis result"""
        if not self.enabled:
            return None
            
        try:
            with self._lock:
                self.cache_stats["total_operations"] += 1
            
            cache_key = self._generate_cache_key(
                "natural_elements", 
                image_hash,
                analysis_depth=analysis_depth
            )
            
            result = await self.get(cache_key)
            
            with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    logger.debug(f"Cache hit for natural elements result: {cache_key}")
                else:
                    self.cache_stats["misses"] += 1
                    logger.debug(f"Cache miss for natural elements result: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get natural elements result from cache: {e}")
            return None
    
    async def set_natural_elements_result(
        self, 
        image_hash: str, 
        result: Dict[str, Any],
        analysis_depth: str = "comprehensive"
    ) -> bool:
        """Cache natural elements analysis result"""
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key(
                "natural_elements", 
                image_hash,
                analysis_depth=analysis_depth
            )
            
            config = self.cache_config["natural_elements"]
            success = await self.set(cache_key, result, config["ttl_hours"])
            
            if success:
                logger.debug(f"Cached natural elements result: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache natural elements result: {e}")
            return False
    
    async def get_batch_processing_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get cached batch processing status with short TTL"""
        if not self.enabled:
            return None
            
        try:
            cache_key = self._generate_cache_key("batch_processing", batch_id)
            result = await self.get(cache_key)
            
            with self._lock:
                self.cache_stats["total_operations"] += 1
                if result:
                    self.cache_stats["hits"] += 1
                else:
                    self.cache_stats["misses"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get batch processing status from cache: {e}")
            return None
    
    async def set_batch_processing_status(
        self, 
        batch_id: str, 
        status: Dict[str, Any]
    ) -> bool:
        """Cache batch processing status with short TTL (1 hour)"""
        if not self.enabled:
            return False
            
        try:
            cache_key = self._generate_cache_key("batch_processing", batch_id)
            config = self.cache_config["batch_processing"]
            
            return await self.set(cache_key, status, config["ttl_hours"])
            
        except Exception as e:
            logger.error(f"Failed to cache batch processing status: {e}")
            return False
    
    # Version management for cached processing results
    
    async def invalidate_cache_version(self, result_type: str, version: str = "v1") -> int:
        """Invalidate all cached results of a specific type and version"""
        if not self.enabled:
            return 0
            
        try:
            config = self.cache_config.get(result_type, {"prefix": "unknown"})
            prefix = config["prefix"]
            pattern = f"{prefix}:{version}:*"
            
            deleted_count = await self.clear_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries for {result_type} version {version}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache version: {e}")
            return 0
    
    async def get_cache_version_info(self, result_type: str) -> Dict[str, Any]:
        """Get information about cached versions for a result type"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            config = self.cache_config.get(result_type, {"prefix": "unknown"})
            prefix = config["prefix"]
            pattern = f"{prefix}:*"
            
            keys = self.redis_client.keys(pattern)
            version_counts = {}
            
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 2:
                    version = parts[1]
                    version_counts[version] = version_counts.get(version, 0) + 1
            
            return {
                "enabled": True,
                "result_type": result_type,
                "total_keys": len(keys),
                "version_counts": version_counts,
                "ttl_hours": config.get("ttl_hours", 24)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache version info: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def set_cache_with_version_management(
        self, 
        result_type: str,
        image_hash: str,
        result: Dict[str, Any],
        version: str = "v1",
        **kwargs
    ) -> bool:
        """Set cache with explicit version management"""
        if not self.enabled:
            return False
            
        try:
            # Generate cache key with specific version
            config = self.cache_config.get(result_type, {"prefix": "unknown"})
            prefix = config["prefix"]
            
            param_str = json.dumps(kwargs, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            
            cache_key = f"{prefix}:{version}:{image_hash}:{param_hash}"
            
            # Add version metadata to result
            versioned_result = {
                **result,
                "_cache_metadata": {
                    "version": version,
                    "cached_at": datetime.now().isoformat(),
                    "result_type": result_type,
                    "ttl_hours": config.get("ttl_hours", 24)
                }
            }
            
            success = await self.set(cache_key, versioned_result, config.get("ttl_hours", 24))
            
            if success:
                logger.debug(f"Cached {result_type} with version {version}: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache with version management: {e}")
            return False
    
    # LRU Cache Eviction Policies and Optimization
    
    async def implement_lru_eviction(self, max_memory_mb: int = 100) -> Dict[str, Any]:
        """Implement LRU cache eviction when memory usage is high"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            # Get current memory usage
            info = self.redis_client.info()
            used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
            
            eviction_stats = {
                "memory_before_mb": used_memory_mb,
                "max_memory_mb": max_memory_mb,
                "evicted_keys": 0,
                "eviction_needed": used_memory_mb > max_memory_mb
            }
            
            if used_memory_mb > max_memory_mb:
                # Get all cache keys with their last access time
                cache_keys_with_access = []
                
                for result_type, config in self.cache_config.items():
                    prefix = config["prefix"]
                    pattern = f"{prefix}:*"
                    keys = self.redis_client.keys(pattern)
                    
                    for key in keys:
                        try:
                            # Get TTL to estimate priority (lower TTL = accessed more recently)
                            ttl = self.redis_client.ttl(key)
                            if ttl > 0:
                                # Calculate priority score (higher = more likely to evict)
                                priority_score = self._calculate_eviction_priority(key, ttl, result_type)
                                cache_keys_with_access.append((key, priority_score, ttl))
                        except Exception:
                            continue
                
                # Sort by priority (highest priority = first to evict)
                cache_keys_with_access.sort(key=lambda x: x[1], reverse=True)
                
                # Evict keys until memory usage is acceptable
                target_memory_mb = max_memory_mb * 0.8  # Target 80% of max memory
                evicted_count = 0
                
                for key, priority, ttl in cache_keys_with_access:
                    if used_memory_mb <= target_memory_mb:
                        break
                        
                    try:
                        self.redis_client.delete(key)
                        evicted_count += 1
                        
                        # Update memory usage estimate
                        used_memory_mb *= 0.99  # Rough estimate of memory reduction
                        
                        with self._lock:
                            self.cache_stats["evictions"] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to evict cache key {key}: {e}")
                
                eviction_stats["evicted_keys"] = evicted_count
                eviction_stats["memory_after_mb"] = used_memory_mb
                
                logger.info(f"LRU eviction completed: evicted {evicted_count} keys, "
                           f"memory reduced from {eviction_stats['memory_before_mb']:.2f}MB "
                           f"to {used_memory_mb:.2f}MB")
            
            return eviction_stats
            
        except Exception as e:
            logger.error(f"LRU eviction failed: {e}")
            return {"enabled": True, "error": str(e)}
    
    def _calculate_eviction_priority(self, key: str, ttl: int, result_type: str) -> float:
        """Calculate eviction priority for a cache key (higher = more likely to evict)"""
        try:
            # Base priority on TTL (keys with more time left are lower priority)
            config = self.cache_config.get(result_type, {"ttl_hours": 24})
            max_ttl_seconds = config["ttl_hours"] * 3600
            
            # Normalize TTL to 0-1 range (1 = just cached, 0 = about to expire)
            ttl_ratio = ttl / max_ttl_seconds if max_ttl_seconds > 0 else 0
            
            # Priority factors
            ttl_priority = ttl_ratio  # Higher TTL = higher eviction priority
            
            # Result type priority (some types are more important to keep)
            type_priority_map = {
                "extraction_results": 0.2,  # Keep extraction results longer
                "segmentation_masks": 0.3,  # Keep segmentation masks longer
                "detection_results": 0.5,   # Medium priority
                "natural_elements": 0.6,    # Medium-high priority
                "batch_processing": 0.9,    # High eviction priority (short-lived)
                "annotations": 0.7          # Medium-high priority
            }
            
            type_priority = type_priority_map.get(result_type, 0.5)
            
            # Combine priorities (weighted average)
            final_priority = (ttl_priority * 0.6) + (type_priority * 0.4)
            
            return final_priority
            
        except Exception as e:
            logger.error(f"Failed to calculate eviction priority: {e}")
            return 0.5  # Default medium priority
    
    async def get_detailed_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics and monitoring data"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            # Get Redis info
            info = self.redis_client.info()
            
            # Get cache type statistics
            type_stats = {}
            total_keys = 0
            
            for result_type, config in self.cache_config.items():
                prefix = config["prefix"]
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                
                type_stats[result_type] = {
                    "key_count": len(keys),
                    "prefix": prefix,
                    "ttl_hours": config["ttl_hours"]
                }
                total_keys += len(keys)
            
            # Calculate cache efficiency metrics
            total_ops = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = self.cache_stats["hits"] / total_ops if total_ops > 0 else 0.0
            
            detailed_stats = {
                "enabled": True,
                "timestamp": datetime.now().isoformat(),
                
                # Redis server stats
                "redis_info": {
                    "used_memory": info.get("used_memory_human", "Unknown"),
                    "used_memory_bytes": info.get("used_memory", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                },
                
                # Application cache stats
                "application_stats": {
                    **self.cache_stats,
                    "hit_rate": hit_rate,
                    "total_keys": total_keys
                },
                
                # Per-type statistics
                "type_statistics": type_stats,
                
                # Performance metrics
                "performance_metrics": {
                    "average_operations_per_minute": self._calculate_ops_per_minute(),
                    "cache_efficiency_score": self._calculate_cache_efficiency_score(hit_rate, total_keys),
                    "memory_efficiency": self._calculate_memory_efficiency(info)
                }
            }
            
            return detailed_stats
            
        except Exception as e:
            logger.error(f"Failed to get detailed cache statistics: {e}")
            return {"enabled": True, "error": str(e)}
    
    def _calculate_ops_per_minute(self) -> float:
        """Calculate approximate operations per minute"""
        # This is a simplified calculation - in production you'd want to track this over time
        total_ops = self.cache_stats["total_operations"]
        # Assume service has been running for at least 1 minute
        return total_ops / max(1, 60)  # Simplified calculation
    
    def _calculate_cache_efficiency_score(self, hit_rate: float, total_keys: int) -> float:
        """Calculate overall cache efficiency score (0-100)"""
        # Combine hit rate and key utilization
        hit_rate_score = hit_rate * 70  # 70% weight for hit rate
        
        # Key utilization score (more keys = better utilization, up to a point)
        optimal_key_count = 1000  # Optimal number of cached keys
        key_utilization = min(1.0, total_keys / optimal_key_count)
        key_score = key_utilization * 30  # 30% weight for key utilization
        
        return hit_rate_score + key_score
    
    def _calculate_memory_efficiency(self, redis_info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate memory efficiency metrics"""
        used_memory = redis_info.get("used_memory", 0)
        
        return {
            "used_memory_mb": used_memory / (1024 * 1024),
            "memory_fragmentation_ratio": redis_info.get("mem_fragmentation_ratio", 1.0),
            "memory_efficiency_score": min(100.0, (1.0 / max(1.0, redis_info.get("mem_fragmentation_ratio", 1.0))) * 100)
        }
    
    async def get_analysis_result(
        self, 
        image_hash: str, 
        analysis_type: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """通用方法：获取分析结果缓存"""
        if not self.enabled:
            return None
            
        try:
            with self._lock:
                self.cache_stats["total_operations"] += 1
            
            # 根据分析类型选择合适的缓存方法
            if analysis_type == "labels" or analysis_type == "objects" or analysis_type == "faces":
                result = await self.get_detection_result(
                    image_hash,
                    confidence_threshold=kwargs.get("confidence_threshold", 0.5),
                    include_faces=analysis_type == "faces" or kwargs.get("include_faces", True),
                    include_labels=analysis_type == "labels" or kwargs.get("include_labels", True)
                )
            elif analysis_type == "natural_elements" or analysis_type in ["vegetation", "water", "sky", "terrain"]:
                result = await self.get_natural_elements_result(
                    image_hash,
                    analysis_depth=kwargs.get("analysis_depth", "comprehensive")
                )
            else:
                # 通用缓存查找
                cache_key = self._generate_cache_key(
                    "detection_results", 
                    image_hash,
                    analysis_type=analysis_type,
                    **kwargs
                )
                result = await self.get(cache_key)
            
            with self._lock:
                if result:
                    self.cache_stats["hits"] += 1
                    logger.debug(f"Cache hit for analysis result: {analysis_type}")
                else:
                    self.cache_stats["misses"] += 1
                    logger.debug(f"Cache miss for analysis result: {analysis_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get analysis result from cache: {e}")
            return None
    
    async def set_analysis_result(
        self, 
        image_hash: str, 
        analysis_type: str,
        result: Dict[str, Any],
        **kwargs
    ) -> bool:
        """通用方法：设置分析结果缓存"""
        if not self.enabled:
            return False
            
        try:
            # 根据分析类型选择合适的缓存方法
            if analysis_type == "labels" or analysis_type == "objects" or analysis_type == "faces":
                success = await self.set_detection_result(
                    image_hash,
                    result,
                    confidence_threshold=kwargs.get("confidence_threshold", 0.5),
                    include_faces=analysis_type == "faces" or kwargs.get("include_faces", True),
                    include_labels=analysis_type == "labels" or kwargs.get("include_labels", True)
                )
            elif analysis_type == "natural_elements" or analysis_type in ["vegetation", "water", "sky", "terrain"]:
                success = await self.set_natural_elements_result(
                    image_hash,
                    result,
                    analysis_depth=kwargs.get("analysis_depth", "comprehensive")
                )
            else:
                # 通用缓存存储
                cache_key = self._generate_cache_key(
                    "detection_results", 
                    image_hash,
                    analysis_type=analysis_type,
                    **kwargs
                )
                config = self.cache_config.get("detection_results", {"ttl_hours": 24})
                success = await self.set(cache_key, result, config["ttl_hours"])
            
            if success:
                logger.debug(f"Cached analysis result: {analysis_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache analysis result: {e}")
            return False

    async def warm_cache_for_common_operations(self, image_hashes: List[str]) -> Dict[str, Any]:
        """Implement cache warming for common operations"""
        if not self.enabled:
            return {"enabled": False}
            
        warming_stats = {
            "total_images": len(image_hashes),
            "warmed_operations": 0,
            "failed_operations": 0,
            "operations_attempted": []
        }
        
        try:
            # Common operation parameters for cache warming
            common_operations = [
                {
                    "operation": "detection_results",
                    "params": {"confidence_threshold": 0.5, "include_faces": True, "include_labels": True}
                },
                {
                    "operation": "natural_elements",
                    "params": {"analysis_depth": "basic"}
                }
            ]
            
            for image_hash in image_hashes:
                for operation in common_operations:
                    try:
                        # Check if already cached
                        cache_key = self._generate_cache_key(
                            operation["operation"], 
                            image_hash, 
                            **operation["params"]
                        )
                        
                        existing_result = await self.get(cache_key)
                        
                        if not existing_result:
                            # This would typically trigger the actual processing
                            # For now, we'll just log that warming is needed
                            logger.debug(f"Cache warming needed for {operation['operation']} on {image_hash}")
                            warming_stats["operations_attempted"].append({
                                "image_hash": image_hash,
                                "operation": operation["operation"],
                                "status": "warming_needed"
                            })
                        else:
                            warming_stats["warmed_operations"] += 1
                            warming_stats["operations_attempted"].append({
                                "image_hash": image_hash,
                                "operation": operation["operation"],
                                "status": "already_cached"
                            })
                            
                    except Exception as e:
                        logger.error(f"Cache warming failed for {image_hash} {operation['operation']}: {e}")
                        warming_stats["failed_operations"] += 1
                        warming_stats["operations_attempted"].append({
                            "image_hash": image_hash,
                            "operation": operation["operation"],
                            "status": "failed",
                            "error": str(e)
                        })
            
            logger.info(f"Cache warming completed: {warming_stats['warmed_operations']} operations warmed, "
                       f"{warming_stats['failed_operations']} failed")
            
            return warming_stats
            
        except Exception as e:
            logger.error(f"Cache warming process failed: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def cleanup_expired_cache_entries(self) -> Dict[str, Any]:
        """Clean up expired cache entries and optimize storage"""
        if not self.enabled:
            return {"enabled": False}
            
        cleanup_stats = {
            "expired_keys_removed": 0,
            "orphaned_keys_removed": 0,
            "total_keys_before": 0,
            "total_keys_after": 0,
            "memory_freed_mb": 0.0
        }
        
        try:
            # Get memory usage before cleanup
            info_before = self.redis_client.info()
            memory_before = info_before.get("used_memory", 0)
            
            # Get all cache keys
            all_keys = []
            for result_type, config in self.cache_config.items():
                prefix = config["prefix"]
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                all_keys.extend(keys)
            
            cleanup_stats["total_keys_before"] = len(all_keys)
            
            # Check each key for expiration or orphaned status
            expired_keys = []
            orphaned_keys = []
            
            for key in all_keys:
                try:
                    ttl = self.redis_client.ttl(key)
                    
                    if ttl == -2:  # Key doesn't exist (expired)
                        expired_keys.append(key)
                    elif ttl == -1:  # Key exists but has no expiration
                        # Check if it's an orphaned key (malformed or from old versions)
                        if not self._is_valid_cache_key(key):
                            orphaned_keys.append(key)
                            
                except Exception as e:
                    logger.error(f"Error checking key {key}: {e}")
                    orphaned_keys.append(key)
            
            # Remove expired keys
            if expired_keys:
                removed_expired = self.redis_client.delete(*expired_keys)
                cleanup_stats["expired_keys_removed"] = removed_expired
                with self._lock:
                    self.cache_stats["evictions"] += removed_expired
            
            # Remove orphaned keys
            if orphaned_keys:
                removed_orphaned = self.redis_client.delete(*orphaned_keys)
                cleanup_stats["orphaned_keys_removed"] = removed_orphaned
                with self._lock:
                    self.cache_stats["evictions"] += removed_orphaned
            
            # Get memory usage after cleanup
            info_after = self.redis_client.info()
            memory_after = info_after.get("used_memory", 0)
            cleanup_stats["memory_freed_mb"] = (memory_before - memory_after) / (1024 * 1024)
            
            # Count remaining keys
            remaining_keys = []
            for result_type, config in self.cache_config.items():
                prefix = config["prefix"]
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                remaining_keys.extend(keys)
            
            cleanup_stats["total_keys_after"] = len(remaining_keys)
            
            logger.info(f"Cache cleanup completed: removed {cleanup_stats['expired_keys_removed']} expired keys, "
                       f"{cleanup_stats['orphaned_keys_removed']} orphaned keys, "
                       f"freed {cleanup_stats['memory_freed_mb']:.2f}MB")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return {"enabled": True, "error": str(e)}
    
    def _is_valid_cache_key(self, key: str) -> bool:
        """Check if a cache key follows the expected format"""
        try:
            parts = key.split(":")
            
            # Expected format: prefix:version:image_hash:param_hash
            if len(parts) != 4:
                return False
            
            prefix, version, image_hash, param_hash = parts
            
            # Check if prefix is valid
            valid_prefixes = [config["prefix"] for config in self.cache_config.values()]
            if prefix not in valid_prefixes:
                return False
            
            # Check version format
            if not version.startswith("v"):
                return False
            
            # Check hash lengths (basic validation)
            if len(image_hash) < 8 or len(param_hash) != 8:
                return False
            
            return True
            
        except Exception:
            return False

# 创建全局缓存服务实例
cache_service = CacheService()
