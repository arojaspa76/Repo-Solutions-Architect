"""
Locust — Pruebas de Carga del Agente LLM (Sesión 7)
======================================================
Alternativa a k6 en Python para probar el agente LLM.

Características especiales para agentes:
  - Tiempos de espera más largos (agente puede tardar 5-60s)
  - Verificación del formato de respuesta del agente
  - Tracking de herramientas usadas
  - Usuario de "spike" para simular picos

Instalación:
    pip install locust

Uso headless (sin UI):
    locust -f loadtesting/locust/locustfile.py \\
        --headless -u 20 -r 2 -t 10m \\
        --host http://localhost:8000 \\
        --csv=loadtesting/results/locust-agent

Uso con UI web (http://localhost:8089):
    locust -f loadtesting/locust/locustfile.py \\
        --host http://localhost:8000
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# ── Datos de prueba ───────────────────────────────────────────────────────────
AGENT_SIMPLE_QUERIES = [
    {"input": "¿Cuánto es 1234 * 5678?", "session_id": "locust-calc"},
    {"input": "¿Qué clima hay en Bogotá?", "session_id": "locust-weather"},
    {"input": "¿Qué es KEDA en Kubernetes?", "session_id": "locust-search"},
    {"input": "¿Cuánto es sqrt(144)?", "session_id": "locust-sqrt"},
    {"input": "¿Cómo está el clima en Medellín?", "session_id": "locust-weather2"},
]

AGENT_COMPLEX_QUERIES = [
    {
        "input": "¿Cuánto es 365 * 24 * 60 y qué clima hay en Lima?",
        "session_id": "locust-multi1",
    },
    {
        "input": "Calcula 1000 * 365 y busca información sobre autoescalado K8s.",
        "session_id": "locust-multi2",
    },
]

CHAT_QUERIES = [
    "Define alta disponibilidad en 2 oraciones.",
    "¿Qué es el patrón Circuit Breaker?",
    "Explica HPA vs KEDA en Kubernetes.",
    "¿Para qué sirve Ollama?",
]

# Estadísticas del agente
_agent_stats = {"total": 0, "success": 0, "errors": 0, "tool_calls": {}}


# ── Usuario principal ─────────────────────────────────────────────────────────
class LLMAgentUser(HttpUser):
    """
    Usuario que simula uso real del agente LLM.
    wait_time: entre 3 y 10 segundos (el agente tarda, los usuarios esperan)
    """
    wait_time = between(3, 10)

    def on_start(self):
        """Verificar que el servicio está disponible."""
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") in ("healthy", "degraded"):
                    resp.success()
                    # Verificar que el agente tiene herramientas
                    tools = data.get("components", {}).get("agent", {}).get("tools", [])
                    if not tools:
                        print("⚠️  Agente sin herramientas — verificar configuración")
                else:
                    resp.failure(f"Status inesperado: {data.get('status')}")
            else:
                resp.failure(f"Health check falló: {resp.status_code}")

    @task(3)
    def health_check(self):
        """Health check rápido."""
        with self.client.get("/health", name="/health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(4)
    def agent_simple(self):
        """Agente con una sola herramienta — más rápido."""
        query = random.choice(AGENT_SIMPLE_QUERIES)

        with self.client.post(
            "/agent/run",
            json={**query, "model": "llama3.2:3b"},
            name="/agent/run (simple)",
            timeout=90,
            catch_response=True,
        ) as resp:
            _agent_stats["total"] += 1

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("output") and len(data["output"]) > 5:
                        resp.success()
                        _agent_stats["success"] += 1

                        # Contabilizar herramientas usadas
                        for step in data.get("steps", []):
                            if step.get("action"):
                                tool = step["action"]
                                _agent_stats["tool_calls"][tool] = \
                                    _agent_stats["tool_calls"].get(tool, 0) + 1
                    else:
                        resp.failure("Output vacío del agente")
                        _agent_stats["errors"] += 1
                except Exception as e:
                    resp.failure(f"Error parseando: {e}")
                    _agent_stats["errors"] += 1

            elif resp.status_code in (503, 429):
                resp.success()  # Circuit breaker / rate limit — esperado bajo carga
            else:
                resp.failure(f"Status inesperado: {resp.status_code}")
                _agent_stats["errors"] += 1

    @task(2)
    def chat_direct(self):
        """Chat directo con el LLM (sin agente) — más rápido, testea el cache."""
        message = random.choice(CHAT_QUERIES)

        with self.client.post(
            "/chat",
            json={"message": message, "model": "llama3.2:3b", "use_cache": True},
            name="/chat",
            timeout=45,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("message"):
                        resp.success()
                    else:
                        resp.failure("Respuesta vacía")
                except Exception:
                    resp.failure("Error parseando")
            elif resp.status_code in (503, 429):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(1)
    def agent_complex(self):
        """Agente con múltiples herramientas — más lento, más intensivo."""
        query = random.choice(AGENT_COMPLEX_QUERIES)

        with self.client.post(
            "/agent/run",
            json={**query, "model": "llama3.2:3b"},
            name="/agent/run (complejo)",
            timeout=120,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("output"):
                        resp.success()
                        tool_count = len([s for s in data.get("steps", []) if s.get("action")])
                        print(f"  Agente complejo: {data['total_steps']} pasos, {tool_count} herramientas")
                    else:
                        resp.failure("Output vacío")
                except Exception as e:
                    resp.failure(str(e))
            elif resp.status_code in (503, 429):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")


# ── Eventos de Locust ─────────────────────────────────────────────────────────
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "=" * 55)
    print("🤖 Iniciando prueba de carga del Agente LLM (Sesión 7)")
    print(f"   Host: {environment.host}")
    print("=" * 55)
    print("\n💡 En otra terminal, monitorear:")
    print("   watch kubectl get hpa,pods -n llm-prod\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    total = stats.total

    print("\n" + "=" * 55)
    print("📊 LOCUST AGENTE LLM — RESUMEN FINAL")
    print("=" * 55)
    print(f"Total requests:     {total.num_requests}")
    print(f"Failures:           {total.num_failures}")
    print(f"Error rate:         {total.fail_ratio * 100:.2f}%")
    print(f"RPS promedio:       {total.current_rps:.2f}")
    print(f"P95 latencia:       {total.get_response_time_percentile(0.95):.0f}ms")
    print(f"P99 latencia:       {total.get_response_time_percentile(0.99):.0f}ms")

    if _agent_stats["total"] > 0:
        print(f"\n🤖 Estadísticas del Agente:")
        print(f"   Ejecuciones:    {_agent_stats['total']}")
        print(f"   Exitosas:       {_agent_stats['success']} "
              f"({_agent_stats['success']/_agent_stats['total']*100:.1f}%)")
        print(f"   Herramientas:   {json.dumps(_agent_stats['tool_calls'], indent=4)}")

    print("=" * 55 + "\n")
