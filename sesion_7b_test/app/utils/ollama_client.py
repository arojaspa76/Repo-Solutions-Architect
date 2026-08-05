"""
Ollama Client con Circuit Breaker — Sesión 7
"""

import asyncio
import logging
import time
from typing import AsyncIterator, Optional
import httpx

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit Breaker para el cliente Ollama."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = "CLOSED"
        self._last_failure_time = 0.0

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_open(self) -> bool:
        if self._state == "OPEN":
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = "HALF_OPEN"
                logger.info("🔄 Circuit Breaker: OPEN → HALF_OPEN")
                return False
            return True
        return False

    def record_success(self):
        if self._state == "HALF_OPEN":
            self._state = "CLOSED"
            self._failures = 0
            logger.info("✅ Circuit Breaker: CLOSED (recuperado)")

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "OPEN"
            logger.error(f"🔴 Circuit Breaker ABIERTO: {self._failures} fallos")


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0):
        self.base_url = base_url
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker()

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception:
            return []

    async def chat(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        if self.circuit_breaker.is_open:
            raise RuntimeError(f"Circuit Breaker {self.circuit_breaker.state}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False,
                            "options": {"temperature": temperature},
                        },
                    )
                    resp.raise_for_status()
                    self.circuit_breaker.record_success()
                    return resp.json()["message"]["content"]
            except Exception as e:
                self.circuit_breaker.record_failure()
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"Ollama error: {e}")

    async def stream_chat(
        self,
        prompt: str,
        model: str = "llama3.2:3b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        import json
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True,
                      "options": {"temperature": temperature}}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if content := chunk.get("message", {}).get("content", ""):
                                yield content
                        except json.JSONDecodeError:
                            continue
