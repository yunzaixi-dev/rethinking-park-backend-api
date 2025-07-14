import json
import redis
import logging
from typing import Any, Optional
from datetime import timedelta

from config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Redis缓存服务"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        
        if settings.REDIS_ENABLED:
            try:
                # 解析Redis URL
                redis_url = settings.REDIS_URL
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                
                # 测试连接
                self.redis_client.ping()
                self.enabled = True
                logger.info("Redis缓存服务初始化成功")
            except Exception as e:
                logger.warning(f"Redis连接失败，缓存功能将被禁用: {e}")
                self.enabled = False
        else:
            logger.info("Redis缓存功能已禁用")
    
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
            return {
                "enabled": True,
                "used_memory": info.get("used_memory_human", "Unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"enabled": True, "error": str(e)}

# 创建全局缓存服务实例
cache_service = CacheService()
