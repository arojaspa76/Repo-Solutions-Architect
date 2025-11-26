# PROYECTO 1 – RAG Serverless Multinube (Azure + AWS o Azure + GCP)

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Office  
**Correo:** andres.rojas@triskelss.com  
**Nivel:** Avanzado  
**Modalidad:** Multicloud + Serverless + LLM + RAG  

---

# Componentes obligatorios del proyecto (con patrón de diseño incluido)

A continuación se presenta el proyecto completo siguiendo los pasos formales para su uso en syllabus, rúbrica y entregables.

---

# Diccionario:
- RAGAS: Herramienta para Evaluar la Calidad de los Sistemas RAG

---

## 1. Definición Avanzada del Caso de Uso del LLM

### Objetivo:
Construir una plataforma RAG multinube donde:

- La web app vive en **Azure App Service** o **Azure Static Web Apps**  
- Los documentos se almacenan en **AWS S3**  
- El vector store vive en **GCP (AlloyDB pgvector o Vertex AI Search)**  
- La inferencia del LLM ocurre en **Azure OpenAI** o **AWS Bedrock**  
- La orquestación es **100% serverless** usando **Azure Functions + AWS Lambda o Cloud Run**

### KPI a medir:
- Latencia entre clouds (Azure → AWS → GCP → Azure)  
- Tokens/s en inferencia  
- Costo por 1k tokens  
- Tasa de aciertos del RAG (RAGAS)  
- Cloud egress cost optimization  

---

## 2. Selección del Modelo + Requerimientos de Infraestructura

El estudiante debe elegir una de las rutas:

### Ruta 1 – Azure OpenAI  
- GPT-4o, GPT-4 Turbo, GPT-4o Mini  
- Endpoints privados  
- Cálculo de latencia cross-cloud  

### Ruta 2 – AWS Bedrock  
- Anthropic Claude 3.5  
- Llama-3 70B  
- Mistral Large  

### Justificación requerida:
- Elección del modelo  
- Tokens promedio por consulta  
- Latencia vs costo  
- Picos esperados de demanda  
- Requerimientos del vector DB  

---

## 3. Selección y Justificación del Patrón de Diseño LLM

El estudiante debe seleccionar **al menos un patrón**:

- RAG Básico  
- RAG + Reranking  
- Model Routing / Router Pattern  
- Mixture of Agents  
- Guardrail Pattern  
- Self-Query Retriever  
- Long-Context Pattern  
- Chain-of-Thought enforced  
- LLM-as-a-Judge  
- Hybrid RAG (Vector + KG)  

### Debe incluir:
- Justificación técnica  
- Trade-offs  
- Diagrama del patrón dentro del pipeline  
- Impacto en latencia, costo, calidad y seguridad  

---

## 4. Contenerización con Docker (solo para microservicios internos)

Aunque es serverless, se exige Docker para:

- Microservicio de ingestión documental  
- Microservicio de chunking  
- API de testing o validación  
- Worker opcional para evaluación RAG  

### Requisitos del Dockerfile:
- Multi-stage build  
- Imágenes mínimas  
- Variables en Secrets  
- Sin usuario root  
- Escaneo con Trivy  

---

## 5. Orquestación — Serverless Multicloud

**No se usa Kubernetes en este proyecto, sino serverless multinube.**

### **Arquitectura mínima requerida:**

### Azure:
- Azure Functions
- Azure App Service o Static Web Apps
- Azure API Management
- Private Endpoints

### AWS:
- AWS Lambda
- AWS S3
- IAM cross-account roles
- API Gateway

### GCP:
- Cloud Run
- AlloyDB pgvector o Vertex AI Search
- Service Accounts

---

## 6. Arquitectura Completa Multicloud (Diagrama Obligatorio)

Obligatorio un diagrama de arquitectura multinube que incluya: luir elementos de:

### Microsoft Azure:
- Web App (App Service / Static Web Apps)
- Azure Functions como Orquestador principal
- API Management
- Azure OpenAI (opcional)
- Private DNS + Private Endpoints

### AWS
- S3 (documentos fuente)
- AWS Lambda opcional para ingesta
- Access control basado en IAM Policies
- IAM roles cross-account
- API Gateway si aplica

### GCP
- AlloyDB pgvector o Vertex AI Search
- Cloud Run (para microservicio de retrieval)
- Cloud Router (si hay VPC interconnect)
- Service Accounts  

### Networking
- Azure → AWS: conexión mediante API Gateway
- Azure → GCP: llamadas directas o Private Services Connect
- Manejo de egress optimization

---

## 7. Diseño de RAG Distribuido

### Pipeline completo:
1. Ingesta → AWS Lambda  
2. Limpieza → Azure Function  
3. Chunking → Cloud Run  
4. Embeddings → Azure OpenAI / Bedrock  
5. Vector store → AlloyDB / Vertex AI Search  
6. Retrieval → Cloud Run  
7. Reranking (opcional) → Azure Function  
8. LLM inference → Azure OpenAI / Bedrock  

### Experimentos obligatorios:
- Chunk size  
- Overlap  
- Comparación de modelos de embedding  
- RAGAS evaluation

---

## 8. Infraestructura de Serving de LLM (Managed)

### Opción A (Azure): 
- Azure OpenAI: GPT-4 Turbo / GPT-4o
- Azure private networking (sin internet público)
- Tokens/s optimizados

### Opción B (AWS Bedrock):
- Bedrock (Claude 3.5 / Llama 3)
- IAM fine-grained access

### Evaluar:
- Latencia  
- Tokens/s  
- Privacidad  
- Costos  

---

## 9. CI/CD Multinube

### Obligatorio usar:
- GitHub Actions

### Debe incluir:
- Build y push de imágenes Docker  
- Deploy automatizado a:
  - Azure Functions  
  - AWS Lambda  
  - GCP Cloud Run  

### IaC:
- Terraform (recomendado para multi-cloud)
- Bicep (solo para Azure)
- CloudFormation (solo para AWS)

---

## 10. Optimización de Costos (FinOps Multicloud)

### Deben calcular:
- Costo mensual  
- Costo por request  
- Costo por 1k tokens  
- Impacto del tráfico entre clouds  
- Comparar un flujo con y sin multilocation

### Estrategias de reduccion de egresos cuando:
- Caching   
- Minimizar salidas de GCP  
- Routing inteligente  
- Llamadas directas en lugar de mover documentos  
- Compresión de embeddings

---

## 11. Observabilidad y Métricas (Cross-Cloud)

**Debe incluir:**

### Azure:
- App Insights  
- Monitor  
- Logs de Functions  

### AWS:
- CloudWatch Metrics
- CloudTrail
- Logs de Lambda

### GCP:
- Cloud Logging  
- Cloud Monitoring  

### Pruebas obligatorias:
- Latencia total del flujo 
- Latencia por cloud  
- RAGAS ≥ 0.7 para aprobación 
- Trazabilidad entera (Azure → AWS → GCP → Azure)  

---

## 12. Documentación Final

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Arquitectura  
- Dockerfiles  
- Configuración Serverless  
- Seguridad  
- Pruebas  
- Costos  
- Flujo multinube  
- Diagrama Mermaid o PlantUML  

---

# Aprendizajes esperados

- Integración multinube avanzada  
- Diseño de RAG distribuido  
- Arquitectura serverless escalable  
- Optimización de costos multi-cloud  
- Patrones de diseño LLM  
- CI/CD operativo entre tres clouds  
- Observabilidad distribuida  
- Diseño al nivel de un Arquitecto de Soluciones Cloud + AI

--- 

# Tabla de Evaluación por Componentes – Proyecto 1

| #  | Componente del Proyecto                        | Descripción de Evaluación                                                         | Puntaje |
|----|------------------------------------------------|------------------------------------------------------------------------------------|---------|
| 1  | Definición del Caso de Uso (LLM)               | Claridad, profundidad técnica, KPIs definidos, relación con un problema real.      | **10**  |
| 2  | Selección del Modelo + Infraestructura         | Justificación del modelo, costos, latencia, VRAM, análisis de trade-offs.          | **10**  |
| 3  | Patrón de Diseño LLM                           | Selección adecuada, diagrama, justificación, trade-offs, integración al pipeline.  | **10**  |
| 4  | Contenerización (Docker)                       | Multi-stage, seguridad (no root), eficiencia, uso de Trivy, buenas prácticas.      | **8**   |
| 5  | Orquestación Serverless Multicloud             | Uso correcto de Azure Functions, Lambda y Cloud Run; integración entre clouds.     | **8**   |
| 6  | Arquitectura Multicloud (Diagrama)             | Diagrama profesional (Mermaid/PlantUML), networking, seguridad, coherencia.        | **10**  |
| 7  | Diseño del Pipeline RAG Distribuido            | Funcionalidad del flujo RAG, chunking, embeddings, retrieval, reranking.           | **10**  |
| 8  | Serving del LLM (Azure OpenAI / Bedrock)       | Elección y configuración del modelo, endpoints privados, pruebas de calidad.       | **6**   |
| 9  | CI/CD Multinube                                | Pipelines funcionales, despliegue automatizado, integración cloud-to-cloud.        | **6**   |
| 10 | Optimización de Costos (FinOps)                | Cálculos, análisis, estrategias para reducir costos y minimizar egress.            | **7**   |
| 11 | Observabilidad y Métricas Cross-Cloud          | Logs, métricas, trazabilidad, latencia por cloud, RAGAS ≥ 0.7.                     | **7**   |
| 12 | Documentación Final Profesional                | Documento 20–25 páginas, decisiones técnicas, riesgos, diagramas, pruebas.         | **8**   |

**Total: 100 puntos**

---

# Resumen de Ponderación

| Categoría                    | Peso  |
|------------------------------|--------|
| **Arquitectura & Diseño**    | **45%** |
| **Implementación Técnica**   | **40%** |
| **Documentación & Análisis** | **15%** |

---

# ¡Éxitos con el desarrollo del proyecto!