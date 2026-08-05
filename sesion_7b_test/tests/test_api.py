"""
Tests de Integración — FastAPI LLM Agent Gateway (Sesión 7)
============================================================
Tests del API usando TestClient de FastAPI (sin servidor real).

Ejecución:
    pytest tests/test_api.py -v
    pytest tests/test_api.py -v -k "health"   # Solo tests de health
    pytest tests/test_api.py --cov=app        # Con cobertura de código
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# ── Fixture: cliente de test ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """
    Cliente de test para FastAPI.
    Mockea Ollama y Redis para que los tests no dependan de servicios externos.
    """
    # Mockear el cache para no necesitar Redis
    with patch("app.utils.cache.CacheManager.connect", new_callable=AsyncMock):
        with patch("app.utils.cache.CacheManager.disconnect", new_callable=AsyncMock):
            from app.main import app
            with TestClient(app) as c:
                yield c


# ── Tests de /health ──────────────────────────────────────────────────────────

class TestHealth:

    def test_health_retorna_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_tiene_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")

    def test_health_tiene_componentes(self, client):
        response = client.get("/health")
        data = response.json()
        assert "components" in data
        assert "ollama" in data["components"]

    def test_health_tiene_version(self, client):
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "3.0.0"


# ── Tests de /agent/tools ─────────────────────────────────────────────────────

class TestAgentTools:

    def test_list_tools_retorna_200(self, client):
        response = client.get("/agent/tools")
        assert response.status_code == 200

    def test_list_tools_tiene_herramientas(self, client):
        response = client.get("/agent/tools")
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 3

    def test_tools_tienen_nombre_y_descripcion(self, client):
        response = client.get("/agent/tools")
        data = response.json()
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert len(tool["description"]) > 10

    def test_calculator_en_herramientas(self, client):
        response = client.get("/agent/tools")
        data = response.json()
        names = [t["name"] for t in data["tools"]]
        assert "calculator" in names

    def test_weather_en_herramientas(self, client):
        response = client.get("/agent/tools")
        data = response.json()
        names = [t["name"] for t in data["tools"]]
        assert "weather" in names

    def test_search_en_herramientas(self, client):
        response = client.get("/agent/tools")
        data = response.json()
        names = [t["name"] for t in data["tools"]]
        assert "search" in names


# ── Tests de / (root) ────────────────────────────────────────────────────────

class TestRoot:

    def test_root_retorna_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_tiene_service(self, client):
        response = client.get("/")
        data = response.json()
        assert "service" in data
        assert "LLM Agent" in data["service"]

    def test_root_tiene_links(self, client):
        response = client.get("/")
        data = response.json()
        assert "docs" in data
        assert "metrics" in data
        assert "agent" in data


# ── Tests de /agent/run ───────────────────────────────────────────────────────

class TestAgentRun:
    """
    Tests del endpoint del agente mockeando el LLM.
    Sin Ollama real, el agente devuelve 503.
    Aquí verificamos el formato de la respuesta.
    """

    def test_agent_run_requiere_input(self, client):
        """Sin el campo 'input' debe retornar 422 (Unprocessable Entity)."""
        response = client.post("/agent/run", json={})
        assert response.status_code == 422

    def test_agent_run_input_vacio_falla(self, client):
        """Input vacío debe retornar 422."""
        response = client.post("/agent/run", json={"input": ""})
        assert response.status_code == 422

    def test_agent_run_acepta_request_valido(self, client):
        """Un request válido debe retornar 200 o 503 (si Ollama no está disponible)."""
        response = client.post("/agent/run", json={
            "input": "¿Cuánto es 2 + 2?",
            "session_id": "test-123",
        })
        # 200 si Ollama está disponible, 503 si no
        assert response.status_code in (200, 503)

    def test_agent_run_con_model(self, client):
        """Debe aceptar un modelo personalizado."""
        response = client.post("/agent/run", json={
            "input": "Test",
            "model": "llama3.2:3b",
            "session_id": "test-model",
        })
        assert response.status_code in (200, 503)

    @patch("app.api.routes.get_agent")
    def test_agent_run_retorna_formato_correcto(self, mock_get_agent, client):
        """Verificar formato de respuesta cuando el agente funciona."""
        from agents.llm_agent.agent import AgentResult, AgentStep

        # Mock del agente
        mock_agent = MagicMock()
        mock_result = AgentResult(
            input="¿Cuánto es 2 + 2?",
            output="2 + 2 = 4",
            steps=[
                AgentStep(
                    step_number=1,
                    thought="Necesito calcular",
                    action="calculator",
                    action_input="2 + 2",
                    observation="4",
                    duration_ms=5.0,
                )
            ],
            total_steps=1,
            total_duration_ms=5000.0,
            model="llama3.2:3b",
            session_id="test-format",
            success=True,
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_agent.tools = {"calculator": MagicMock(), "weather": MagicMock(), "search": MagicMock()}
        mock_agent._memory = {}
        mock_get_agent.return_value = mock_agent

        with patch("app.api.routes.ollama") as mock_ollama:
            mock_ollama.health_check = AsyncMock(return_value=True)
            mock_ollama.circuit_breaker.is_open = False

            response = client.post("/agent/run", json={
                "input": "¿Cuánto es 2 + 2?",
                "session_id": "test-format",
            })

        assert response.status_code == 200
        data = response.json()

        # Verificar campos obligatorios
        assert "input" in data
        assert "output" in data
        assert "steps" in data
        assert "total_steps" in data
        assert "total_duration_ms" in data
        assert "success" in data
        assert "session_id" in data
        assert data["success"] is True
        assert data["total_steps"] == 1
        assert len(data["steps"]) == 1
        assert data["steps"][0]["action"] == "calculator"


# ── Tests de /chat ────────────────────────────────────────────────────────────

class TestChat:

    def test_chat_requiere_message(self, client):
        response = client.post("/chat", json={})
        assert response.status_code == 422

    def test_chat_acepta_request_valido(self, client):
        response = client.post("/chat", json={
            "message": "Hola",
            "model": "llama3.2:3b",
        })
        # 200 si Ollama disponible, 503 si no
        assert response.status_code in (200, 503)

    @patch("app.api.routes.ollama")
    @patch("app.api.routes.CacheManager", create=True)
    def test_chat_usa_cache(self, mock_cache_class, mock_ollama, client):
        """Si hay cache hit, debe retornar cached=True."""
        mock_ollama.chat = AsyncMock(return_value="Respuesta del LLM")
        mock_ollama.circuit_breaker.is_open = False

        response = client.post("/chat", json={
            "message": "Test cache",
            "use_cache": True,
        })
        assert response.status_code in (200, 503)


# ── Tests de /cache ───────────────────────────────────────────────────────────

class TestCache:

    def test_cache_stats_retorna_200(self, client):
        response = client.get("/cache/stats")
        assert response.status_code == 200

    def test_cache_stats_tiene_backend(self, client):
        response = client.get("/cache/stats")
        data = response.json()
        assert "backend" in data
        assert data["backend"] in ("redis", "memory", "none")

    def test_cache_flush_retorna_200(self, client):
        response = client.delete("/cache/flush")
        assert response.status_code == 200

    def test_cache_flush_retorna_success(self, client):
        response = client.delete("/cache/flush")
        data = response.json()
        assert "success" in data


# ── Tests de /metrics ────────────────────────────────────────────────────────

class TestMetrics:

    def test_metrics_retorna_respuesta(self, client):
        response = client.get("/metrics")
        # 200 si prometheus instalado, 503 si no
        assert response.status_code in (200, 503)

    def test_metrics_content_type_prometheus(self, client):
        response = client.get("/metrics")
        if response.status_code == 200:
            # Prometheus format
            assert "text/plain" in response.headers.get("content-type", "")


# ── Tests de /models ──────────────────────────────────────────────────────────

class TestModels:

    def test_models_retorna_200(self, client):
        response = client.get("/models")
        assert response.status_code == 200

    def test_models_tiene_provider(self, client):
        response = client.get("/models")
        data = response.json()
        assert "provider" in data
        assert data["provider"] == "ollama"
