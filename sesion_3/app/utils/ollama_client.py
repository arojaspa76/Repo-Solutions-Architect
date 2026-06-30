"""
============================================================
ollama_client.py — Cliente para Ollama (LLM local)
Sesión 3: Kubernetes, Docker y Contenedores para LLMs
============================================================

Ollama permite ejecutar LLMs de forma local sin necesidad
de API keys ni conexión a la nube. Perfecto para:
- Desarrollo y pruebas
- Ambientes sin acceso a internet
- Cero costo durante el aprendizaje

Instalación:
    # Linux/Mac
    curl -fsSL https://ollama.ai/install.sh | sh
    
    # Windows (descargar instalador)
    https://ollama.ai/download

Modelos recomendados para clase:
    ollama pull llama3.2:3b    # ~2GB — recomendado
    ollama pull mistral:7b     # ~4GB — mejor calidad
    ollama pull phi3:mini      # ~2GB — rápido

Referencia API: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import time
import logging
from typing import AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)

# URL base de Ollama (puede cambiarse con variable de entorno)
OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaClient:
    """
    Cliente asíncrono para la API de Ollama.
    
    Ollama expone una API REST local en el puerto 11434.
    Este cliente envuelve esa API para facilitar su uso desde FastAPI.
    
    Ejemplo de uso:
        client = OllamaClient()
        
        # Verificar conexión
        if await client.health_check():
            # Chat simple
            response = await client.chat("¿Qué es Docker?")
            print(response)
    """
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout: int = 120):
        self.base_url = base_url
        self.timeout = timeout
        # httpx es el cliente HTTP async recomendado para FastAPI
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
        )
    
    async def health_check(self) -> bool:
        """
        Verifica si Ollama está corriendo y accesible.
        
        Ollama expone GET / que retorna "Ollama is running" si está activo.
        
        Returns:
            True si Ollama responde, False si no está disponible
        """
        try:
            response = await self._client.get("/")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
        except Exception as e:
            logger.error(f"Error al verificar Ollama: {e}")
            return False
    
    async def list_models(self) -> list[dict]:
        """
        Lista todos los modelos descargados en Ollama.
        
        Equivalente a: ollama list
        
        Returns:
            Lista de dicts con info de cada modelo:
            [{"name": "llama3.2:3b", "size": 2.0, ...}]
        """
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Error listando modelos Ollama: {e}")
            return []
    
    async def chat(
        self,
        message: str,
        model: str = "llama3.2:3b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict:
        """
        Envía un mensaje al LLM y recibe la respuesta completa.
        
        Llama a POST /api/chat de Ollama con stream=False.
        Espera a que el modelo termine de generar antes de retornar.
        
        Args:
            message: El mensaje del usuario
            model: Nombre del modelo (ej: "llama3.2:3b")
            system_prompt: Instrucciones del sistema
            temperature: 0.0 a 2.0 (creatividad)
            max_tokens: Máximo de tokens a generar
            
        Returns:
            Dict con "response", "tokens_used", "latency_ms"
            
        Example:
            result = await client.chat(
                "¿Qué es Kubernetes?",
                model="llama3.2:3b",
                system_prompt="Responde en máximo 3 oraciones."
            )
            print(result["response"])
        """
        start_time = time.perf_counter()
        
        # Construir mensajes en formato OpenAI (compatible con Ollama)
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })
        
        messages.append({
            "role": "user",
            "content": message,
        })
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        try:
            logger.info(f"📤 Chat request → model={model}, tokens_max={max_tokens}")
            
            response = await self._client.post(
                "/api/chat",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extraer información de uso de tokens
            usage = data.get("usage", {})
            tokens_used = (
                usage.get("prompt_tokens", 0) + 
                usage.get("completion_tokens", 0)
            )
            
            logger.info(
                f"📥 Chat response ← model={model}, "
                f"tokens={tokens_used}, latency={latency_ms:.0f}ms"
            )
            
            return {
                "response": data["message"]["content"],
                "tokens_used": tokens_used or None,
                "latency_ms": latency_ms,
                "model": model,
                "provider": "ollama",
            }
            
        except httpx.ConnectError:
            raise ConnectionError(
                "No se puede conectar a Ollama. "
                "¿Está corriendo? Ejecuta: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Modelo '{model}' no encontrado. "
                    f"Descárgalo con: ollama pull {model}"
                )
            raise
    
    async def chat_stream(
        self,
        message: str,
        model: str = "llama3.2:3b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Chat con streaming de tokens.
        
        En lugar de esperar la respuesta completa, retorna los tokens
        a medida que el modelo los genera. Útil para interfaces de usuario
        reactivas (como ChatGPT).
        
        Args:
            message: El mensaje del usuario
            model: Nombre del modelo
            system_prompt: Instrucciones del sistema
            temperature: Creatividad
            
        Yields:
            Tokens de texto a medida que se generan
            
        Example:
            async for token in client.chat_stream("¿Qué es Docker?"):
                print(token, end="", flush=True)
        """
        import json
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        ) as client:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if content := chunk.get("message", {}).get("content"):
                                yield content
                        except json.JSONDecodeError:
                            continue
    
    async def generate_embedding(
        self,
        text: str,
        model: str = "llama3.2:3b",
    ) -> list[float]:
        """
        Genera un vector de embedding para el texto dado.
        
        Los embeddings son representaciones numéricas del significado
        semántico del texto. Se usan en:
        - Búsqueda semántica
        - RAG (Retrieval-Augmented Generation)
        - Clustering de documentos
        
        Args:
            text: Texto a vectorizar
            model: Modelo para generar el embedding
            
        Returns:
            Lista de floats (vector de alta dimensión)
        """
        try:
            response = await self._client.post(
                "/api/embeddings",
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
    
    async def pull_model(self, model: str) -> AsyncIterator[dict]:
        """
        Descarga un modelo de Ollama Hub.
        
        Equivalente a: ollama pull model_name
        
        Yields:
            Dicts con progreso de descarga:
            {"status": "pulling", "completed": 1234, "total": 5678}
        """
        import json
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(600),  # 10 minutos para descargas grandes
        ) as client:
            async with client.stream(
                "POST",
                "/api/pull",
                json={"name": model, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
    
    async def close(self):
        """Cerrar el cliente HTTP."""
        await self._client.aclose()
