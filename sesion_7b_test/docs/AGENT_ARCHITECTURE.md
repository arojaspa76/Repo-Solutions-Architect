# 🤖 Arquitectura del Agente LLM — Patrón ReAct

## ¿Qué es un Agente LLM?

Un **agente LLM** es un sistema donde el LLM no solo genera texto, sino que **toma decisiones** sobre qué acciones ejecutar para completar una tarea.

```
Sistema tradicional:   Usuario → LLM → Respuesta
Sistema con agente:    Usuario → LLM → Decidir → Herramienta → Observar → LLM → Respuesta
```

## El Patrón ReAct (Reasoning + Acting)

Publicado por Yao et al. (2022). El agente alterna entre razonar y actuar:

```
Thought: Razono sobre qué necesito hacer
Action: Decido qué herramienta usar
Action Input: El argumento para la herramienta
Observation: El resultado que devuelve la herramienta
... (repito si necesito más pasos)
Final Answer: La respuesta final para el usuario
```

### Ejemplo completo

```
Usuario: "¿Cuánto es 1234 * 5678 y qué clima hay en Bogotá?"

[Paso 1]
Thought: Necesito calcular una multiplicación. Usaré la calculadora.
Action: calculator
Action Input: 1234 * 5678
Observation: 7,006,652

[Paso 2]
Thought: Ahora necesito el clima de Bogotá. Usaré la herramienta weather.
Action: weather
Action Input: Bogotá
Observation: Bogotá: 14°C, parcialmente nublado, humedad 75%

[Paso 3]
Thought: Tengo ambos resultados. Puedo responder.
Final Answer: 1234 × 5678 = 7,006,652. En Bogotá hay 14°C 
con cielo parcialmente nublado y humedad del 75%.
```

## Arquitectura del Código

```
agents/
├── llm_agent/
│   ├── agent.py         ← Motor del agente (loop ReAct)
│   └── prompts.py       ← Prompts del sistema y few-shot examples
└── tools/
    ├── calculator.py    ← Cálculos matemáticos (eval seguro con whitelist)
    ├── weather.py       ← Clima (mock; en prod: API real)
    └── search.py        ← Búsqueda (mock; en prod: Tavily/Bing/Google)
```

## Por qué el Agente es MÁS LENTO que una API Simple

| Operación | Latencia típica |
|-----------|----------------|
| Chat simple (sin agente) | 2-5 seg |
| Agente, 1 herramienta | 5-15 seg |
| Agente, 2 herramientas | 10-25 seg |
| Agente, 3+ herramientas | 20-45 seg |

Cada paso ReAct = 1 llamada al LLM. Un agente con 3 pasos = 3 × latencia del LLM.

**Mitigación:** Cache para respuestas repetidas. Si la misma pregunta ya fue respondida, el resultado se sirve en <50ms desde Redis.

## Seguridad en Herramientas

La herramienta `calculator` usa evaluación segura:

```python
# ❌ PELIGROSO: eval(expression) directamente
eval("os.system('rm -rf /')")  # ← El LLM podría inyectar esto

# ✅ SEGURO: AST whitelist
_SAFE_NAMES = {"sqrt": math.sqrt, "sin": math.sin, "pi": math.pi}
tree = ast.parse(expression, mode="eval")
_validate_ast(tree)  # ← Solo permite nodos seguros
eval(compile(tree, "<string>", "eval"), {"__builtins__": {}}, _SAFE_NAMES)
```

## Escalabilidad del Agente en K8s

El agente es **stateful** (guarda memoria de sesión en RAM).

**Problema con múltiples réplicas:** si el usuario va al pod A en el request 1 y al pod B en el request 2, la memoria de la sesión se pierde.

**Solución:** Externalizar la memoria a Redis:

```python
# En lugar de:
self._memory: dict[str, list] = {}  # ← En RAM del pod

# Usar:
await redis.set(f"session:{session_id}", json.dumps(history), ex=3600)
history = json.loads(await redis.get(f"session:{session_id}") or "[]")
```

Con Redis, todos los pods comparten la misma memoria de sesión — el HPA puede escalar sin problemas.
