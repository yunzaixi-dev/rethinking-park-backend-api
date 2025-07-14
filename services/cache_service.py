import json
import aioredis
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

from config import settings

class CacheService:
    """Redis缓存服务，用于缓存图像分析结果"""
    
    def __init__(self):
        self.redis = None
        self.cache_enabled = getattr(settings, 'REDIS_ENABLED', True)
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
        self.default_ttl = getattr(settings, 'CACHE_TTL_HOURS', 24) * 3600  # 默认24小时
        
    async def initialize(self):
        """初始化Redis连接"""
        if not self.cache_enabled:
            print("⚠️ 缓存服务已禁用")
            return
            
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await self.redis.ping()
            print("✅ Redis缓存服务初始化成功")
        except Exception as e:
            print(f"⚠️ Redis连接失败，缓存功能将禁用: {e}")
            self.cache_enabled = False
            self.redis = None
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
    
    def _make_cache_key(self, image_hash: str, analysis_type: str) -> str:
        """生成缓存键"""
        return f"analysis:{image_hash}:{analysis_type}"
    
    async def get_analysis_result(self, image_hash: str, analysis_type: str) -> Optional[Dict[Any, Any]]:
        """获取缓存的分析结果"""
        if not self.cache_enabled or not self.redis:
            return None
            
        try:
            cache_key = self._make_cache_key(image_hash, analysis_type)
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                result = json.loads(cached_data)
                print(f"✅ 从缓存获取分析结果: {image_hash[:8]}...{analysis_type}")
                return result
                
        except Exception as e:
            print(f"❌ 获取缓存失败: {e}")
            
        return None
    
    async def set_analysis_result(self, image_hash: str, analysis_type: str, result: Dict[Any, Any], ttl: Optional[int] = None) -> bool:
        """缓存分析结果"""
        if not self.cache_enabled or not self.redis:
            return False
            
        try:
            cache_key = self._make_cache_key(image_hash, analysis_type)
            cache_data = {
                "result": result,
                "cached_at": datetime.now().isoformat(),
                "analysis_type": analysis_type,
                "image_hash": image_hash
            }
            
            cache_ttl = ttl or self.default_ttl
            await self.redis.setex(
                cache_key,
                cache_ttl,
                json.dumps(cache_data, ensure_ascii=False)
            )
            
            print(f"✅ 缓存分析结果: {image_hash[:8]}...{analysis_type} (TTL: {cache_ttl}s)")
            return True
            
        except Exception as e:
            print(f"❌ 设置缓存失败: {e}")
            return False
    
    async def delete_analysis_result(self, image_hash: str, analysis_type: str = None) -> bool:
        """删除缓存的分析结果"""
        if not self.cache_enabled or not self.redis:
            return False
            
        try:
            if analysis_type:
                # 删除特定类型的分析结果
                cache_key = self._make_cache_key(image_hash, analysis_type)
                await self.redis.delete(cache_key)
            else:
                # 删除该图像所有类型的分析结果
                pattern = f"analysis:{image_hash}:*"
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
            
            print(f"✅ 删除缓存: {image_hash[:8]}...")
            return True
            
        except Exception as e:
            print(f"❌ 删除缓存失败: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.cache_enabled or not self.redis:
            return {"enabled": False, "message": "缓存未启用"}
            
        try:
            info = await self.redis.info()
            keys_count = await self.redis.dbsize()
            
            return {
                "enabled": True,
                "connected": True,
                "total_keys": keys_count,
                "memory_usage": info.get("used_memory_human", "未知"),
                "uptime": info.get("uptime_in_seconds", 0),
                "redis_version": info.get("redis_version", "未知")
            }
        except Exception as e:
            return {"enabled": True, "connected": False, "error": str(e)}

# 创建全局实例
cache_service = CacheService() 