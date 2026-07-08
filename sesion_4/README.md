# 🚀 Sesión 4: Serverless, Latencia y Alta Disponibilidad para LLMs

**BSG Institute — Diseño de Infraestructura Escalable para LLMs**  
**Capítulo 3 & 4** | Duración: 3 horas

---

## 📋 Contenido de la Sesión

| Capítulo | Tema | Subtemas |
|----------|------|----------|
| **Cap. 3** | Arquitecturas Serverless | Conceptos, servicios, despliegue + LLM en Azure / GCP / AWS |
| **Cap. 4** | Reducción de Latencia y Alta Disponibilidad | Balanceo de carga, autoescalado K8s local/nube, pruebas de carga k6 |

---

## 🗂️ Estructura del Repositorio

```
session4-serverless-ha-llm/
├── app/                          # FastAPI LLM Gateway (evolución de Sesión 3)
│   ├── main.py                   # App principal con métricas extendidas
│   ├── api/
│   │   ├── routes.py             # Endpoints REST
│   │   └── middleware.py         # Latencia, circuit breaker, rate limiting
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas
│   └── utils/
│       ├── ollama_client.py      # Cliente Ollama local
│       └── cache.py              # Cache en memoria + Redis
│
├── serverless/                   # Cap. 3: Ejercicios Serverless
│   ├── azure/
│   │   ├── function_app.py       # Azure Function HTTP trigger + LLM
│   │   ├── host.json             # Config Azure Functions runtime
│   │   ├── local.settings.json   # Variables locales (no commitear con secrets)
│   │   └── deploy.sh             # Script de despliegue
│   ├── gcp/
│   │   ├── main.py               # Google Cloud Function gen2 + LLM
│   │   ├── requirements.txt      # Deps específicas del function
│   │   └── deploy.sh             # Script de despliegue
│   └── aws/
│       ├── handler.py            # AWS Lambda + LLM (Bedrock)
│       ├── template.yaml         # AWS SAM template
│       └── deploy.sh             # Script de despliegue
│
├── kubernetes/                   # Cap. 4: Autoescalado K8s
│   ├── local/
│   │   ├── deployment.yaml       # Deployment base (Minikube)
│   │   ├── hpa.yaml              # HorizontalPodAutoscaler
│   │   ├── vpa.yaml              # VerticalPodAutoscaler
│   │   └── metrics-server.yaml   # Metrics Server para HPA
│   ├── azure/
│   │   ├── cluster-setup.sh      # AKS con KEDA + autoescalado
│   │   ├── hpa-azure.yaml        # HPA configurado para AKS
│   │   └── keda-scaler.yaml      # KEDA ScaledObject para AKS
│   ├── gcp/
│   │   ├── cluster-setup.sh      # GKE Autopilot + VPA
│   │   └── hpa-gcp.yaml          # HPA para GKE
│   └── aws/
│       ├── cluster-setup.sh      # EKS + Karpenter
│       └── hpa-aws.yaml          # HPA para EKS
│
├── loadtesting/                  # Cap. 4: Pruebas de carga
│   ├── k6/
│   │   ├── smoke-test.js         # Test rápido de sanidad (5 usuarios, 1 min)
│   │   ├── load-test.js          # Test de carga normal (50 usuarios, 10 min)
│   │   ├── stress-test.js        # Test de estrés (hasta 200 usuarios)
│   │   └── spike-test.js         # Test de pico súbito
│   ├── locust/
│   │   └── locustfile.py         # Alternativa Python para pruebas de carga
│   └── results/
│       └── .gitkeep
│
├── scripts/
│   ├── setup-local.sh            # Setup completo local (Ollama + app + k8s local)
│   ├── benchmark.py              # Benchmark de latencia multi-cloud
│   └── latency-analyzer.py       # Análisis de resultados con visualización
│
├── docs/
│   ├── SERVERLESS_GUIDE.md       # Guía completa serverless en 3 nubes
│   ├── AUTOSCALING_GUIDE.md      # Guía de autoescalado K8s
│   └── LOAD_TESTING_GUIDE.md     # Guía de pruebas de carga
│
├── tests/
│   ├── test_api.py               # Tests unitarios FastAPI
│   └── test_serverless.py        # Tests de funciones serverless
│
├── .env.example                  # Variables de entorno (template)
├── requirements.txt              # Dependencias Python
└── docker-compose.yml            # Stack local: app + ollama + redis + prometheus + grafana
```

---

## ⚡ Inicio Rápido (5 minutos)

### Prerrequisitos

```bash
# Python 3.11+
python --version

# Docker Desktop
docker --version

# Ollama (LLM local gratuito)
# macOS/Linux:
curl -fsSL https://ollama.ai/install.sh | sh
# Windows: descargar desde https://ollama.ai/download
```

### Setup Local

```bash
# 1. Clonar repositorio
git clone https://github.com/bsginstitute/session4-serverless-ha-llm
cd session4-serverless-ha-llm

# 2. Entorno virtual
python -m venv venv
# Linux/Mac:
source venv/bin/activate
# Windows (Git Bash):
source venv/Scripts/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales (para demos cloud)

# 5. Descargar modelo Ollama
ollama pull llama3.2:3b    # 2GB - Recomendado para clase

# 6. Iniciar aplicación
uvicorn app.main:app --reload --port 8000
```

### Stack Completo con Docker Compose

```bash
# Levanta: FastAPI + Ollama + Redis + Prometheus + Grafana
docker-compose up -d

# Verificar servicios
docker-compose ps

# URLs de acceso:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

---

## 📦 Capítulo 3: Serverless

### Concepto Central

> **Serverless NO significa "sin servidores"** — significa que TÚ no gestionas los servidores. El proveedor cloud escala automáticamente desde 0 hasta millones de requests.

### El mismo ejercicio en las 3 nubes

Vamos a desplegar una **función serverless que recibe texto y retorna un resumen generado por un LLM**:

```
[Cliente HTTP]
     |
     v
[Función Serverless]
     |
     +---> Azure Function + Azure OpenAI
     +---> Google Cloud Function + Vertex AI  
     +---> AWS Lambda + Amazon Bedrock
```

#### Azure Functions

```bash
cd serverless/azure
# Ver deploy.sh para instrucciones completas

# Instalar Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Ejecutar localmente
func start

# Test local
curl -X POST http://localhost:7071/api/llm-summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Kubernetes es un sistema de orquestación de contenedores..."}'

# Deploy a Azure
./deploy.sh
```

#### Google Cloud Functions

```bash
cd serverless/gcp

# Test local con functions-framework
pip install functions-framework
functions-framework --target llm_summarize --port 8080

# Test
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"text": "Texto a resumir..."}'

# Deploy a GCP
./deploy.sh
```

#### AWS Lambda

```bash
cd serverless/aws

# Instalar AWS SAM CLI
pip install aws-sam-cli

# Test local
sam local invoke LLMFunction \
  --event '{"body": "{\"text\": \"Texto a resumir...\"}"}'

# Deploy
./deploy.sh
```

---

## ⚙️ Capítulo 4: Autoescalado

### HPA Local (Minikube)

```bash
# Iniciar Minikube con métricas
minikube start --cpus=4 --memory=8192
minikube addons enable metrics-server

# Desplegar aplicación + HPA
kubectl apply -f kubernetes/local/

# Observar autoescalado en tiempo real
watch kubectl get hpa -n llm-prod
watch kubectl get pods -n llm-prod

# Generar carga para disparar escalado
cd loadtesting
k6 run k6/load-test.js
```

### HPA en Nube

```bash
# Azure AKS
cd kubernetes/azure && ./cluster-setup.sh

# GCP GKE
cd kubernetes/gcp && ./cluster-setup.sh

# AWS EKS
cd kubernetes/aws && ./cluster-setup.sh
```

---

## 🔬 Pruebas de Carga con k6

```bash
# Instalar k6
# macOS:   brew install k6
# Linux:   snap install k6
# Windows: choco install k6

# Test de humo (sanidad rápida)
k6 run loadtesting/k6/smoke-test.js

# Test de carga (normal)
k6 run loadtesting/k6/load-test.js

# Test de estrés (límites del sistema)
k6 run loadtesting/k6/stress-test.js

# Test de pico (spike)
k6 run loadtesting/k6/spike-test.js

# Test contra endpoint en nube
k6 run -e BASE_URL=https://tu-app.azurewebsites.net loadtesting/k6/load-test.js
```

---

## 📊 Análisis de Resultados

```bash
# Benchmark de latencia multi-cloud
python scripts/benchmark.py --endpoints \
  http://localhost:8000 \
  https://tu-function.azurewebsites.net/api/llm-summarize \
  https://us-central1-tu-proyecto.cloudfunctions.net/llm-summarize \
  https://tu-lambda.execute-api.us-east-1.amazonaws.com/prod/summarize

# Análizar resultados guardados
python scripts/latency-analyzer.py --results loadtesting/results/
```

---

## 🌡️ Comparativa Serverless vs Containers

| Criterio | Serverless | Containers (K8s) |
|----------|-----------|-----------------|
| **Cold start LLM** | 2-15 seg | <1 seg (pod ya caliente) |
| **Costo bajo tráfico** | ~$0 (pay-per-use) | $35+/mes (nodos activos) |
| **Costo alto tráfico** | Puede dispararse | Predecible |
| **Estado (memoria)** | Stateless por diseño | Stateful posible |
| **Timeout máximo** | 5-15 min | Sin límite |
| **GPU support** | Limitado | Nativo |
| **Modelo en memoria** | Por invocación | Siempre en RAM |
| **Control de infra** | Bajo | Alto |
| **Mejor para** | APIs ligeras, triggers | LLMs grandes, baja latencia |

---

## 📚 Documentación Adicional

- [SERVERLESS_GUIDE.md](docs/SERVERLESS_GUIDE.md) — Guía completa de serverless en las 3 nubes
- [AUTOSCALING_GUIDE.md](docs/AUTOSCALING_GUIDE.md) — Autoescalado HPA/VPA/KEDA paso a paso
- [LOAD_TESTING_GUIDE.md](docs/LOAD_TESTING_GUIDE.md) — Metodología de pruebas de carga

---

## 🔗 Recursos

| Recurso | URL |
|---------|-----|
| Azure Functions + OpenAI | https://learn.microsoft.com/azure/azure-functions |
| Google Cloud Functions | https://cloud.google.com/functions/docs |
| AWS Lambda | https://docs.aws.amazon.com/lambda |
| k6 Load Testing | https://k6.io/docs |
| KEDA (K8s Event-driven) | https://keda.sh |
| Ollama | https://ollama.ai |

---

*BSG Institute · Sesión 4 de 10 · Próxima sesión: Optimización de Costos y FinOps*
