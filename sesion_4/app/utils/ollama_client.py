"""
Ollama Client — Sesión 4
========================
Cliente async para el servidor Ollama local.
Incluye circuit breaker para alta disponibilidad.

Circuit Breaker Pattern:
  CLOSED  → Todo normal, requests pasan al LLM
  OPEN    → LLM falló N veces, requests fallan rápido (fail-fast)
  HALF-OPEN → Prueba si LLM se recuperó
"""

import asyncio
import logging
import time
from typing import AsyncIterator, Optional
import httpx

logger = logging.getLogger(__name__)

# ── Circuit Breaker simple ────────────────────────────────────────────────────
class CircuitBreaker:
    """
    Implementación simple del patrón Circuit Breaker.

    Previene cascadas de fallos cuando el LLM no responde:
    En vez de esperar 30s de timeout N veces, después de 5 fallos
    el circuito "abre" y falla inmediatamente durante 60 segundos.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = "CLOSED"    # CLOSED | OPEN | HALF_OPEN
        self._last_failure_time = 0.0

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_open(self) -> bool:
        if self._state == "OPEN":
            # Verificar si es hora de intentar recovery
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = "HALF_OPEN"
                logger.info("🔄 Circuit Breaker: OPEN → HALF_OPEN (probando recovery)")
                return False
            return True
        return False

    def record_success(self):
        if self._state == "HALF_OPEN":
            self._state = "CLOSED"
            self._failures = 0
            logger.info("✅ Circuit Breaker: HALF_OPEN → CLOSED (LLM recuperado)")
        elif self._state == "CLOSED":
            self._failures = max(0, self._failures - 1)

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            if self._state != "OPEN":
                self._state = "OPEN"
                logger.error(
                    f"🔴 Circuit Breaker ABIERTO: {self._failures} fallos consecutivos. "
                    f"Esperando {self.recovery_timeout}s antes de reintentar."
                )


# ── Cliente Ollama ────────────────────────────────────────────────────────────
class OllamaClient:
    """
    Cliente async para Ollama con circuit breaker integrado.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )

    async def health_check(self) -> bool:
        """Verificar si Ollama está corriendo."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        """Listar modelos descargados en Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception as e:
            logger.error(f"Error listando modelos: {e}")
            return []

    async def chat(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Chat con el LLM local via Ollama.

        Incluye:
        - Circuit breaker (falla rápido si Ollama no responde)
        - Reintentos automáticos (hasta 3 intentos con backoff)
        - Timeout configurable

        Args:
            prompt: Mensaje del usuario
            model: Modelo Ollama (llama3.2:3b, mistral:7b, etc.)
            system_prompt: Instrucción de sistema opcional
            temperature: Creatividad (0.0=determinista, 1.0=creativo)

        Returns:
            Texto de respuesta del LLM
        """
        # ── Circuit Breaker check ─────────────────────────────────────────────
        if self.circuit_breaker.is_open:
            raise RuntimeError(
                f"Circuit Breaker ABIERTO — Ollama no disponible. "
                f"Estado: {self.circuit_breaker.state}"
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        # ── Reintentos con backoff exponencial ────────────────────────────────
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["message"]["content"]
                    self.circuit_breaker.record_success()
                    return text

            except httpx.TimeoutException:
                self.circuit_breaker.record_failure()
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"⏱ Timeout (intento {attempt+1}/{max_retries}), reintentando en {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise RuntimeError(f"Ollama timeout después de {max_retries} intentos")

            except httpx.HTTPStatusError as e:
                self.circuit_breaker.record_failure()
                raise RuntimeError(f"Ollama HTTP error {e.response.status_code}: {e.response.text}")

            except Exception as e:
                self.circuit_breaker.record_failure()
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"⚠️  Error (intento {attempt+1}/{max_retries}): {e}, reintentando en {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise

    async def stream_chat(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Chat con streaming — retorna tokens a medida que se generan.
        Ideal para UIs que muestran la respuesta progresivamente.
        """
        if self.circuit_breaker.is_open:
            raise RuntimeError("Circuit Breaker ABIERTO")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        import json
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if content := chunk.get("message", {}).get("content", ""):
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Generar embedding vectorial del texto."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": model, "input": text},
                )
                resp.raise_for_status()
                return resp.json()["embeddings"][0]
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
