# 📖 Guía de Serverless para LLMs en 3 Nubes

## ¿Qué es Serverless?

Serverless **NO significa "sin servidores"**. Significa que **tú no gestionas los servidores**:
- El proveedor cloud asigna recursos automáticamente
- Pagas solo por el tiempo de ejecución real
- Escala desde 0 hasta millones de requests sin configuración
- Sin patching, sin capacity planning, sin mantenimiento de SO

---

## Casos de Uso de Serverless para LLMs

| Caso | Recomendado | Por qué |
|------|-------------|---------|
| API de resumen de texto (sin estado) | ✅ Serverless | Sin estado, latencia variable OK |
| Chatbot interactivo (baja latencia) | ⚠️ Containers K8s | Serverless tiene cold start |
| LLM grande (>13B params) | ❌ No serverless | RAM insuficiente en Consumption |
| Procesamiento por lotes nocturno | ✅ Serverless | Pay-per-use, sin costo en idle |
| RAG pipeline (búsqueda + LLM) | ✅ Serverless (gen2/premium) | Si el modelo es via API externa |
| Fine-tuning / Training | ❌ No serverless | Necesita GPU dedicada |

---

## Comparativa de Servicios

### Azure Functions

| Característica | Consumption | Premium | Container Apps |
|----------------|------------|---------|----------------|
| **RAM máxima** | 1.5 GB | 14 GB | 30+ GB |
| **Timeout** | 5 min | ilimitado | ilimitado |
| **Cold start** | 1-3 seg | ~0 seg | ~0 seg |
| **Scale to zero** | ✅ | Opcional | ✅ |
| **VNet privada** | ❌ | ✅ | ✅ |
| **GPU** | ❌ | ❌ | ❌ (usar AKS) |
| **Precio aprox.** | $0 (2M/mes gratis) | $169+/mes | $0.000024/vCPU-seg |

**Recomendación para LLMs via API (Azure OpenAI):** Azure Functions Premium o Container Apps.

### Google Cloud Functions gen2

| Característica | gen1 | gen2 |
|----------------|------|------|
| **RAM máxima** | 8 GB | 32 GB |
| **CPU máxima** | 2 vCPU | 8 vCPU |
| **Timeout** | 9 min | 60 min |
| **Concurrencia** | 1 req/instancia | Hasta 1000 req/instancia |
| **Precio requests** | $0.0000004/req | Igual |

**Nota importante:** gen2 usa Cloud Run internamente, con mucha más flexibilidad.

**Recomendación:** Cloud Run > Cloud Functions gen2 para LLMs (más control sobre imagen Docker).

### AWS Lambda

| Característica | Valor |
|----------------|-------|
| **RAM máxima** | 10 GB |
| **CPU** | Proporcional a RAM (1 vCPU por 1769 MB) |
| **Timeout** | 15 minutos |
| **Tamaño deployment** | 50 MB (zip) / 10 GB (container image) |
| **Concurrencia** | 1000 instancias (por defecto) |
| **Precio** | $0.0000166667 por GB-segundo |

**Nota:** Para modelos > 10GB de RAM, usar ECS Fargate o SageMaker.

---

## El Ejercicio: Mismo Código para 3 Nubes

### Arquitectura

```
Cliente HTTP
     │
     ▼
┌────────────────────────────────────────┐
│         Función Serverless             │
│                                        │
│  1. Recibir texto via HTTP POST        │
│  2. Construir prompt de resumen        │
│  3. Llamar LLM (Ollama o Cloud LLM)   │
│  4. Retornar JSON con resultado        │
└────────────────────────────────────────┘
     │                │                │
   Azure           Google             AWS
  Function     Cloud Function        Lambda
     │                │                │
  Azure           Vertex AI         Bedrock
  OpenAI          Gemini             Claude
```

### Código Compartido (lógica de negocio idéntica)

```python
def build_summary_prompt(text: str, language: str, max_length: int) -> str:
    lang_str = "en español" if language == "es" else "in English"
    return (
        f"Resume el siguiente texto {lang_str} en máximo {max_length} palabras. "
        f"Solo el resumen, sin introducción:\n\n{text}"
    )

async def call_ollama(prompt: str) -> str:
    # Código IDÉNTICO para Azure, GCP y AWS (en desarrollo local)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "http://localhost:11434/api/chat",
            json={"model": "llama3.2:3b",
                  "messages": [{"role": "user", "content": prompt}],
                  "stream": False}
        )
        return resp.json()["message"]["content"]
```

### Lo que cambia por nube (solo el wrapper)

```python
# Azure: decorador @app.route()
@app.route(route="llm-summarize")
async def llm_summarize(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()
    ...

# GCP: decorador @functions_framework.http
@functions_framework.http
def llm_summarize(request):
    body = request.get_json()
    ...

# AWS: función lambda_handler con event dict
def lambda_handler(event: dict, context) -> dict:
    body = json.loads(event.get("body", "{}"))
    ...
```

---

## Cold Start: El Principal Problema de Serverless para LLMs

### ¿Qué es el Cold Start?

Cuando una función lleva tiempo sin recibir requests, el proveedor "destruye" la instancia. La próxima request debe:
1. Crear una nueva instancia (VM o contenedor)
2. Descargar el código/imagen
3. Inicializar el runtime (Python)
4. Importar librerías (`import torch`, `import transformers` → 5-30 segundos)
5. Cargar el modelo en RAM (si es local)

### Latencias típicas de Cold Start

| Scenario | Cold Start |
|----------|-----------|
| Azure Functions Consumption (Python) | 1-5 seg |
| Azure Functions Premium | ~200ms |
| Google Cloud Functions gen2 | 500ms-2 seg |
| AWS Lambda (Python, 512MB) | 300ms-1 seg |
| AWS Lambda con imagen Docker 1GB+ | 5-20 seg |
| Lambda + carga de modelo Llama 7B | 30-120 seg ❌ |

### Estrategias de Mitigación

1. **Provisioned Concurrency (AWS)** / **Pre-warmed instances (Azure)**: mantener instancias calientes. Costo extra.

2. **Usar API externa de LLM**: si la función llama a Azure OpenAI o Bedrock en vez de cargar el modelo, el cold start es solo el startup del runtime (~1 seg).

3. **Minimum instances = 1**: siempre mantener una instancia caliente. Costo mínimo constante.

4. **Warm-up trigger**: un ping periódico (cada 5 min) mantiene la instancia activa en Consumption.

5. **Container Apps / Cloud Run**: mejor manejo de cold start con imágenes cacheadas.

---

## Precios Reales (Estimación para Demo de Clase)

Para 1000 requests/día al endpoint de resumen:
- Cada request: ~5 segundos de ejecución, 512MB RAM

| Proveedor | Costo/mes | Notas |
|-----------|-----------|-------|
| Azure Functions Consumption | **~$0** | Primeras 400K GB-seg gratis/mes |
| GCP Cloud Functions | **~$0** | Primeras 2M invocaciones gratis/mes |
| AWS Lambda | **~$0.01** | Primeras 1M invocaciones gratis/mes |
| Ollama Local | **$0** | Sin costo de API, solo electricidad |

**Conclusión: para demos y proyectos académicos, el costo es $0 en los 3 proveedores.**
