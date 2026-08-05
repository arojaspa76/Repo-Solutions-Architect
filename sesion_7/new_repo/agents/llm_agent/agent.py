"""
Agente LLM con patrón ReAct — Sesión 7
========================================
ReAct = Reasoning + Acting

El agente razona sobre qué herramienta usar, la ejecuta,
observa el resultado y decide si necesita más pasos o puede
responder al usuario.

Flujo:
  Pregunta del usuario
       ↓
  [LLM] Razona qué herramienta necesita
       ↓
  [Tool] Se ejecuta la herramienta
       ↓
  [LLM] Observa el resultado y decide continuar o responder
       ↓
  Respuesta final al usuario

Ejemplo:
  Input:  "¿Cuánto es 1234 × 5678 y qué clima hay en Bogotá?"
  Paso 1: calculator("1234 * 5678") → 7,006,652
  Paso 2: weather("Bogotá")         → 14°C, parcialmente nublado
  Output: "1234 × 5678 = 7,006,652. En Bogotá hay 14°C y está
           parcialmente nublado."

Uso:
    agent = LLMAgent()
    result = await agent.run("¿Cuánto es 100 * 200?", session_id="s1")
    print(result.output)
"""

import asyncio
import logging
import time
import os
from typing import Optional
from dataclasses import dataclass, field

import httpx

from agents.tools.calculator import CalculatorTool
from agents.tools.weather import WeatherTool
from agents.tools.search import SearchTool
from agents.llm_agent.prompts import SYSTEM_PROMPT, build_react_prompt

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:3b")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.1"))


# ── Estructuras de datos ───────────────────────────────────────────────────────
@dataclass
class AgentStep:
    """Un paso de razonamiento del agente."""
    step_number: int
    thought: str           # Qué está pensando el agente
    action: Optional[str]  # Qué herramienta va a usar
    action_input: str      # Con qué argumento
    observation: str       # Resultado de la herramienta
    duration_ms: float


@dataclass
class AgentResult:
    """Resultado final de una ejecución del agente."""
    input: str
    output: str
    steps: list[AgentStep] = field(default_factory=list)
    total_steps: int = 0
    total_duration_ms: float = 0.0
    model: str = DEFAULT_MODEL
    session_id: str = ""
    success: bool = True
    error: Optional[str] = None
    tokens_used: int = 0


# ── Agente LLM ─────────────────────────────────────────────────────────────────
class LLMAgent:
    """
    Agente LLM con patrón ReAct.

    Características:
    - Máximo MAX_STEPS pasos para evitar loops infinitos
    - Timeout configurable para toda la ejecución
    - Memoria de conversación por session_id
    - Métricas de latencia por paso y total
    - Soporte para Ollama local y APIs cloud
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.tools = {
            "calculator": CalculatorTool(),
            "weather": WeatherTool(),
            "search": SearchTool(),
        }
        # Memoria simple: session_id → historial de mensajes
        self._memory: dict[str, list[dict]] = {}
        logger.info(
            f"🤖 LLMAgent iniciado | modelo={model} | "
            f"herramientas={list(self.tools.keys())}"
        )

    # ── Ejecución principal ────────────────────────────────────────────────────
    async def run(
        self,
        user_input: str,
        session_id: str = "default",
        model: Optional[str] = None,
    ) -> AgentResult:
        """
        Ejecutar el agente con un input del usuario.

        El loop ReAct:
        1. Construir prompt con historial + herramientas disponibles
        2. LLM genera Thought + Action + Action Input
        3. Ejecutar herramienta y obtener Observation
        4. Si el LLM dice "Final Answer" → retornar
        5. Repetir hasta MAX_STEPS

        Args:
            user_input:  La pregunta o tarea del usuario
            session_id:  ID de sesión para memoria de conversación
            model:       Modelo Ollama (override del default)

        Returns:
            AgentResult con output, pasos y métricas
        """
        start_total = time.perf_counter()
        active_model = model or self.model
        steps: list[AgentStep] = []

        # Historial de la sesión (memoria conversacional)
        history = self._memory.get(session_id, [])

        # Descripción de herramientas para el prompt
        tools_desc = self._build_tools_description()

        # Contexto acumulado para el loop ReAct
        scratchpad = ""

        logger.info(f"🚀 Agent run | session={session_id} | input='{user_input[:60]}...'")

        try:
            for step_num in range(1, MAX_STEPS + 1):
                step_start = time.perf_counter()

                # 1. Construir prompt ReAct
                prompt = build_react_prompt(
                    user_input=user_input,
                    tools_description=tools_desc,
                    scratchpad=scratchpad,
                    history=history,
                )

                # 2. Llamar al LLM
                llm_response = await self._call_llm(prompt, active_model)

                # 3. Parsear la respuesta del LLM
                parsed = self._parse_llm_response(llm_response)

                if parsed["type"] == "final_answer":
                    # El agente llegó a una conclusión
                    final_output = parsed["content"]
                    duration_ms = (time.perf_counter() - step_start) * 1000

                    steps.append(AgentStep(
                        step_number=step_num,
                        thought=parsed.get("thought", ""),
                        action=None,
                        action_input="",
                        observation="[Respuesta final generada]",
                        duration_ms=duration_ms,
                    ))

                    # Guardar en memoria de sesión
                    self._update_memory(session_id, user_input, final_output, history)

                    total_ms = (time.perf_counter() - start_total) * 1000
                    logger.info(
                        f"✅ Agent completado en {step_num} pasos | "
                        f"{total_ms:.0f}ms total"
                    )
                    return AgentResult(
                        input=user_input,
                        output=final_output,
                        steps=steps,
                        total_steps=step_num,
                        total_duration_ms=round(total_ms, 2),
                        model=active_model,
                        session_id=session_id,
                        success=True,
                    )

                elif parsed["type"] == "action":
                    # El agente quiere usar una herramienta
                    tool_name = parsed["action"]
                    tool_input = parsed["action_input"]
                    thought = parsed.get("thought", "")

                    logger.info(f"  Paso {step_num}: {tool_name}('{tool_input}')")

                    # 4. Ejecutar herramienta
                    observation = await self._execute_tool(tool_name, tool_input)

                    duration_ms = (time.perf_counter() - step_start) * 1000
                    steps.append(AgentStep(
                        step_number=step_num,
                        thought=thought,
                        action=tool_name,
                        action_input=tool_input,
                        observation=observation,
                        duration_ms=duration_ms,
                    ))

                    # 5. Agregar al scratchpad para el próximo loop
                    scratchpad += (
                        f"\nThought: {thought}"
                        f"\nAction: {tool_name}"
                        f"\nAction Input: {tool_input}"
                        f"\nObservation: {observation}\n"
                    )

                else:
                    # Respuesta no parseable — tratar como respuesta final
                    final_output = llm_response
                    total_ms = (time.perf_counter() - start_total) * 1000
                    self._update_memory(session_id, user_input, final_output, history)
                    return AgentResult(
                        input=user_input,
                        output=final_output,
                        steps=steps,
                        total_steps=step_num,
                        total_duration_ms=round(total_ms, 2),
                        model=active_model,
                        session_id=session_id,
                        success=True,
                    )

            # Límite de pasos alcanzado
            total_ms = (time.perf_counter() - start_total) * 1000
            logger.warning(f"⚠️ Agent alcanzó límite de {MAX_STEPS} pasos")
            fallback = (
                f"He procesado {MAX_STEPS} pasos pero no pude completar la tarea. "
                f"Por favor reformula la pregunta de manera más específica."
            )
            return AgentResult(
                input=user_input,
                output=fallback,
                steps=steps,
                total_steps=MAX_STEPS,
                total_duration_ms=round(total_ms, 2),
                model=active_model,
                session_id=session_id,
                success=False,
                error="max_steps_reached",
            )

        except asyncio.TimeoutError:
            total_ms = (time.perf_counter() - start_total) * 1000
            logger.error(f"⏱ Agent timeout después de {total_ms:.0f}ms")
            return AgentResult(
                input=user_input,
                output="El agente no pudo completar la tarea a tiempo.",
                steps=steps,
                total_steps=len(steps),
                total_duration_ms=round(total_ms, 2),
                model=active_model,
                session_id=session_id,
                success=False,
                error="timeout",
            )
        except Exception as e:
            total_ms = (time.perf_counter() - start_total) * 1000
            logger.error(f"❌ Agent error: {e}")
            return AgentResult(
                input=user_input,
                output=f"Error al procesar la solicitud: {str(e)}",
                steps=steps,
                total_steps=len(steps),
                total_duration_ms=round(total_ms, 2),
                model=active_model,
                session_id=session_id,
                success=False,
                error=str(e),
            )

    # ── Llamada al LLM ─────────────────────────────────────────────────────────
    async def _call_llm(self, prompt: str, model: str) -> str:
        """Llamar a Ollama de forma asíncrona."""
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": TEMPERATURE,
                        "num_predict": 512,  # Limitar tokens para más velocidad
                    },
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

    # ── Parseo de respuesta ReAct ──────────────────────────────────────────────
    def _parse_llm_response(self, response: str) -> dict:
        """
        Parsear la respuesta del LLM en formato ReAct.

        El LLM debe responder en uno de estos formatos:

        Formato 1 — Usar herramienta:
          Thought: [razonamiento]
          Action: [nombre_herramienta]
          Action Input: [argumento]

        Formato 2 — Respuesta final:
          Thought: [razonamiento final]
          Final Answer: [respuesta para el usuario]
        """
        lines = response.strip().split("\n")
        result = {"type": "unknown", "thought": "", "content": response}

        thought_lines = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            if line_stripped.startswith("Thought:"):
                thought_lines.append(line_stripped.replace("Thought:", "").strip())

            elif line_stripped.startswith("Final Answer:"):
                result["type"] = "final_answer"
                result["thought"] = " ".join(thought_lines)
                # La respuesta final puede ser multilínea
                final_content = line_stripped.replace("Final Answer:", "").strip()
                remaining = "\n".join(lines[i + 1:]).strip()
                result["content"] = f"{final_content} {remaining}".strip()
                return result

            elif line_stripped.startswith("Action:"):
                action = line_stripped.replace("Action:", "").strip()
                # Buscar Action Input en las líneas siguientes
                action_input = ""
                for next_line in lines[i + 1:]:
                    if next_line.strip().startswith("Action Input:"):
                        action_input = next_line.strip().replace("Action Input:", "").strip()
                        break

                result["type"] = "action"
                result["thought"] = " ".join(thought_lines)
                result["action"] = action.lower().replace(" ", "_")
                result["action_input"] = action_input
                return result

        # Si el LLM no sigue el formato exacto, tratar como respuesta final
        result["type"] = "final_answer"
        result["content"] = response
        return result

    # ── Ejecutar herramienta ───────────────────────────────────────────────────
    async def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Ejecutar una herramienta y retornar la observación."""
        tool = self.tools.get(tool_name)
        if not tool:
            available = ", ".join(self.tools.keys())
            return f"Error: herramienta '{tool_name}' no existe. Disponibles: {available}"
        try:
            return await tool.run(tool_input)
        except Exception as e:
            return f"Error ejecutando {tool_name}: {str(e)}"

    # ── Memoria ────────────────────────────────────────────────────────────────
    def _update_memory(
        self,
        session_id: str,
        user_input: str,
        output: str,
        history: list,
    ):
        """Actualizar historial de conversación."""
        updated = history + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": output},
        ]
        # Mantener solo las últimas 10 interacciones (5 turnos)
        self._memory[session_id] = updated[-10:]

    def clear_memory(self, session_id: str):
        """Limpiar historial de una sesión."""
        self._memory.pop(session_id, None)

    def _build_tools_description(self) -> str:
        """Construir descripción de herramientas para el prompt."""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions)
