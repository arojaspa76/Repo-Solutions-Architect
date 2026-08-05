"""
Cache Manager con Redis + fallback memoria — Sesión 7
"""

import hashlib
import time
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", default_ttl: int = 300):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._redis = None
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self.backend = "none"
        self._hits = 0
        self._misses = 0

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True,
                socket_connect_timeout=2,
            )
            await self._redis.ping()
            self.backend = "redis"
            logger.info(f"✅ Cache Redis: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️  Redis no disponible ({e}) — usando memoria")
            self._redis = None
            self.backend = "memory"

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()

    def _make_key(self, prompt: str, model: str) -> str:
        content = f"{model}::{prompt}".encode("utf-8")
        return f"llm::{hashlib.sha256(content).hexdigest()[:16]}"

    async def get(self, key: str) -> Optional[str]:
        try:
            if self._redis:
                value = await self._redis.get(key)
                if value:
                    self._hits += 1
                    return value
                self._misses += 1
                return None
            else:
                if key in self._memory_cache:
                    value, expires = self._memory_cache[key]
                    if time.time() < expires:
                        self._hits += 1
                        return value
                    del self._memory_cache[key]
                self._misses += 1
                return None
        except Exception:
            self._misses += 1
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        ttl = ttl or self.default_ttl
        try:
            if self._redis:
                await self._redis.setex(key, ttl, value)
            else:
                self._memory_cache[key] = (value, time.time() + ttl)
            return True
        except Exception:
            return False

    async def flush(self) -> bool:
        try:
            if self._redis:
                await self._redis.flushdb()
            else:
                self._memory_cache.clear()
            self._hits = self._misses = 0
            return True
        except Exception:
            return False

    async def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = round(self._hits / total, 3) if total > 0 else 0.0
        stats = {
            "backend": self.backend,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "hit_rate_percent": f"{hit_rate * 100:.1f}%",
        }
        if self.backend == "memory":
            stats["memory_entries"] = len(self._memory_cache)
        return stats
