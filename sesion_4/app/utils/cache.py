"""
Cache Manager — Sesión 4
==============================
Implementa cache de dos niveles:
  1. Redis (distribuido, compartido entre pods)
  2. Dict en memoria (fallback si Redis no está disponible)

Por qué cachear respuestas de LLM:
  - Una llamada a GPT-4o puede tardar 3-15 segundos
  - Si 100 usuarios hacen la misma pregunta, sin cache = 100 llamadas = 100x costo
  - Con cache: 1 llamada real + 99 cache hits = 99% de ahorro en latencia y costo

Uso:
    cache = CacheManager()
    await cache.connect()

    # Guardar
    await cache.set("mi_key", "mi_valor", ttl=300)

    # Recuperar
    valor = await cache.get("mi_key")  # None si no existe o expiró
"""

import hashlib
import json
import time
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gestor de cache con soporte Redis y fallback en memoria.

    El cache usa como clave el hash SHA256 del prompt + modelo,
    garantizando que la misma pregunta al mismo modelo siempre
    retorna el mismo resultado cacheado.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0",
                 default_ttl: int = 300):
        self.redis_url = redis_url
        self.default_ttl = default_ttl  # segundos
        self._redis = None
        self._memory_cache: dict[str, tuple[Any, float]] = {}  # {key: (value, expires_at)}
        self.backend = "none"
        self._hits = 0
        self._misses = 0

    async def connect(self):
        """
        Intenta conectar a Redis.
        Si falla, usa cache en memoria (sin persistencia entre pods).
        """
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            # Test de conexión
            await self._redis.ping()
            self.backend = "redis"
            logger.info(f"✅ Cache Redis conectado: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️  Redis no disponible ({e}) — usando cache en memoria")
            self._redis = None
            self.backend = "memory"

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()

    def _make_key(self, prompt: str, model: str) -> str:
        """
        Genera una clave de cache determinista basada en prompt + modelo.

        SHA256 garantiza:
        - Claves de longitud fija (no importa el tamaño del prompt)
        - Sin colisiones en la práctica
        - El mismo prompt siempre genera la misma key
        """
        content = f"{model}::{prompt}".encode("utf-8")
        return f"llm::{hashlib.sha256(content).hexdigest()[:16]}"

    async def get(self, key: str) -> Optional[str]:
        """Recuperar valor del cache. Retorna None si no existe o expiró."""
        try:
            if self._redis:
                value = await self._redis.get(key)
                if value:
                    self._hits += 1
                    return value
                self._misses += 1
                return None
            else:
                # Cache en memoria
                if key in self._memory_cache:
                    value, expires_at = self._memory_cache[key]
                    if time.time() < expires_at:
                        self._hits += 1
                        return value
                    else:
                        del self._memory_cache[key]
                self._misses += 1
                return None
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            self._misses += 1
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Guardar valor en cache."""
        ttl = ttl or self.default_ttl
        try:
            if self._redis:
                await self._redis.setex(key, ttl, value)
            else:
                self._memory_cache[key] = (value, time.time() + ttl)
                # Limpiar entradas expiradas cada 100 writes
                if len(self._memory_cache) % 100 == 0:
                    self._cleanup_memory()
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def get_or_compute(
        self,
        prompt: str,
        model: str,
        compute_fn,
        ttl: Optional[int] = None
    ) -> tuple[str, bool]:
        """
        Patrón cache-aside:
        1. Buscar en cache
        2. Si no está, llamar compute_fn() (el LLM)
        3. Guardar resultado en cache
        4. Retornar (resultado, fue_cacheado)

        Ejemplo de uso:
            response, cached = await cache.get_or_compute(
                prompt="¿Qué es Kubernetes?",
                model="llama3.2:3b",
                compute_fn=lambda: ollama.chat(...)
            )
        """
        key = self._make_key(prompt, model)

        # 1. Buscar en cache
        cached_value = await self.get(key)
        if cached_value:
            logger.info(f"🎯 Cache HIT: {key[:12]}...")
            return cached_value, True

        # 2. Cache MISS → llamar al LLM
        logger.info(f"📡 Cache MISS: {key[:12]}... → llamando al LLM")
        result = await compute_fn()

        # 3. Guardar en cache
        await self.set(key, result, ttl)

        return result, False

    async def invalidate(self, key: str) -> bool:
        """Invalidar una entrada específica del cache."""
        try:
            if self._redis:
                await self._redis.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return False

    async def flush(self) -> bool:
        """Vaciar todo el cache (usar con cuidado en producción)."""
        try:
            if self._redis:
                await self._redis.flushdb()
            else:
                self._memory_cache.clear()
            self._hits = 0
            self._misses = 0
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

    async def stats(self) -> dict:
        """Estadísticas del cache para el endpoint /cache/stats"""
        total = self._hits + self._misses
        hit_rate = round(self._hits / total, 3) if total > 0 else 0.0

        stats = {
            "backend": self.backend,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "hit_rate_percent": f"{hit_rate * 100:.1f}%",
        }

        if self.backend == "redis" and self._redis:
            try:
                info = await self._redis.info("memory")
                stats["redis_memory_mb"] = round(
                    info.get("used_memory", 0) / 1024 / 1024, 2
                )
                stats["redis_keys"] = await self._redis.dbsize()
            except Exception:
                pass
        else:
            stats["memory_entries"] = len(self._memory_cache)

        return stats

    def _cleanup_memory(self):
        """Eliminar entradas expiradas del cache en memoria."""
        now = time.time()
        expired = [k for k, (_, exp) in self._memory_cache.items() if exp < now]
        for k in expired:
            del self._memory_cache[k]
        if expired:
            logger.debug(f"🧹 Cache: {len(expired)} entradas expiradas eliminadas")
