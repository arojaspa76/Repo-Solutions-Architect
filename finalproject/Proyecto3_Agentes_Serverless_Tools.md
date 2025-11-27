# PROYECTO 3 – Arquitectura de Agentes con Serverless y Tools
## "LLM Agentic Architecture with Serverless Tools Integration"

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Officer  
**Correo:** andres.rojas@triskelss.com  
**Nivel:** Avanzado  
**Modalidad:** LLM Agents + Serverless + Tool-Calling + Workflow Orchestration

---

# Componentes obligatorios del proyecto (12 pasos formales)

Este proyecto exige diseñar y construir un **agente inteligente** capaz de razonar, decidir acciones, llamar herramientas serverless y ejecutar workflows complejos.

---

## 1. Definición Avanzada del Caso de Uso del Agente

El estudiante debe definir un escenario real, por ejemplo:

- Agente para soporte de TI  
- Agente administrativo para procesos operativos  
- Agente para logística, inventarios, compras  
- Agente médico/financiero (simulado)

Debe incluir:

- Usuarios objetivo  
- Flujo completo de tareas del agente  
- Límites del sistema  
- Inputs/outputs (texto, JSON)

**KPIs:**

- Task Success Rate  
- Tool-Call Success Rate  
- Latencia de resolución de tareas  
- Pasos promedio por tarea  
- Errores detectados y manipulados correctamente  

---

## 2. Selección del Modelo + Requerimientos de Infraestructura

El estudiante debe elegir un LLM con capacidades de **function calling**:

### LLMs gestionados:
- Azure OpenAI (GPT-4o, GPT-4o mini)  
- AWS Bedrock (Claude 3.5 Sonnet / Haiku, Llama 3, Mistral Large)  
- Google Vertex AI (Gemini 1.5 Pro/Flash/2.0)

### Open-source self-hosted:
- Llama 3  
- Mistral  
- Qwen  
- Gemma  

Debe justificar:

- Capacidad de razonamiento  
- Velocidad y costo  
- Soporte nativo de tool-calling  
- Latencia esperada  
- Riesgos y restricciones  

---

## 3. Selección y Justificación del Patrón de Diseño LLM (Agentic)

El estudiante debe seleccionar al menos un patrón:

### Patrón principal:
- **ReAct (Reason + Act) + Tool-Calling**

### Patrones complementarios (opcional):
- Planner–Executor  
- Multi-Agent (agente especialista)  
- Memory Pattern  
- Guardrail Pattern  
- LLM-as-a-Judge  
- Self-Reflection Pattern  

Debe incluir:

- Diagrama del flujo ReAct  
- Explicación del mecanismo de decisión  
- Manejo del contexto  
- Trade-offs del patrón seleccionado  

---

## 4. Contenerización con Docker

Se deben contenerizar los servicios propios:

- Orchestrator backend (FastAPI / Node / Go)  
- APIs internas simuladas  
- Servicios auxiliares (logging, mocks)

Requisitos:

- Multi-stage  
- Non-root  
- Imágenes livianas  
- Secrets externos  
- Vulnerability scanning  

---

## 5. Tooling Serverless (Azure Functions / AWS Lambda / Cloud Functions)

Cada **tool** debe ser una función serverless real.

Ejemplos:

- `get_user_info(id)`  
- `create_ticket(payload)`  
- `validate_payment(data)`  
- `send_notification(channel, body)`  

Cada función debe:

- Tener contrato JSON input/output  
- Manejar errores  
- Ser idempotente  
- Estar registrada como tool para el LLM  

---

## 6. Arquitectura Lógica del Sistema de Agentes

El entregable debe incluir un diagrama con:

- Interfaz del usuario (CLI/Web/API)  
- Backend orchestrator  
- LLM provider  
- Tools serverless  
- Workflow Orchestrator  
- Logging + Monitoring  

Y el flujo:

**Usuario → Agente → LLM → Tool(s) → Workflow(s) → LLM → Usuario**

---

## 7. Diseño del Conjunto de Tools (APIs Internas Simuladas)

Debe incluir:

- Lista de tools (mínimo 3–5)  
- Input schema  
- Output schema  
- Códigos de error  
- Documentación para el LLM (tool schema JSON)  

---

## 8. Administración de Workflows con Step Functions / Durable Functions

El agente debe interactuar con un flujo multi-paso:

- AWS Step Functions  
- Azure Durable Functions  
- Google Workflows  

Debe incluir:

- Diagrama del workflow  
- Manejo de errores  
- Reintentos  
- Integración desde el agente  

---

## 9. CI/CD Completo

El pipeline debe:

- Construir imágenes Docker  
- Desplegar Functions/Lambda/Cloud Functions  
- Desplegar el orquestador  
- Manejar variables y secrets  
- Correr tests automáticos  

---

## 10. Optimización de Costos y Performance

El estudiante debe entregar:

- Costo por 1k tokens  
- Costo por invocación serverless  
- Optimización de steps ReAct  
- Comparación: modelo pequeño vs grande  
- Estrategias:
  - cache  
  - modelos small-first  
  - reducción de profundidad del reasoning  

---

## 11. Observabilidad, Logs y Auditoría

Debe incluir:

- Logs del agente  
- Logs de tools  
- Latencias por tool  
- Tool-call success rate  
- Trazabilidad completa: prompts, acciones, respuestas  

Herramientas:

- AWS CloudWatch / X-Ray  
- Azure Monitor / Application Insights  
- GCP Logging / Cloud Trace  

---

## 12. Documentación Final Profesional

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Caso de uso  
- Modelo  
- Patrón agentic  
- Arquitectura  
- Tools  
- Workflows  
- Estrategias de optimización  
- Pruebas  
- Resultados  
- Riesgos y mitigaciones  

---

# Tabla de Evaluación por Componentes – Proyecto 3

| #  | Componente del Proyecto                                  | Descripción de Evaluación                                                                 | Puntaje |
|----|----------------------------------------------------------|--------------------------------------------------------------------------------------------|---------|
| 1  | Definición del Caso de Uso                               | Claridad, realismo, KPIs definidos.                                                       | **10** |
| 2  | Selección del Modelo + Infraestructura                   | Justificación del LLM, costos, capacidades de tool-calling.                               | **10** |
| 3  | Patrón de Diseño LLM (ReAct / Agentic)                   | Diagrama, integración de tools, trade-offs.                                               | **10** |
| 4  | Docker/Contenerización                                   | Calidad de imágenes, seguridad, eficiencia.                                               | **8**  |
| 5  | Tooling Serverless                                       | Diseño de functions/Lambda, contratos JSON, calidad técnica.                              | **8**  |
| 6  | Arquitectura de la Solución                              | Diagrama profesional y coherente.                                                         | **10** |
| 7  | Diseño del Conjunto de Tools                             | Documentación, schemas, manejo de errores.                                                | **10** |
| 8  | Workflows Serverless                                     | Correcta orquestación, manejo de fallos, integración.                                     | **6**  |
| 9  | CI/CD                                                    | Deploy automático, tests, pipelines funcionales.                                          | **6**  |
| 10 | Optimización de Costos y Performance                     | Análisis cuantitativo, estrategias FinOps.                                                | **7**  |
| 11 | Observabilidad, Logs y Auditoría                         | Métricas, logs, trazabilidad completa.                                                    | **7**  |
| 12 | Documentación Final                                      | Claridad, profundidad técnica, completitud.                                               | **8**  |

**Total: 100 puntos**

---

# Resumen de Ponderación

| Categoría                    | Peso |
|------------------------------|-------|
| Arquitectura & Diseño        | **45%** |
| Implementación Técnica       | **40%** |
| Documentación & Análisis     | **15%** |

---

# Aprendizajes esperados

- Construcción de **LLM Agents** con patrones ReAct  
- Tool-calling profesional  
- Integración real con funciones serverless  
- Orquestación de workflows empresariales  
- Construcción de Agentes capaces de ejecutar tareas complejas  
- Buenas prácticas de logging, observabilidad y trazabilidad  
- Diseño y documentación de sistemas agentic empresariales  

