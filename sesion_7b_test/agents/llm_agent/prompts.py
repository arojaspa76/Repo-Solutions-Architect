"""
Prompts del Agente LLM ReAct — Sesión 7
==========================================
Los prompts son críticos para el comportamiento del agente.
Un prompt bien diseñado = agente confiable.
Un prompt malo = agente que alucina, loopea o ignora las herramientas.

Principios de diseño:
  1. Formato estricto y explícito (Thought/Action/Observation)
  2. Ejemplos concretos (few-shot)
  3. Instrucciones claras sobre cuándo parar
  4. Manejo de errores en el prompt
"""

# ── Prompt de sistema ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un asistente técnico experto en infraestructura cloud, 
Kubernetes, LLMs y arquitectura de sistemas distribuidos.

REGLAS IMPORTANTES:
1. Siempre razona paso a paso antes de actuar
2. Usa las herramientas disponibles cuando necesites información o cálculos
3. Si no necesitas herramientas, responde directamente con "Final Answer:"
4. Responde siempre en español
5. Sé conciso pero completo
6. Si una herramienta falla, dilo en la respuesta final
"""

# ── Prompt ReAct con few-shot ─────────────────────────────────────────────────
_REACT_TEMPLATE = """Tienes acceso a las siguientes herramientas:

{tools_description}

Usa el siguiente formato EXACTAMENTE:

Thought: [tu razonamiento sobre qué hacer]
Action: [nombre de la herramienta]
Action Input: [argumento para la herramienta]
Observation: [resultado de la herramienta — esto lo añade el sistema]
... (repite Thought/Action/Observation si necesitas más pasos)
Thought: [razonamiento final]
Final Answer: [respuesta final para el usuario]

Si NO necesitas ninguna herramienta, responde directamente:
Thought: Esta pregunta no requiere herramientas.
Final Answer: [tu respuesta]

EJEMPLOS:

Ejemplo 1 — Con herramienta:
  Pregunta: ¿Cuánto es 1500 * 365?
  Thought: El usuario quiere un cálculo. Usaré la calculadora.
  Action: calculator
  Action Input: 1500 * 365
  Observation: 547500
  Thought: El cálculo está hecho.
  Final Answer: 1500 × 365 = 547,500.

Ejemplo 2 — Sin herramienta:
  Pregunta: ¿Qué es el patrón ReAct?
  Thought: Esta es una pregunta conceptual que conozco, no necesito herramientas.
  Final Answer: ReAct (Reasoning + Acting) es un patrón de agentes LLM que combina razonamiento con acción. El agente alterna entre pensar qué hacer (Thought), ejecutar una herramienta (Action) y observar el resultado (Observation) hasta llegar a una respuesta final.

Ejemplo 3 — Múltiples herramientas:
  Pregunta: ¿Cuánto es 100 * 200 y qué clima hay en Madrid?
  Thought: Necesito calcular y obtener el clima. Haré los pasos por separado.
  Action: calculator
  Action Input: 100 * 200
  Observation: 20000
  Thought: Ahora necesito el clima de Madrid.
  Action: weather
  Action Input: Madrid
  Observation: Madrid: 22°C, soleado
  Thought: Tengo ambos resultados.
  Final Answer: 100 × 200 = 20,000. En Madrid actualmente hay 22°C con cielo soleado.

---

{history_section}

Pregunta del usuario: {user_input}

{scratchpad}
"""


def build_react_prompt(
    user_input: str,
    tools_description: str,
    scratchpad: str = "",
    history: list | None = None,
) -> str:
    """
    Construir el prompt ReAct completo.

    Args:
        user_input:        La pregunta del usuario
        tools_description: Descripción de las herramientas disponibles
        scratchpad:        Pasos previos en el loop actual
        history:           Historial de conversación de la sesión

    Returns:
        Prompt formateado listo para enviar al LLM
    """
    # Formatear historial de conversación
    history_section = ""
    if history:
        history_lines = []
        for msg in history[-6:]:  # Últimas 3 interacciones
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            history_lines.append(f"{role}: {msg['content'][:200]}")
        if history_lines:
            history_section = "Conversación previa:\n" + "\n".join(history_lines)

    return _REACT_TEMPLATE.format(
        tools_description=tools_description,
        user_input=user_input,
        history_section=history_section,
        scratchpad=scratchpad if scratchpad else "",
    )
