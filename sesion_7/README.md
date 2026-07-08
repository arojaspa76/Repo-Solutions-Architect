# TechCorp LLM Infrastructure — Caso Práctico Completo

> Chatbot de Soporte IT con Azure OpenAI + AKS + Azure AI Search  
> BSG Institute — Infraestructura Cloud para LLMs | RE-I&D-041

---

## Estructura del proyecto

```
techcorp-llm/
├── rag-orchestrator/           # Capítulos 2, 5, 6 — FastAPI + Docker + AKS
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py             # FastAPI app, lifespan, middlewares
│       ├── models/
│       │   └── schemas.py      # Pydantic models (request/response)
│       ├── routers/
│       │   ├── chat.py         # POST /chat — flujo RAG completo
│       │   ├── health.py       # GET /health — Kubernetes probe
│       │   └── admin.py        # POST /admin/index y /admin/create-index
│       └── services/
│           ├── openai_service.py   # Azure OpenAI: embeddings + completions
│           ├── search_service.py   # Azure AI Search: índice vectorial HNSW
│           └── cosmos_service.py   # Azure Cosmos DB: historial de sesiones
│
├── serverless-functions/       # Capítulo 3 — Azure Functions
│   └── daily_summary/
│       ├── function_app.py     # Timer Trigger + HTTP Trigger
│       ├── requirements.txt
│       └── host.json
│
├── kubernetes/                 # Capítulos 2, 5 — Manifiestos K8s
│   └── rag-deployment.yaml     # Deployment, Service, HPA, KEDA ScaledObject
│
├── github-workflows/           # Capítulo 6 — CI/CD
│   └── deploy.yml              # Build ACR → Rolling update AKS
│
├── k6-tests/                   # Capítulo 5 — Pruebas de carga
│   └── load_test.js            # 1,000 usuarios, SLA p95 < 2s
│
└── scripts/
    ├── provision_azure.sh      # Aprovisionamiento completo (todos los caps)
    └── seed_knowledge_base.py  # Poblar base de conocimiento IT
```

---

## Inicio rápido

### 1. Aprovisionar Azure (una sola vez)

```bash
chmod +x scripts/provision_azure.sh
./scripts/provision_azure.sh
```

### 2. Configurar variables de entorno

```bash
cd rag-orchestrator
cp .env.example .env
# Editar .env con los valores reales de Azure
```

### 3. Ejecutar localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Poblar la base de conocimiento

```bash
RAG_API_URL=http://localhost:8000 python scripts/seed_knowledge_base.py
```

### 5. Probar el chatbot

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cómo configuro la VPN en Windows 11?"}'
```

### 6. Construir y subir imagen Docker (Capítulo 2)

```bash
cd rag-orchestrator
az acr build --registry acrtechcorp --image rag-function:v1.0 .
```

### 7. Desplegar en AKS (Capítulo 2)

```bash
kubectl apply -f kubernetes/rag-deployment.yaml
kubectl get pods -w
```

### 8. Prueba de carga (Capítulo 5)

```bash
k6 run k6-tests/load_test.js \
  -e BASE_URL=http://$(kubectl get svc rag-function-svc -o jsonpath='{.status.loadBalancer.ingress[0].ip}') \
  --out json=results.json
```

---

## Variables de entorno requeridas

| Variable | Descripción |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | URL del recurso Azure OpenAI |
| `AZURE_OPENAI_KEY` | API Key de Azure OpenAI |
| `AZURE_OPENAI_CHAT_MODEL` | Nombre del deployment GPT-4o |
| `AZURE_OPENAI_EMBED_MODEL` | Nombre del deployment text-embedding-3-small |
| `AZURE_SEARCH_ENDPOINT` | URL de Azure AI Search |
| `AZURE_SEARCH_KEY` | Admin Key de Azure AI Search |
| `AZURE_SEARCH_INDEX` | Nombre del índice (default: knowledge-base) |
| `COSMOS_ENDPOINT` | URL de Cosmos DB |
| `COSMOS_KEY` | Primary Key de Cosmos DB |
| `COSMOS_DATABASE` | Nombre de la base de datos |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Para Azure Monitor |

---

## Capítulos y archivos correspondientes

| Capítulo | Archivos |
|----------|----------|
| Cap. 1 — Conceptos e infraestructura | `scripts/provision_azure.sh` (sección cap1) |
| Cap. 2 — Docker y Kubernetes | `rag-orchestrator/Dockerfile`, `kubernetes/rag-deployment.yaml` |
| Cap. 3 — Serverless | `serverless-functions/daily_summary/` |
| Cap. 4 — Optimización de costos | `scripts/provision_azure.sh` (sección cap4), Redis config |
| Cap. 5 — Rendimiento y HA | `kubernetes/rag-deployment.yaml` (HPA + KEDA), `k6-tests/` |
| Cap. 6 — Proyecto integrador | `app/` (completo), `github-workflows/deploy.yml` |

---

## Limpieza de recursos

```bash
az group delete --name rg-techcorp-llm --yes --no-wait
```

> ⚠️ Ejecutar al terminar cada sesión para preservar el crédito de Azure for Students.

---

*BSG Institute — Sistema de Gestión de la Calidad RE-I&D-041 — Revisión 01 — 2024*
