# 🤖 Sesión 7: Autoescalado + Pruebas de Carga de Agentes LLM

**BSG Institute — Diseño de Infraestructura Escalable para LLMs**  
**Capítulo 5** | Duración: 3 horas

---

## 📋 Contenido de la Sesión

| Tema | Subtemas |
|------|----------|
| **5.1 Técnicas de mejora de rendimiento** | Balanceo de carga, HPA, VPA, KEDA en K8s local y 3 nubes |
| **5.2 Agente LLM con FastAPI** | Agente ReAct con herramientas, circuit breaker, cache Redis |
| **5.3 Pruebas de carga** | k6 smoke/load/stress, Locust, análisis P50/P95/P99 en Azure/GCP/AWS |

---

## 🗂️ Estructura del Repositorio

```
session7-autoscaling-load-testing/
│
├── app/                          # FastAPI Gateway (punto de entrada)
│   ├── main.py                   # App con métricas Prometheus
│   ├── api/routes.py             # Endpoints /agent/run, /health, /metrics
│   ├── models/schemas.py         # Pydantic models
│   └── utils/
│       ├── ollama_client.py      # Cliente Ollama con circuit breaker
│       └── cache.py              # Cache Redis + memoria
│
├── agents/                       # ← NOVEDAD Sesión 7: Agente LLM
│   ├── llm_agent/
│   │   ├── agent.py              # Agente ReAct con herramientas
│   │   └── prompts.py            # Prompts del sistema + few-shot examples
│   └── tools/
│       ├── calculator.py         # Herramienta: calculadora (eval seguro AST)
│       ├── weather.py            # Herramienta: clima (mock 20+ ciudades)
│       └── search.py             # Herramienta: búsqueda (knowledge base del curso)
│
├── docker/
│   └── Dockerfile                # Multi-stage build (builder + runtime)
│
├── kubernetes/                   # Autoescalado K8s
│   ├── local/
│   │   ├── deployment.yaml       # Deployment + Services (Minikube)
│   │   └── hpa.yaml              # HPA CPU 60% / RAM 75%
│   ├── azure/
│   │   ├── cluster-setup.sh      # AKS + KEDA setup completo
│   │   ├── hpa-azure.yaml        # HPA para AKS (maxReplicas 15)
│   │   └── keda-scaler.yaml      # KEDA ScaledObject HTTP + Prometheus
│   ├── gcp/
│   │   ├── cluster-setup.sh      # GKE Autopilot setup
│   │   └── hpa-gcp.yaml          # HPA + VPA para GKE
│   └── aws/
│       ├── cluster-setup.sh      # EKS + Karpenter setup
│       └── hpa-aws.yaml          # HPA + NodePool Karpenter (spot)
│
├── loadtesting/                  # Pruebas de carga
│   ├── k6/
│   │   ├── smoke-test.js         # Sanidad rápida (3 VUs, 2 min)
│   │   ├── load-test.js          # Carga normal (25-40 VUs, 10 min)
│   │   ├── stress-test.js        # Estrés: buscar punto de quiebre (75 VUs)
│   │   └── spike-test.js         # Picos súbitos (0→50→0 VUs)
│   ├── locust/
│   │   └── locustfile.py         # Alternativa Python con UI web
│   └── results/
│       └── .gitkeep              # Aquí se guardan los JSON de k6
│
├── scripts/
│   ├── setup-local.sh            # Setup completo en 1 comando
│   ├── benchmark-agent.py        # Benchmark multi-cloud con tabla Rich
│   └── analyze-results.py        # Análisis de JSONs de k6 con recomendaciones
│
├── monitoring/
│   ├── prometheus.yml            # Config Prometheus (scrape del agente)
│   └── grafana/
│       └── dashboard-agent.json  # Dashboard Grafana: P50/P95, tool calls, steps
│
├── docs/
│   ├── AGENT_ARCHITECTURE.md     # Patrón ReAct, herramientas, seguridad, escalabilidad
│   ├── AUTOSCALING_GUIDE.md      # Guía HPA/KEDA/Karpenter en 3 nubes + troubleshooting
│   └── LOAD_TESTING_GUIDE.md     # Metodología: smoke→load→stress→spike + análisis
│
├── tests/
│   ├── test_agent.py             # Tests unitarios: calculadora, weather, search, parser ReAct
│   └── test_api.py               # Tests integración FastAPI: health, /agent/run, /chat, /metrics
│
├── docker-compose.yml            # Stack: llm-agent + ollama + redis + prometheus + grafana
├── .env.example                  # Variables de entorno (copiar a .env)
└── requirements.txt              # Dependencias Python
```

---

## ⚡ Inicio Rápido (5 minutos)

### Prerrequisitos

```bash
# Python 3.11+
python --version

# Docker Desktop
docker --version

# Ollama (LLM local gratuito — sin API key)
curl -fsSL https://ollama.ai/install.sh | sh   # Linux/Mac
# Windows: https://ollama.ai/download

# k6 (pruebas de carga)
# macOS:   brew install k6
# Linux:   snap install k6
# Windows: choco install k6
```

### Setup Local Completo

```bash
# 1. Clonar y configurar
git clone https://github.com/bsginstitute/session7-autoscaling-agent
cd session7-autoscaling-agent
cp .env.example .env

# 2. Entorno virtual
python -m venv venv && source venv/bin/activate   # Linux/Mac
# source venv/Scripts/activate                    # Windows Git Bash

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo LLM local
ollama pull llama3.2:3b   # 2GB — recomendado para clase

# 5. Iniciar todo con Docker Compose
docker-compose up -d

# URLs disponibles:
# API + Agente:  http://localhost:8000/docs
# Grafana:       http://localhost:3000 (admin/admin)
# Prometheus:    http://localhost:9090
```

### Probar el Agente

```bash
# Chat directo
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": "¿Cuánto es 1234 × 5678? Luego dame el clima de Bogotá.",
    "session_id": "demo-001"
  }'

# Chat simple con LLM
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explica el autoescalado en K8s en 3 oraciones."}'
```

---

## 🤖 El Agente LLM (novedad Sesión 7)

El agente usa el patrón **ReAct** (Reasoning + Acting):

```
[Usuario] → "¿Cuánto es 1234 × 5678 y qué clima hay en Bogotá?"
     ↓
[Agente LLM] → Razón: necesito calcular y obtener clima
     ↓
[Tool: calculator] → 1234 × 5678 = 7,006,652
[Tool: weather]    → Bogotá: 14°C, parcialmente nublado
     ↓
[Agente LLM] → Combina resultados y responde al usuario
```

### Herramientas disponibles

| Herramienta | Función | Latencia |
|-------------|---------|---------|
| `calculator` | Cálculos matemáticos | ~5ms |
| `weather` | Clima de cualquier ciudad (mock) | ~50ms |
| `search` | Búsqueda de información (mock) | ~100ms |

---

## ⚙️ Capítulo 5.1 — Autoescalado K8s

### Local con Minikube

```bash
# Iniciar con recursos suficientes
minikube start --cpus=4 --memory=8192
minikube addons enable metrics-server

# Desplegar app + HPA
kubectl apply -f kubernetes/local/

# Monitorear en tiempo real (Terminal 2)
watch -n 2 kubectl get hpa,pods -n llm-prod

# Generar carga para disparar HPA (Terminal 3)
k6 run loadtesting/k6/load-test.js
```

### En Nube (los 3 proveedores)

```bash
# Azure AKS (con KEDA)
cd kubernetes/azure && ./cluster-setup.sh

# GCP GKE Autopilot
cd kubernetes/gcp && ./cluster-setup.sh

# AWS EKS (con Karpenter)
cd kubernetes/aws && ./cluster-setup.sh
```

---

## 🔬 Capítulo 5.2 — Pruebas de Carga del Agente

```bash
# 1. Smoke test — siempre primero
k6 run loadtesting/k6/smoke-test.js

# 2. Load test — carga normal + observar HPA
# (Abrir otra terminal con: watch kubectl get hpa -n llm-prod)
k6 run loadtesting/k6/load-test.js

# 3. Stress test — encontrar el límite
k6 run loadtesting/k6/stress-test.js

# 4. Locust (UI web en http://localhost:8089)
locust -f loadtesting/locust/locustfile.py --host http://localhost:8000

# 5. Benchmark multi-cloud
python scripts/benchmark-agent.py \
  --endpoints \
  http://localhost:8000 \
  https://mi-aks-ip \
  https://mi-gke-ip \
  https://mi-eks-ip
```

---

## 📊 Métricas del Agente

El agente expone métricas específicas en `/metrics`:

| Métrica | Descripción |
|---------|-------------|
| `agent_runs_total` | Total de ejecuciones del agente |
| `agent_tool_calls_total` | Llamadas por herramienta |
| `agent_duration_seconds` | Histograma de latencia del agente |
| `agent_steps_total` | Pasos de razonamiento por request |
| `llm_tokens_total` | Tokens consumidos por el LLM |

---

## 📚 Documentación

- [AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) — Patrón ReAct, herramientas, prompts
- [AUTOSCALING_GUIDE.md](docs/AUTOSCALING_GUIDE.md) — HPA/KEDA en los 3 clouds
- [LOAD_TESTING_GUIDE.md](docs/LOAD_TESTING_GUIDE.md) — Metodología completa de pruebas

---

*BSG Institute · Sesión 7 de 10 · Próxima sesión: Seguridad y Ética en LLMs*
