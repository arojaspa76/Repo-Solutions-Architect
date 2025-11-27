# PROYECTO 9 – Distributed RAG Architecture (Sharded Vector Stores)
## "Distributed RAG with Sharding and Multi-Index Strategy"

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Officer  
**Correo:** andres.rojas@triskelss.com  
**Nivel:** Avanzado  
**Modalidad:** Distributed RAG + Vector Sharding + Multi-Index Retrieval + Query Rewriting

---

# Componentes obligatorios del proyecto (12 pasos formales)

Este proyecto enseña a diseñar una **arquitectura RAG distribuida**, con **sharding por dominio**, **multi-index**, **replicación multi-región**, **query rewriting**, y **re-ranking avanzado**.

---

## 1. Definición Avanzada del Caso de Uso

El estudiante debe definir un escenario empresarial real, con múltiples dominios documentales:

- Legal  
- HSE  
- Técnico  
- Operaciones  
- Financiero (opcional)  

Debe definir:

- Volumen por dominio  
- Necesidad de sharding  
- Reglas de negocio  
- Latencia tolerable  
- SLA por dominio  

**KPIs:**

- Retrieval Accuracy por shard  
- Latencia cross-region  
- Reranking Quality Score  
- Shard Selection Accuracy  
- Costo por 1000 queries  

---

## 2. Selección del Modelo + Requerimientos de Infraestructura

Debe seleccionar embeddings:

- Azure OpenAI  
- AWS Titan  
- Vertex AI  
- Open Source: BGE / E5 / Instructor  

Debe seleccionar vector stores distribuidos:

- Pinecone (multi-index)  
- Milvus / Zilliz  
- Qdrant Distributed  
- AlloyDB + pgvector  
- OpenSearch  

Debe justificar:

- Latencia  
- Capacidad de clustering/sharding  
- Replicación  
- Costo mensual aproximado  

---

## 3. Selección y Justificación del Patrón de Diseño LLM

Patrones permitidos:

- **Sharded Retrieval Pattern (obligatorio)**  
- **Multi-Index Retrieval Pattern**  
- Query Rewriting Pattern  
- Reranking Pattern  
- Retrieval Cascade Pattern  
- Domain Router Pattern  

Debe incluir:

- Diagrama del patrón  
- Proceso de selección de shard  
- Proceso de re-escritura  
- Flujo multi-step de retrieval  
- Trade-offs técnicos  

---

## 4. Contenerización con Docker

Debe contenerizar:

- Ingestor documental  
- Chunker  
- Embedding generator  
- Shard router  
- Retrieval API  
- Reranker  

Requisitos:

- Multi-stage  
- Non-root  
- Slim base images  
- Secrets externos  
- Pruebas básicas  

---

## 5. Orquestación (Serverless o Kubernetes)

Opciones aceptadas:

### Serverless  
- AWS Lambda  
- Step Functions  
- Azure Functions  
- Durable Functions  
- Cloud Functions  
- Cloud Run  

### Kubernetes  
- AKS / EKS / GKE  
- HPA + GPU pods para reranking  
- Pod Anti-Affinity  

El estudiante debe justificar la elección.

---

## 6. Arquitectura Completa Distribuida

Debe incluir:

- Múltiples shards por dominio  
- Multi-index retrieval  
- Replicación multi-región  
- Reranking  
- Query rewriting  
- Layer de enrutamiento  
- Observabilidad distribuida  

Debe entregar un diagrama en **Mermaid o PlantUML**.

---

## 7. Diseño del Pipeline de Ingesta + Sharding

Debe diseñar:

### Limpieza  
- Normalización  
- Eliminación de ruido  
- Extracción de metadatos  

### Chunking  
- Semántico  
- Basado en secciones  
- Token-based dinámico  

### Sharding  
- Por dominio (obligatorio)  
- Por semántica (opcional)  

Debe justificar el método.

---

## 8. Generación de Embeddings + Sharded Storage

Debe incluir:

- Generación en batch  
- Optimización de embeddings  
- Asignación a shards correctos  
- Indexación distribuida  
- Replicación multi-región  
- Evaluación:

  - Latencia  
  - Costo  
  - Recall / Precision por shard  

---

## 9. Re-ranking Avanzado + Query Rewriting

Debe implementar:

### Re-ranking  
- Cross-encoders  
- Fusion ranking (opcional)  
- Re-ranking LLM-based  

### Query Rewriting  
- Reformulación multi-step  
- Elaboración incremental  
- Reroll cuando no encuentra resultados  

Debe realizar experimentos comparativos.

---

## 10. Optimización Multi-Región y Alta Disponibilidad

Debe incluir:

- Replicación activa/activa o activa/pasiva  
- Geo-balancing  
- Circuit breakers  
- Semantic caching  
- Fallback automático  

Debe calcular:

- Latencia por región  
- Costo del tráfico cross-region  
- Ahorro por caching  

---

## 11. Observabilidad y Métricas

Debe entregar:

- Logs por shard  
- Evaluación RAGAS por dominio  
- Latencia por etapa  
- Métricas del router  
- Queries por segundo  
- Estadísticas de cache hits  

---

## 12. Documentación Final Profesional

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Caso de uso  
- Arquitectura  
- Shards  
- Embeddings  
- Multi-index  
- Query rewriting  
- Reranking  
- Replicación  
- Costos  
- Pruebas  
- Lecciones aprendidas  

---

# Tabla de Evaluación por Componentes – Proyecto 9

| #  | Componente del Proyecto                   | Evaluación                                                           | Puntaje |
|----|-------------------------------------------|----------------------------------------------------------------------|---------|
| 1  | Caso de Uso                               | Claridad, dominios, KPIs definidos                                   | **10** |
| 2  | Selección de Modelo + Infraestructura     | Justificación de embeddings y vector store                           | **10** |
| 3  | Patrón de Diseño LLM                      | Sharded retrieval + multi-index + rewriting                          | **10** |
| 4  | Docker/Contenerización                    | Calidad técnica, seguridad                                           | **8**  |
| 5  | Orquestación                              | Escalabilidad, disponibilidad, eficiencia                            | **8**  |
| 6  | Arquitectura Distribuida                  | Diagrama completo, coherencia                                        | **10** |
| 7  | ETL + Sharding                            | Diseño, calidad del chunking, criterios de sharding                  | **10** |
| 8  | Embeddings & Vector Storage               | Calidad, optimización, replicación                                   | **6**  |
| 9  | Reranking + Query Rewriting               | Efectividad, experimentación, calidad                                | **6**  |
| 10 | Optimización Multi-Región                 | Failover, caching, balanceo                                          | **7**  |
| 11 | Observabilidad                             | Logs, métricas, trazas                                               | **7**  |
| 12 | Documentación Final                        | Rigor técnico, claridad, nivel profesional                           | **8**  |

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

- Construcción de sistemas RAG distribuidos y escalables  
- Diseño de sharding por dominio  
- Implementación de multi-index y multi-region replication  
- Query rewriting avanzado  
- Reranking robusto  
- Diseño de pipelines ETL para RAG distribuido  
- Optimización de costos y latencias  
- Observabilidad profesional en sistemas de búsqueda semántica  

