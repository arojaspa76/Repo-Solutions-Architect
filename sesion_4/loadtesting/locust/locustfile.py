"""
Locust — Pruebas de Carga en Python
=====================================
Alternativa a k6 para estudiantes más cómodos con Python.

Locust permite definir el comportamiento de usuarios virtuales
con código Python normal — más flexible que DSLs de otras tools.

Instalación:
    pip install locust

Uso básico (modo headless):
    locust -f loadtesting/locust/locustfile.py \
        --headless -u 50 -r 5 -t 5m \
        --host http://localhost:8000

Uso con UI web (abrir http://localhost:8089):
    locust -f loadtesting/locust/locustfile.py \
        --host http://localhost:8000

Exportar resultados:
    locust -f locustfile.py --headless -u 50 -r 5 -t 5m \
        --host http://localhost:8000 \
        --csv=results/locust-report
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner


# ── Datos de prueba ───────────────────────────────────────────────────────────
CHAT_MESSAGES = [
    "¿Qué es el autoescalado en Kubernetes?",
    "Explica serverless en 3 oraciones.",
    "¿Qué es el patrón circuit breaker?",
    "¿Cuándo usar HPA vs KEDA?",
    "Define alta disponibilidad para LLMs.",
]

TEXTS_TO_SUMMARIZE = [
    """Kubernetes es una plataforma de orquestación de contenedores open source
    que automatiza el despliegue, escalado y gestión de aplicaciones contenerizadas.
    Fue diseñado por Google basándose en su sistema interno Borg y donado a la CNCF.""",

    """El autoescalado horizontal (HPA) en Kubernetes ajusta automáticamente el número
    de réplicas de un Deployment basándose en métricas como CPU, memoria o métricas
    personalizadas. El HPA consulta el Metrics Server cada 15 segundos y calcula
    el número deseado de réplicas.""",
]


# ── Usuario LLM — comportamiento realista ─────────────────────────────────────
class LLMGatewayUser(HttpUser):
    """
    Simula un usuario de la API LLM Gateway.

    wait_time: tiempo de espera entre requests (entre 1 y 5 segundos)
    Simula comportamiento humano real — no todos piden al mismo tiempo.
    """
    wait_time = between(1, 5)  # Espera entre 1-5 segundos entre requests

    def on_start(self):
        """
        Ejecutado al inicio de cada usuario virtual.
        Verificar que el servicio está disponible.
        """
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") in ("healthy", "degraded"):
                    resp.success()
                else:
                    resp.failure(f"Health status: {data.get('status')}")
            else:
                resp.failure(f"Health check falló: {resp.status_code}")

    @task(4)  # Peso 4: 40% de las requests son health checks
    def health_check(self):
        """Health check — verifica disponibilidad del servicio."""
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(4)  # Peso 4: 40% son chats
    def chat_with_llm(self):
        """Chat con el LLM — con cache habilitado."""
        message = random.choice(CHAT_MESSAGES)

        with self.client.post(
            "/chat",
            json={
                "message": message,
                "model": "llama3.2:3b",
                "use_cache": True,
            },
            name="/chat",
            timeout=60,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("message"):
                        resp.success()
                        # Registrar si fue cache hit
                        if data.get("cached"):
                            self.environment.events.request.fire(
                                request_type="CACHE",
                                name="hit",
                                response_time=resp.elapsed.total_seconds() * 1000,
                                response_length=0,
                            )
                    else:
                        resp.failure("Respuesta vacía del LLM")
                except Exception as e:
                    resp.failure(f"Error parseando JSON: {e}")
            elif resp.status_code == 503:
                # Circuit breaker abierto — esperado bajo estrés
                resp.success()
            else:
                resp.failure(f"Status inesperado: {resp.status_code}")

    @task(2)  # Peso 2: 20% son summarize
    def summarize_text(self):
        """Resumir texto — ejercicio serverless-like."""
        text = random.choice(TEXTS_TO_SUMMARIZE)

        with self.client.post(
            "/summarize",
            json={
                "text": text,
                "language": "es",
                "max_length": 80,
            },
            name="/summarize",
            timeout=60,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("summary"):
                        resp.success()
                    else:
                        resp.failure("Resumen vacío")
                except Exception as e:
                    resp.failure(f"Error: {e}")
            elif resp.status_code in (503, 429):
                resp.success()  # Circuit breaker / rate limit — comportamiento esperado
            else:
                resp.failure(f"Status: {resp.status_code}")


# ── Escenario de estrés con picos ─────────────────────────────────────────────
class SpikeUser(HttpUser):
    """
    Usuario de spike test — requests muy rápidas para simular picos.
    Usar solo en tests de estrés.
    """
    wait_time = between(0.1, 0.5)  # Muy poco tiempo de espera

    @task
    def rapid_health(self):
        self.client.get("/health", name="/health-spike")


# ── Eventos de Locust ─────────────────────────────────────────────────────────
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "=" * 50)
    print("🚀 Iniciando prueba de carga Locust")
    print(f"   Host: {environment.host}")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    total = stats.total

    print("\n" + "=" * 50)
    print("📊 LOCUST — RESUMEN FINAL")
    print("=" * 50)
    print(f"Total requests:    {total.num_requests}")
    print(f"Total failures:    {total.num_failures}")
    print(f"Error rate:        {total.fail_ratio * 100:.2f}%")
    print(f"RPS (avg):         {total.current_rps:.1f}")
    print(f"P95 latencia:      {total.get_response_time_percentile(0.95):.0f}ms")
    print(f"P99 latencia:      {total.get_response_time_percentile(0.99):.0f}ms")
    print("=" * 50 + "\n")
