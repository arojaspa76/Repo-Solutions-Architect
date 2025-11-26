# PROYECTO 12 – LLM Data Engineering Pipeline (Chunking + ETL + Indexing)
## "ETL + Chunking + Embeddings Pipeline for Large Document Repositories"

**Curso:** Diseño de Infraestructura Escalable BSG Institute  
**Profesor:** Msc, PgP, Andrés Felipe Rojas Parra  
**Cargo:** Chief Artificial Intelligence Officer  
**Correo:** andres.rojas@triskelss.com  
**Nivel:** Avanzado / Maestría  
**Modalidad:** LLM Data Engineering + Pipelines + Indexing + Embeddings

---

# Componentes obligatorios del proyecto (12 pasos formales)

Este proyecto enseña a diseñar un **pipeline completo de ingeniería de datos para LLMs**, desde la ingesta y normalización documental, hasta la generación de embeddings, indexación cloud y versionamiento.

---

## 1. Definición Avanzada del Caso de Uso  
El estudiante debe definir un escenario real de ingestión documental:

- Repositorios grandes de PDFs, Word, HTML  
- Artículos científicos, reportes financieros, manuales, pólizas, expedientes  
- Volumen mínimo: **300–1000 documentos** (pueden ser simulados)

Debe definir:

- Tipos de documentos  
- Reglas de limpieza y normalización  
- Estructura final deseada  
- Objetivo del pipeline (RAG, búsqueda semántica, auditoría documental)

**KPIs:**
- Tiempo total del pipeline  
- Calidad del chunking (medida por RAGAS o heurísticas)  
- Cobertura de metadatos  
- Tasa de errores de parsing  
- Costo total del pipeline  

---

## 2. Selección del Modelo + Requerimientos de Infraestructura  
Debe elegir:

### Modelos de embeddings:
- Azure OpenAI embeddings  
- AWS Titan embeddings  
- Google Vertex embeddings  
- Open-source: BGE, InstructorXL, E5 Large, etc.

### Infraestructura:
- AWS Glue, Lambda, S3  
- Azure Data Factory + Functions + Blob Storage  
- GCP Dataflow + Cloud Functions + GCS  
- Opción self-hosted en contenedores

Debe justificar:

- Velocidad  
- Costo por 1k embeddings  
- Calidad semántica  
- Adecuación al caso de uso  

---

## 3. Selección y Justificación del Patrón de Diseño LLM  
Debe seleccionar patrones centrados en pipelines y chunking:

- **Semantic Chunking Pattern** (obligatorio)  
- Embedding Optimization Pattern  
- Metadata Enrichment Pattern  
- Small-to-Big Reranker Pattern (para evaluar chunks)  
- Auto-RAG Optimizer Pattern  

Debe justificar:

- Por qué ese patrón es óptimo  
- Impacto en latencia, calidad y costo  
- Diagrama del patrón dentro del pipeline  

---

## 4. Contenerización con Docker  
El estudiante debe contenerizar los módulos:

- ETL extractor  
- Chunker  
- Embedding generator  
- Metadata extractor  
- Indexer service  

Requisitos:

- Multi-stage  
- Python/Node/Go lightweight  
- Non-root  
- Secrets externos  
- Pruebas básicas integradas  

---

## 5. Orquestación (Serverless + Batch + Containers)  
Opciones aceptadas:

### AWS  
- Glue Jobs  
- Lambda  
- Step Functions  
- ECS Fargate  

### Azure  
- Data Factory  
- Functions  
- Container Apps  

### GCP  
- Dataflow  
- Cloud Functions  
- Cloud Run  

El pipeline debe ser **reintetable y tolerante a fallos**.

---

## 6. Arquitectura Completa del Pipeline  
El diagrama debe incluir:

- Ingesta → Limpieza → Normalización  
- Extracción de metadatos  
- Chunking semántico  
- Generación de embeddings  
- Almacenamiento cloud  
- Indexación (OpenSearch, AlloyDB, BigQuery, Aurora pgvector, Azure AI Search)  
- Registro de versiones  

Debe entregarse en Mermaid o PlantUML.

---

## 7. Diseño del Pipeline de ETL + Chunking  
Debe diseñarse:

### Limpieza:
- Eliminación de tablas, headers repetidos, footers  
- Normalización UTF-8  
- Sanitización de HTML  

### Chunking:
- Basado en semántica  
- Basado en tokens (tamaño dinámico)  
- Basado en estructura (títulos, secciones)  

### Evaluación:
- Distribución de tamaños  
- Calidad semántica  
- Cohesión entre chunks  

---

## 8. Generación y Almacenamiento de Embeddings  
Debe incluir:

- Elección del modelo  
- Estrategias para embeddings masivos  
- Batch optimization  
- Compresión o reducción dimensional (opcional)  
- Almacenamiento en:
  - S3 / Blob / GCS  
  - pgvector / AlloyDB  
  - Azure AI Search  
  - OpenSearch  
  - BigQuery  

Debe evaluar costo por 1k embeddings.

---

## 9. Indexación Cloud  
El estudiante debe elegir una opción:

- OpenSearch (AWS / self-hosted)  
- Aurora PostgreSQL + pgvector  
- AlloyDB + pgvector  
- Azure AI Search  
- Google BigQuery Vector Search  

Debe justificar:

- Latencia  
- Costo  
- Capacidad para queries híbridas  
- Integración con downstream RAG  

---

## 10. Versionamiento de Índices  
Debe implementar:

- Versiones incrementales  
- Control de cambios  
- Registro de:
  - número de documentos  
  - número de chunks  
  - número de embeddings  
  - fecha de indexación  
  - hash o firma del dataset  

Debe demostrar qué pasa cuando:

- Se agregan nuevos documentos  
- Se re-procesan documentos  
- Se eliminan documentos  

---

## 11. Observabilidad y Métricas  
Debe incluir:

- Logs del pipeline  
- Tiempos de procesamiento por etapa  
- Tasa de fallos (parse errors, chunks vacíos)  
- Costo total del pipeline (estimated)  
- Métricas del indexador  

Herramientas:

- CloudWatch / X-Ray  
- Azure Monitor  
- GCP Cloud Logging  

---

## 12. Documentación Final Profesional (20–25 páginas)  

### Formato de la documentación:
- Documento del proyecto - Guia de Usuario
- Documento del proyecto - Guia de Administrador
- Caso de uso  
- Arquitectura  
- Diseño ETL  
- Patrones LLM  
- Resultados de chunking  
- Comparación embeddings  
- Benchmarking de indexación  
- Versionamiento  
- Lecciones aprendidas  

---

# Tabla de Evaluación por Componentes – Proyecto 12

| #  | Componente del Proyecto                                  | Descripción de Evaluación                                       | Puntaje |
|----|----------------------------------------------------------|------------------------------------------------------------------|---------|
| 1  | Definición del Caso de Uso                               | Claridad, KPIs, volumen documental, realismo.                   | **10** |
| 2  | Selección del Modelo + Infraestructura                   | Justificación técnica, costos, calidad del embedding.           | **10** |
| 3  | Patrón de Diseño LLM                                     | Diagrama, justificación, trade-offs, impacto en el pipeline.    | **10** |
| 4  | Docker/Contenerización                                   | Calidad de imágenes, seguridad, eficiencia.                     | **8**  |
| 5  | Orquestación del Pipeline                                | Glue/Data Factory/Dataflow correcto, reintentos, tolerancia.    | **8**  |
| 6  | Arquitectura del Pipeline                                | Diagrama profesional, coherencia y completitud.                 | **10** |
| 7  | Diseño del ETL + Chunking                                | Calidad del chunking, limpieza, normalización, evaluación.      | **10** |
| 8  | Embeddings                                                | Batch optimization, calidad, costos, almacenamiento.            | **6**  |
| 9  | Indexación Cloud                                         | Elección adecuada, justificación técnica, rendimiento.           | **6**  |
| 10 | Versionamiento                                           | Estrategia clara, integridad, organización.                     | **7**  |
| 11 | Observabilidad                                           | Logs, métricas, Tiempos, errores, reportes.                     | **7**  |
| 12 | Documentación Final                                      | Claridad, detalle técnico, completitud.                         | **8**  |

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

- Construcción de pipelines ETL para LLMs  
- Diseño profesional de chunking semántico  
- Generación y optimización de embeddings  
- Indexación cloud con bases vectoriales  
- Versionamiento de índices para auditoría y control  
- Observabilidad completa de pipelines  
- Buenas prácticas de ingeniería de datos aplicada a LLMs  
- Integración con infra cloud (AWS / Azure / GCP)

