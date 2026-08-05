"""
Tests Unitarios del Agente LLM — Sesión 7
==========================================
Pruebas para el agente ReAct y sus herramientas.

Ejecución:
    pytest tests/test_agent.py -v
    pytest tests/test_agent.py -v --tb=short   # Traceback corto
    pytest tests/test_agent.py -k "calculator" # Solo tests de calculadora
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def calculator():
    from agents.tools.calculator import CalculatorTool
    return CalculatorTool()


@pytest.fixture
def weather():
    from agents.tools.weather import WeatherTool
    return WeatherTool()


@pytest.fixture
def search():
    from agents.tools.search import SearchTool
    return SearchTool()


@pytest.fixture
def agent():
    """Agente con Ollama mockeado para no necesitar el servidor real."""
    from agents.llm_agent.agent import LLMAgent
    return LLMAgent(model="llama3.2:3b")


# ── Tests de Calculator ───────────────────────────────────────────────────────

class TestCalculatorTool:

    @pytest.mark.asyncio
    async def test_multiplicacion_basica(self, calculator):
        result = await calculator.run("1234 * 5678")
        assert "7,006,652" in result

    @pytest.mark.asyncio
    async def test_suma(self, calculator):
        result = await calculator.run("100 + 200")
        assert "300" in result

    @pytest.mark.asyncio
    async def test_sqrt(self, calculator):
        result = await calculator.run("sqrt(144)")
        assert "12" in result

    @pytest.mark.asyncio
    async def test_expresion_compleja(self, calculator):
        result = await calculator.run("365 * 24 * 60")
        assert "525,600" in result

    @pytest.mark.asyncio
    async def test_division_por_cero(self, calculator):
        result = await calculator.run("100 / 0")
        assert "División por cero" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_bloquea_codigo_peligroso(self, calculator):
        """El eval seguro debe bloquear intentos de ejecutar código arbitrario."""
        result = await calculator.run("__import__('os').system('ls')")
        assert "Error" in result or "no permitido" in result.lower()

    @pytest.mark.asyncio
    async def test_bloquea_os_system(self, calculator):
        result = await calculator.run("os.system('rm -rf /')")
        assert "Error" in result or "no permitido" in result.lower()

    @pytest.mark.asyncio
    async def test_pi(self, calculator):
        result = await calculator.run("pi * 2")
        # Resultado debe ser ~6.28
        assert "6.28" in result or "6.2831" in result

    @pytest.mark.asyncio
    async def test_simbolo_multiplicacion(self, calculator):
        """Debe manejar el símbolo × además del *"""
        result = await calculator.run("100 × 200")
        assert "20,000" in result or "20000" in result

    @pytest.mark.asyncio
    async def test_potencia(self, calculator):
        result = await calculator.run("2 ** 10")
        assert "1,024" in result or "1024" in result


# ── Tests de Weather ──────────────────────────────────────────────────────────

class TestWeatherTool:

    @pytest.mark.asyncio
    async def test_bogota(self, weather):
        result = await weather.run("Bogotá")
        assert "Bogotá" in result or "bogotá" in result.lower()
        assert "°C" in result

    @pytest.mark.asyncio
    async def test_medellin(self, weather):
        result = await weather.run("Medellín")
        assert "°C" in result
        assert "Medellín" in result or "22" in result

    @pytest.mark.asyncio
    async def test_ciudad_desconocida(self, weather):
        """Ciudades no en el mock deben retornar datos generados."""
        result = await weather.run("Timbuktu")
        assert "°C" in result
        assert "Timbuktu" in result

    @pytest.mark.asyncio
    async def test_contiene_humedad_y_viento(self, weather):
        result = await weather.run("Madrid")
        assert "humedad" in result.lower()
        assert "km/h" in result or "viento" in result.lower()

    @pytest.mark.asyncio
    async def test_case_insensitive(self, weather):
        """Debe funcionar con mayúsculas y minúsculas."""
        result_lower = await weather.run("bogota")
        result_upper = await weather.run("BOGOTA")
        assert "°C" in result_lower
        assert "°C" in result_upper


# ── Tests de Search ───────────────────────────────────────────────────────────

class TestSearchTool:

    @pytest.mark.asyncio
    async def test_buscar_kubernetes(self, search):
        result = await search.run("¿qué es kubernetes?")
        assert "Kubernetes" in result or "kubernetes" in result.lower()

    @pytest.mark.asyncio
    async def test_buscar_keda(self, search):
        result = await search.run("KEDA scale to zero")
        assert "KEDA" in result
        assert "zero" in result.lower() or "cero" in result.lower()

    @pytest.mark.asyncio
    async def test_buscar_ollama(self, search):
        result = await search.run("ollama local LLM")
        assert "Ollama" in result or "ollama" in result.lower()

    @pytest.mark.asyncio
    async def test_busqueda_sin_resultado(self, search):
        """Búsquedas sin resultado deben retornar mensaje útil."""
        result = await search.run("receta de paella valenciana")
        assert "no encontré" in result.lower() or "no encontr" in result.lower()

    @pytest.mark.asyncio
    async def test_buscar_k6(self, search):
        result = await search.run("prueba de carga k6")
        assert "k6" in result.lower() or "load" in result.lower()


# ── Tests del Parser ReAct ────────────────────────────────────────────────────

class TestReActParser:

    def setup_method(self):
        from agents.llm_agent.agent import LLMAgent
        self.agent = LLMAgent()

    def test_parsea_final_answer(self):
        response = """Thought: Ya tengo la información.
Final Answer: 1234 × 5678 = 7,006,652"""
        result = self.agent._parse_llm_response(response)
        assert result["type"] == "final_answer"
        assert "7,006,652" in result["content"]

    def test_parsea_action(self):
        response = """Thought: Necesito calcular.
Action: calculator
Action Input: 1234 * 5678"""
        result = self.agent._parse_llm_response(response)
        assert result["type"] == "action"
        assert result["action"] == "calculator"
        assert "1234 * 5678" in result["action_input"]

    def test_parsea_action_weather(self):
        response = """Thought: Necesito el clima.
Action: weather
Action Input: Bogotá"""
        result = self.agent._parse_llm_response(response)
        assert result["type"] == "action"
        assert result["action"] == "weather"
        assert "Bogotá" in result["action_input"]

    def test_respuesta_sin_formato(self):
        """Respuestas sin formato ReAct se tratan como Final Answer."""
        response = "El resultado es 42."
        result = self.agent._parse_llm_response(response)
        assert result["type"] == "final_answer"
        assert "42" in result["content"]

    def test_extrae_thought(self):
        response = """Thought: Este es mi razonamiento detallado.
Final Answer: Respuesta aquí."""
        result = self.agent._parse_llm_response(response)
        assert "razonamiento" in result.get("thought", "")


# ── Tests de Memoria del Agente ───────────────────────────────────────────────

class TestAgentMemory:

    def setup_method(self):
        from agents.llm_agent.agent import LLMAgent
        self.agent = LLMAgent()

    def test_guardar_y_recuperar_memoria(self):
        history = []
        self.agent._update_memory("sesion-1", "Hola", "Hola, ¿cómo puedo ayudarte?", history)
        assert "sesion-1" in self.agent._memory
        assert len(self.agent._memory["sesion-1"]) == 2

    def test_limpiar_memoria(self):
        history = []
        self.agent._update_memory("sesion-limpieza", "Test", "Response", history)
        assert "sesion-limpieza" in self.agent._memory
        self.agent.clear_memory("sesion-limpieza")
        assert "sesion-limpieza" not in self.agent._memory

    def test_memoria_max_10_mensajes(self):
        """La memoria no debe crecer indefinidamente."""
        history = []
        for i in range(10):
            self.agent._update_memory("sesion-larga", f"Pregunta {i}", f"Resp {i}", history)
            history = self.agent._memory.get("sesion-larga", [])
        # No debe tener más de 10 mensajes
        assert len(self.agent._memory.get("sesion-larga", [])) <= 10

    def test_sesiones_independientes(self):
        """Cada session_id tiene su propia memoria."""
        self.agent._update_memory("sesion-A", "Preg A", "Resp A", [])
        self.agent._update_memory("sesion-B", "Preg B", "Resp B", [])
        assert "sesion-A" in self.agent._memory
        assert "sesion-B" in self.agent._memory
        # Las sesiones no se mezclan
        mem_a = self.agent._memory["sesion-A"]
        assert all("A" in m["content"] or "A" in m["content"] for m in mem_a
                   if m["role"] == "user")


# ── Test de integración del agente (con Ollama mockeado) ─────────────────────

class TestAgentIntegration:

    @pytest.mark.asyncio
    async def test_agente_ejecuta_calculator(self):
        """Test end-to-end mockeando solo la llamada al LLM."""
        from agents.llm_agent.agent import LLMAgent

        agent = LLMAgent()

        # Mock del LLM: primero pide calculator, luego da Final Answer
        responses = iter([
            "Thought: Necesito calcular.\nAction: calculator\nAction Input: 100 * 200",
            "Thought: Tengo el resultado.\nFinal Answer: 100 × 200 = 20,000",
        ])

        async def mock_llm(prompt, model):
            return next(responses)

        agent._call_llm = mock_llm

        result = await agent.run("¿Cuánto es 100 * 200?", session_id="test-calc")

        assert result.success
        assert "20,000" in result.output or "20000" in result.output
        assert result.total_steps == 2
        # Verificar que se usó la herramienta
        tool_steps = [s for s in result.steps if s.action == "calculator"]
        assert len(tool_steps) == 1
        assert "20,000" in tool_steps[0].observation or "20000" in tool_steps[0].observation

    @pytest.mark.asyncio
    async def test_agente_responde_sin_herramienta(self):
        """El agente puede responder directamente sin usar herramientas."""
        from agents.llm_agent.agent import LLMAgent

        agent = LLMAgent()

        async def mock_llm(prompt, model):
            return "Thought: Conozco la respuesta.\nFinal Answer: El patrón ReAct combina razonamiento con acción."

        agent._call_llm = mock_llm

        result = await agent.run("¿Qué es ReAct?", session_id="test-direct")

        assert result.success
        assert "ReAct" in result.output
        assert result.total_steps == 1

    @pytest.mark.asyncio
    async def test_agente_maneja_herramienta_inexistente(self):
        """Si el LLM pide una herramienta que no existe, el agente continúa."""
        from agents.llm_agent.agent import LLMAgent

        agent = LLMAgent()

        responses = iter([
            "Thought: Usaré una herramienta.\nAction: herramienta_falsa\nAction Input: algo",
            "Thought: La herramienta falló, respondo directamente.\nFinal Answer: No pude usar esa herramienta.",
        ])

        async def mock_llm(prompt, model):
            return next(responses)

        agent._call_llm = mock_llm

        result = await agent.run("Usa herramienta_falsa", session_id="test-bad-tool")

        # El agente debe continuar y dar una respuesta final
        assert result.total_steps >= 1
        # La observación debe indicar el error
        if result.steps:
            assert "no existe" in result.steps[0].observation or "Disponibles" in result.steps[0].observation
