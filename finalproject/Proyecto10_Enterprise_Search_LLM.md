# PROYECTO 10 – LLM Pipeline para Enterprise Search
## "Enterprise LLM Search Engine with Semantic Indexing"

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Officer  
**Correo:** andres.rojas@triskelss.com
**Nivel:** Avanzado  
**Modalidad:** Enterprise Search + Semantic Indexing + Multi-Modal RAG + Re-ranking

---

# Componentes obligatorios del proyecto (12 pasos formales)

Este proyecto enseña a construir un **motor de búsqueda empresarial** basado en LLMs, con indexación semántica distribuida, RAG multi-modal, caching de embeddings y document scoring avanzado.

---

## 1. Definición Avanzada del Caso de Uso

El estudiante debe definir un caso empresarial:

- Búsqueda interna corporativa  
- Búsqueda en bases de conocimiento  
- Búsqueda de manuales técnicos  
- Multi-modal: texto + imágenes + tablas + PDFs complejos  

Debe incluir:

- Tipos de datos  
- Volumen esperado  
- Latencia esperada  
- Nivel de precisión requerido  
- Reglas de relevancia  

**KPIs:**
- Recall@K / Precision@K  
- MRR (Mean Reciprocal Rank)  
- Latencia de búsqueda  
- Document Scoring Accuracy  
- Costo por 1k búsquedas  

---

## 2. Selección del Modelo + Requerimientos de Infraestructura

Debe elegir:

### Embeddings:
- Azure OpenAI (text-embedding-3-large)  
- AWS Titan  
- Google Vertex AI embeddings  
- Open-source BGE / E5 / Instructor / GTE  

### LLM para generación:
- GPT-4o  
- Claude 3.5 Sonnet / Opus  
- Gemini 1.5 Pro/Flash  
- Llama 3 / Mistral (self-hosted)

Debe justificar:

- Latencia  
- Calidad  
- Costo  
- Capacidades multi-modales  
- Trade-offs entre precisión y eficiencia  

---

## 3. Selección y Justificación del Patrón de Diseño LLM

Debe elegir:

### Patrón obligatorio:
- **Semantic Indexing Pattern**

### Opcionales:
- Multi-Modal RAG Pattern  
- Metadata-Oriented Retrieval Pattern  
- Hybrid Search Pattern  
- Reranking Pattern  
- Query Rewriting Pattern  

Debe incluir:

- Diagrama del patrón  
- Proceso de scoring  
- Cómo se combina con multi-modal retrieval  
- Trade-offs  

---

## 4. Contenerización con Docker

Debe contenerizar:

- ETL extractor  
- Multi-modal extractor (OCR + image encoder)  
- Embedding generator  
- Indexer  
- Search API  
- Reranker service  

Requisitos:

- Multi-stage  
- Slim images  
- Non-root  
- Secrets externos  
- Pruebas básicas  

---

## 5. Orquestación (Serverless o Kubernetes)

Opciones:

### AWS:
- Lambda  
- Step Functions  
- ECS Fargate  
- OpenSearch  

### Azure:
- Functions  
- Data Factory  
- Azure AI Search  

### GCP:
- Cloud Functions  
- Cloud Run  
- BigQuery Vector Search  

Debe justificar:

- Escalabilidad  
- Costos  
- Latencia  
- Requerimientos multi-modales  

---

## 6. Arquitectura Completa del Enterprise Search Engine

Debe incluir:

- ETL → limpieza + normalización  
- Multi-modal processing (imágenes + texto)  
- Embeddings + caching  
- Indexación semántica distribuida  
- Retrieval híbrido (opcional)  
- Document scoring  
- Re-ranking avanzado  
- LLM answer generation  

Debe incluir:

- Diagrama en Mermaid o PlantUML  
- Flujo detallado end-to-end  

---

## 7. Pipeline de Ingesta y Preprocesamiento

Debe incluir:

### Limpieza:
- Remover ruido  
- Normalizar texto  
- Estándares UTF-8  
- OCR si aplica  

### Multi-modal ingestion:
- Vision embeddings  
- OCR embeddings  
- Tablas → estructuración  

### Chunking:
- Semántico  
- Multi-modal chunking (texto + imagen asociada)

---

## 8. Embeddings + Caching

Debe incluir:

- Generación de embeddings masivos  
- Estrategias de batch  
- Caching:
  - Cache de embeddings por documento  
  - Cache de consultas (semantic query cache)  

Debe incluir:

- Estrategia de invalidación  
- Evaluación de costos  

---

## 9. Indexación Semántica Distribuida

Debe elegir:

- Azure Cognitive Search  
- OpenSearch  
- Pinecone  
- Qdrant  
- AlloyDB + pgvector  
- BigQuery Vector Search  

Debe incluir:

- Bulk indexing  
- Multi-period indexing  
- Index sharding  
- Metadata indexing  
- Multi-modal vectors (image/text fusion)

---

## 10. Document Scoring + Re-ranking Avanzado

Debe incorporar:

### Scoring:
- TF-IDF (baseline)  
- BM25 (baseline)  
- Semantic score  
- Hybrid score  

### Re-ranking:
- Cross-encoder  
- LLM Re-ranker  
- Fusion ranking (RRF)

Debe incluir experimentos comparativos.

---

## 11. Observabilidad + Search Analytics

Debe incorporar:

- Métricas de uso de índices  
- Latencia por etapa  
- Evaluación por dominio  
- Logs de búsqueda  
- Heatmaps de queries  
- RAGAS (si aplica)

---

## 12. Documentación Final Profesional

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Caso de uso  
- Arquitectura  
- Patrones LLM  
- Pipeline  
- Multi-modal ingestion  
- Embeddings  
- Caching  
- Indexación  
- Re-ranking  
- Evaluación experimental  
- Lecciones aprendidas  

---

# Tabla de Evaluación por Componentes – Proyecto 10

| #  | Componente del Proyecto                       | Evaluación                                                   | Puntaje |
|----|-----------------------------------------------|--------------------------------------------------------------|---------|
| 1  | Caso de Uso                                   | Claridad, KPIs, precisión del escenario                      | **10** |
| 2  | Selección de Modelo + Infraestructura         | Embeddings, LLMs, justificación técnica                      | **10** |
| 3  | Patrón de Diseño LLM                          | Semantic indexing + multi-modal + re-ranking                 | **10** |
| 4  | Docker/Contenerización                        | Imágenes limpias y seguras                                   | **8**  |
| 5  | Orquestación                                  | Serverless/K8s correcto, escalabilidad                       | **8**  |
| 6  | Arquitectura                                   | Diagrama completo y coherente                                | **10** |
| 7  | Pipeline de Ingesta                            | Limpieza, multi-modal ingestion, chunking                    | **10** |
| 8  | Embeddings + Caching                           | Batch, cache, optimización                                   | **6**  |
| 9  | Indexación                                     | Técnica, escalabilidad, elección adecuada                     | **6**  |
| 10 | Document Scoring + Re-ranking                  | Calidad del re-ranking y experimentos                         | **7**  |
| 11 | Observabilidad                                 | Logs, métricas, analytics                                     | **7**  |
| 12 | Documentación Final                            | Claridad, rigor técnico                                       | **8**  |

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

- Diseño de motores de búsqueda empresariales  
- Implementación de **multi-modal RAG**  
- Construcción de pipelines ETL para búsqueda  
- Generación y caching de embeddings  
- Indexación semántica distribuida  
- Hybrid retrieval y re-ranking profesional  
- Evaluación completa de un motor de búsqueda tipo enterprise  
- Arquitectura escalable y observable  

