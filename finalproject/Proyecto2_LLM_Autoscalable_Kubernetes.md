# PROYECTO 2 – LLM Autoscalable sobre Kubernetes (AKS/EKS/GKE)

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Office  
**Correo:** andres.rojas@triskelss.com  
**Nivel:** Avanzado  
**Modalidad:** Kubernetes + GPU Autoscaling + LLM Serving + DevOps

---

# Componentes obligatorios del proyecto (incluyendo patrones de diseño LLM)

A continuación se presenta el Proyecto 2 completo siguiendo los **12 pasos formales**, listo para syllabus, rúbrica y entregables finales.

---

## 1. Definición Avanzada del Caso de Uso

El estudiante debe:

- Implementar una API LLM usando **modelos open-source**:  
  - Llama 3  
  - Gemma  
  - Mistral  
  - Qwen  
- Servir el modelo en **Kubernetes** con GPU autoscaling.
- Garantizar que la API soporte carga variable mediante:
  - Horizontal Pod Autoscaler (HPA)
  - Vertical Pod Autoscaler (VPA)
  - NVIDIA GPU Operator
  - Pod Anti-Affinity
  - Canary Deployments

### KPI obligatorios:
- Tokens/s servidos por pod
- Latencia P50, P90, P99
- GPU Utilization
- Throughput (req/s)
- Costo estimado por hora (GPU nodes)

---

## 2. Selección del Modelo + Requerimientos de Infraestructura

El estudiante debe elegir un modelo:

- **Llama 3 (small, medium, large)**
- **Mistral 7B / 8x22B MoE**
- **Gemma 2B / 7B**
- **Qwen 2.5**

Debe justificar:

- Cuánta VRAM requiere
- Quantization (FP16, INT8, AWQ, GPTQ)
- Throughput esperado
- Parámetros del servidor:
  - vLLM  
  - Text Generation Inference (TGI)  
  - SGLang / Ollama (opcional)

Debe seleccionar una cloud:

- **AKS** (Azure)
- **EKS** (AWS)
- **GKE** (GCP)

---

## 3. Selección y Justificación del Patrón de Diseño LLM

El estudiante debe seleccionar **uno o varios** patrones:

- **Inference Router Pattern** (ruta modelos small → large)
- **Speculative Decoding Pattern**
- **Guardrail Pattern (Shielding)**  
- **Efficient Context Handling Pattern**
- **Mixture-of-Experts Serving Pattern**
- **Batching Pattern (vLLM + continuous batching)**

Debe entregar:

- Diagrama del patrón
- Trade-offs
- Cómo optimiza latencia, costos o throughput
- Implicaciones para Kubernetes autoscaling

---

## 4. Contenerización con Docker

El estudiante debe crear una imagen para:

- El servidor LLM (vLLM/TGI/SGLang)
- API Gateway (FastAPI/Node/Go)

Requisitos:

- Multi-stage build
- Imagen slim
- Non-root user
- GPU-enabled base image
- Variables en Secrets
- Análisis de vulnerabilidades (Trivy)

---

## 5. Orquestación con Kubernetes (AKS/EKS/GKE)

El proyecto debe incluir:

- Deployments
- GPU-enabled Pods
- NodeSelector/GPU labels
- Pod Anti-Affinity
- ConfigMaps + Secrets
- Liveness/Readiness Probes
- Ingress Controller (NGINX/Traefik)

---

## 6. Arquitectura Completa en Kubernetes

Debe incluir:

- GPU Node Pool
- NVIDIA GPU Operator
- HPA + VPA
- Metrics Server
- Ingress Controller
- Service Mesh (opcional: Istio/Linkerd)
- API Gateway interno/externo
- Vector DB opcional para RAG

Debe entregarse en **Mermaid o PlantUML**.

---

## 7. Diseño del Pipeline de Serving

El pipeline mínimo es:

1. Request → Ingress  
2. Ingress → LLM API Gateway  
3. Gateway → vLLM/TGI Pod  
4. Continuous Batching  
5. GPU Inference  
6. Result → Client  

Opcional: RAG con vector DB (Redis/Milvus/pgvector).

Experimentos obligatorios:

- Batch size
- Max model concurrency
- GPU memory fragmentation
- Speculative decoding (si aplica)

---

## 8. Infraestructura de Serving con GPU

Debe incluir:

- Autoscaling GPU nodes (Cluster Autoscaler)
- GPU metrics con **DCGM**
- Configuración de nodos:
  - A10G
  - L4
  - L40S
  - T4 (opcional académico)

Evaluar:

- GPU utilization
- Power consumption (si aplica)
- Costo por throughput

---

## 9. CI/CD Completo

Pipeline debe:

- Construir el Dockerfile
- Push al registry (ECR/ACR/GAR)
- Aplicar Helm chart
- Desplegar canary con Helm o Argo Rollouts
- Validar health checks
- Integrar tests de carga (Locust/K6)

---

## 10. Optimización de Costos

Debe incluir:

- Cálculo del costo del nodo GPU por hora
- Impacto del autoscaling
- Comparación entre:
  - Modelo pequeño vs grande
  - Quantized vs full precision
  - Batch size pequeño vs grande
- Estrategias:
  - Spot nodes
  - Pre-warmed pods
  - Aggressive batching
  - Utilizar modelos pequeños para requests simples

---

## 11. Observabilidad y Métricas

Debe incluir:

### Prometheus
- GPU metrics (via DCGM)
- CPU/memory
- Pod restart count
- Latencia de la API

### Grafana dashboards:
- Latencia P50/P90/P99
- GPU Utilization
- Tokens/s
- Requests/s
- Errors/s (rate)

### Alertas:
- GPU throttling
- Latencia > 800 ms
- Reinicios repetidos

---

## 12. Documentación Final (20–25 páginas)

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Arquitectura
- Patrones LLM
- Helm chart
- Dockerfiles
- YAMLs
- Resultados de pruebas
- Estrategias de autoscaling
- Cálculo de costos
- Problemas encontrados + mitigaciones
- Diagramas formales

---

# Tabla de Evaluación por Componentes – Proyecto 2

| #  | Componente del Proyecto                        | Descripción de Evaluación                                                         | Puntaje |
|----|------------------------------------------------|------------------------------------------------------------------------------------|---------|
| 1  | Definición del Caso de Uso                     | Claridad, profundidad técnica, KPIs definidos.                                     | **10** |
| 2  | Selección del Modelo + Infraestructura         | Modelo, VRAM, costos, latencia, justificación técnica.                             | **10** |
| 3  | Patrón de Diseño LLM                           | Patrón seleccionado, trade-offs, diagrama, claridad conceptual.                     | **10** |
| 4  | Docker/Contenerización                         | Optimización, seguridad, multi-stage, GPU compatibility.                            | **8**  |
| 5  | Orquestación Kubernetes                        | Deployments, Probes, Ingress, Secrets, NodeSelector, GPU Operator.                  | **8**  |
| 6  | Arquitectura en Kubernetes                     | Diagrama profesional y coherente.                                                  | **10** |
| 7  | Pipeline de Serving                            | Batching, inferencia, Gateway, coherencia del flujo.                                | **10** |
| 8  | GPU Serving                                    | GPU autoscaling, configuración, métricas, Nvidia Operator.                          | **6**  |
| 9  | CI/CD                                          | Pipeline funcional, deploy automático, tests.                                       | **6**  |
| 10 | Optimización de Costos                         | Análisis, cálculos, estrategias FinOps.                                             | **7**  |
| 11 | Observabilidad                                 | Dashboards, alertas, métricas clave.                                                | **7**  |
| 12 | Documentación Final                            | Claridad, estructura profesional, 20–25 páginas.                                    | **8**  |

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

- LLM serving en contenedores  
- Autoscaling GPU/CPU  
- Observabilidad profesional  
- Canary deployments  
- Optimización de latencia y costos  
- Kubernetes avanzado con GPU  
- Patrones modernos de inferencia  

