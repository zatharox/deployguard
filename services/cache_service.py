"""
Redis cache service for performance optimization
"""
import json
from typing import Optional, Any
import redis.asyncio as redis
import structlog
from config import get_settings

logger = structlog.get_logger()


class CacheService:
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = bool(self.settings.redis_url)
    
    async def connect(self):
        """Connect to Redis"""
        if not self.enabled:
            logger.warning("redis_not_configured_cache_disabled")
            return
        
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            self.enabled = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return json.loads(value)
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL (default 1 hour)"""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            serialized = json.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            logger.debug("cache_set", key=key, ttl=ttl)
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            await self.redis_client.delete(key)
            logger.debug("cache_deleted", key=key)
        except Exception as e:
            logger.error("cache_delete_failed", key=key, error=str(e))
    
    async def invalidate_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info("cache_pattern_invalidated", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.error("cache_invalidate_failed", pattern=pattern, error=str(e))
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("redis_disconnected")


# Global cache instance
cache_service = CacheService()
