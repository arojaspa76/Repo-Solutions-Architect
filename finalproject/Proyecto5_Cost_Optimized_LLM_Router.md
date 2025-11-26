# PROYECTO 5 – Cost-Optimized LLM Architecture with Autoscaling Router
## "Cost-Efficient Multi-Model Router for LLM Workloads"

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Officer  
**Correo:** andres.rojas@triskelss.com  
**Nivel:** Avanzado / Maestría  
**Modalidad:** Multi-Model Routing + Cost Optimization + Serverless + LLM Architecture

---

# Componentes obligatorios del proyecto (12 pasos formales)

Este proyecto exige diseñar un **router inteligente y autoscalable** que seleccione el modelo LLM óptimo según costo, complejidad y tipo de consulta.

---

## 1. Definición Avanzada del Caso de Uso del Router

El estudiante debe definir un caso donde múltiples modelos sean necesarios:

- Consultas simples → **modelo barato**  
- Tareas generativas → **modelo mediano**  
- Razonamiento complejo → **modelo premium (GPT‑4o / Claude 3.5 / Gemini Ultra)**  

Debe definir:

- Tipos de consultas soportadas  
- Reglas de negocio  
- Latencia esperada  
- Cost constraints  
- Inputs/outputs  
- Límites del router  

**KPI obligatorios:**

- Routing Accuracy  
- Cost Savings %  
- Latencia promedio por tipo de consulta  
- Throughput del router  
- Costo total por 1k requests  

---

## 2. Selección del Modelo + Requerimientos de Infraestructura

Debe elegir **mínimo 3 modelos**:

### Modelos económicos:
- GPT‑4o mini  
- Claude Haiku  
- Gemini Flash  
- Mistral Small  

### Modelos medianos:
- GPT‑4 Turbo  
- Claude Sonnet  
- Gemini Pro  

### Modelos premium:
- GPT‑4o  
- Claude 3.5 Opus  
- Gemini Ultra  

Debe justificar:

- Precio por 1k tokens  
- Latencia típica  
- Capacidades (reasoning, coding, summarization)  
- Riesgos y limitaciones  

Debe seleccionar una o más clouds:

- **AWS:** Lambda + Bedrock + API Gateway  
- **Azure:** Function Apps + AOAI + API Management  
- **GCP:** Cloud Run + Vertex AI  

---

## 3. Selección y Justificación del Patrón de Diseño LLM

El estudiante debe seleccionar al menos uno:

### Patrones permitidos:
- **Model Router Pattern** (principal obligatorio)  
- **Speculative Decoding Pattern**  
- **Guardrail Pattern**  
- **Small-to-Big Cascade Pattern**  
- **Context Optimization Pattern**  
- **LLM-as-a-Judge** para verificar calidad  

Debe incluir:

- Diagrama del router  
- Cómo se clasifican consultas  
- Cálculo de “query complexity”  
- Reglas y heurísticas  
- Trade-offs  

---

## 4. Contenerización con Docker

Debe contenerizar:

- Router backend  
- Clasificador de consultas (FastAPI/Node/Go)  
- Módulo de logging/metrics  

Requisitos:

- Multi-stage  
- Light-weight base image  
- No root user  
- Secrets externos  
- Vulnerability scanning  

---

## 5. Orquestación Serverless

Dependiendo de la cloud:

### AWS:
- API Gateway  
- Lambda  
- Bedrock models  

### Azure:
- API Management  
- Functions  
- Azure OpenAI  

### GCP:
- Cloud Run  
- Vertex AI  

El router debe autoscale según demanda:

- Concurrency-based autoscaling  
- Minimum warm instances  
- Cold-start mitigation  

---

## 6. Arquitectura Completa Multicloud (opcional)

Debe incluir:

- Router API (punto de entrada)  
- Clasificador de consultas  
- LLM selector  
- Modelo económico  
- Modelo mediano  
- Modelo premium  
- Logs/Metrics  
- Opcional: Caching layer (Redis/Cloud Memorystore)  

Diagrama obligatorio en Mermaid o PlantUML.

---

## 7. Diseño del Pipeline de Routing

Debe incluir:

1. Input de usuario  
2. Query classifier  
3. Decision tree o ML classifier  
4. Selección de modelo  
5. Ejecución  
6. Validación opcional (LLM-as-a-Judge)  
7. Respuesta  

Experimentos obligatorios:

- Distintas estrategias de routing  
- Comparación de costos  
- Comparación de latencias  
- Calidad subjetiva (BLEU, ROUGE o Judge Model)  

---

## 8. Infraestructura de Serving (Managed)

Debe incluir:

- Optimización de endpoints  
- Uso de embeddings para clasificación avanzada  
- Uso de modelos diferentes en paralelo  
- Evaluación de concurrency  
- Configuración de timeouts adecuados  

---

## 9. CI/CD Multicloud

El pipeline debe:

- Construir imágenes  
- Deploy automático a Functions/Lambda/Cloud Run  
- Configurar variables y secrets  
- Testear el router con payloads reales  
- Generar reportes  

---

## 10. Optimización de Costos (FinOps + Multi-Model)

Debe analizar:

- Costo de cada modelo por request  
- Cuánto se ahorra usando el router  
- Costo total por 1k peticiones  
- Estrategias:
  - Overriding thresholds  
  - Reducción de profundidad  
  - Mode switching (p. ej., texto simple → Flash)  
  - Caching de prompts  
  - Fee caps  

Debe entregar:

- **Cost Saving Report**  
- **Routing Efficiency Score**  

---

## 11. Observabilidad y Métricas

Debe registrar:

- Routing Accuracy  
- Requests por modelo  
- Latencia promedio por modelo  
- Cost per request  
- Errores  
- Logs del router  

Herramientas requeridas:

- CloudWatch / X-Ray (AWS)  
- Application Insights (Azure)  
- Cloud Logging (GCP)  

---

## 12. Documentación Final Profesional (20–25 páginas)

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Caso de uso  
- Diseño del router  
- Modelos utilizados  
- Patrones LLM  
- Arquitectura  
- Estrategias de costo  
- Resultados experimentales  
- Testing  
- Diagrama final  
- Lecciones aprendidas  

---

# Tabla de Evaluación por Componentes – Proyecto 5

| #  | Componente del Proyecto                                  | Descripción de Evaluación                                                    | Puntaje |
|----|----------------------------------------------------------|-------------------------------------------------------------------------------|---------|
| 1  | Definición del Caso de Uso                               | Claridad, KPIs, criterios de decisión.                                       | **10** |
| 2  | Selección del Modelo + Infraestructura                   | Justificación, análisis de latencia, costos y trade-offs.                    | **10** |
| 3  | Patrón de Diseño LLM                                     | Diagrama, heurísticas, trade-offs, patrón router.                            | **10** |
| 4  | Docker/Contenerización                                   | Calidad técnica, seguridad, eficiencia.                                      | **8**  |
| 5  | Serverless Orchestration                                 | Configuración correcta de Gateway/Functions/Lambda/Cloud Run.                | **8**  |
| 6  | Arquitectura del Router                                  | Diagrama, claridad, escalabilidad.                                           | **10** |
| 7  | Diseño del Pipeline de Routing                           | Flujo completo, experimentación, heurísticas.                                | **10** |
| 8  | Serving de Modelos                                       | Elección del endpoint, paralelización, gestión de timeouts.                  | **6**  |
| 9  | CI/CD                                                    | Automatización, pipelines, tests automáticos.                                | **6**  |
| 10 | Optimización de Costos                                   | Cálculos, reportes, estrategias FinOps.                                      | **7**  |
| 11 | Observabilidad                                           | Logs, métricas, dashboards.                                                  | **7**  |
| 12 | Documentación Final                                      | Claridad, rigor técnico, calidad profesional.                                | **8**  |

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

- Construcción de routers LLM inteligentes  
- Optimización real de costos por modelo  
- Uso estratégico de modelos pequeños, medianos y premium  
- Creación de arquitecturas serverless avanzadas  
- Diseño de pipelines multi-model  
- Integración de APIs y autoscaling  
- Evaluación de trade-offs de reasoning vs costo  
- Observabilidad y monitoreo avanzado  

