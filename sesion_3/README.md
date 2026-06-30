# 🚀 Sesión 3 — Kubernetes, Docker y Contenedores para LLMs
## Curso: Diseño de Infraestructura Escalable para LLMs

> **BSG Institute** | Capítulo 2: Sistemas Distribuidos y Contenedores

---

## 📋 Descripción

Este repositorio contiene todo el material práctico de la **Sesión 3**, donde aprenderás a:

1. Desplegar aplicaciones LLM con **Docker** (local, Azure, GCP, AWS)
2. Orquestar contenedores con **Kubernetes** (local con Minikube + las 3 nubes)
3. Ejecutar un **LLM local con Ollama** y consumirlo via FastAPI
4. Comparar estrategias de costos entre proveedores cloud

---

## 🏗️ Arquitectura del Ejercicio

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE / ALUMNO                          │
│                  curl / Postman / Browser                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI — LLM Gateway API                       │
│         /health  /chat  /models  /embeddings                 │
│              (Puerto 8000)                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴────────────────┐
           ▼                                ▼
┌──────────────────┐              ┌──────────────────────┐
│  Ollama Server   │              │  Azure/GCP/AWS LLM   │
│  (Local LLM)     │              │  (Cloud API)         │
│  llama3.2:3b     │              │  GPT-4o / Gemini /   │
│  mistral:7b      │              │  Claude / Bedrock    │
│  Puerto 11434    │              │                      │
└──────────────────┘              └──────────────────────┘
```

---

## 📁 Estructura del Repositorio

```
sesion_3/
├── README.md                          # Este archivo
├── requirements.txt                   # Dependencias Python
├── .env.example                       # Variables de entorno (plantilla)
├── .gitignore                         # Archivos ignorados
│
├── app/                               # Código FastAPI
│   ├── main.py                        # Punto de entrada
│   ├── api/
│   │   ├── routes.py                  # Endpoints REST
│   │   └── middleware.py              # CORS, logging, rate-limit
│   ├── models/
│   │   └── schemas.py                 # Pydantic schemas
│   └── utils/
│       ├── ollama_client.py           # Cliente Ollama local
│       └── cloud_clients.py           # Clientes Azure/GCP/AWS
│
├── docker/                            # Docker (mismo ejercicio, 3 nubes)
│   ├── Dockerfile                     # Imagen base de la app
│   ├── docker-compose.yml             # Stack local completo
│   ├── docker-compose.ollama.yml      # Ollama + FastAPI local
│   ├── deploy-azure.sh                # Script despliegue Azure ACR + ACI
│   ├── deploy-gcp.sh                  # Script despliegue GCP Artifact + Cloud Run
│   └── deploy-aws.sh                  # Script despliegue AWS ECR + ECS
│
├── kubernetes/                        # Kubernetes (mismo ejercicio, 3 nubes)
│   ├── local/                         # Minikube
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── hpa.yaml
│   ├── azure/                         # AKS — Azure Kubernetes Service
│   │   ├── cluster-setup.sh
│   │   ├── deployment.yaml
│   │   └── ingress.yaml
│   ├── gcp/                           # GKE — Google Kubernetes Engine
│   │   ├── cluster-setup.sh
│   │   ├── deployment.yaml
│   │   └── ingress.yaml
│   └── aws/                           # EKS — Amazon Elastic Kubernetes Service
│       ├── cluster-setup.sh
│       ├── deployment.yaml
│       └── ingress.yaml
│
├── scripts/
│   ├── setup-ollama.sh                # Instala y configura Ollama
│   ├── test-api.sh                    # Pruebas rápidas de la API
│   └── cost-calculator.py             # Calculadora de costos multi-cloud
│
└── docs/
    ├── OLLAMA_GUIDE.md                # Guía detallada de Ollama local
    ├── DOCKER_GUIDE.md                # Guía Docker paso a paso
    ├── KUBERNETES_GUIDE.md            # Guía Kubernetes completa
    └── COST_ANALYSIS.md               # Análisis de costos y ROI
```

---

## 🚀 Inicio Rápido

### Prerequisitos

```bash
# Verificar instalaciones
python --version        # Python 3.10+
docker --version        # Docker 24+
docker compose version  # Docker Compose 2+
kubectl version         # kubectl 1.28+
```

### 1. Clonar y Configurar

```bash
git clone https://github.com/arojaspa76/Repo-Solutions-Architect.git
cd Repo-Solutions-Architect
cd sesion_3

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate       # Linux/Mac
# .venv\Scripts\activate        # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### 2. Ejecutar con Ollama (LLM Local — RECOMENDADO para practicar)

```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh   # Linux/Mac
# En Windows: descargar desde https://ollama.ai/download

# Descargar un modelo (elige uno según tu RAM disponible)
ollama pull llama3.2:3b     # ~2GB RAM — recomendado para clases
ollama pull mistral:7b      # ~5GB RAM
ollama pull llama3.1:8b     # ~8GB RAM

# Verificar que Ollama está corriendo
ollama list
curl http://localhost:11434/api/tags

# Iniciar la API FastAPI
uvicorn app.main:app --reload --port 8000
```

### 3. Ejecutar con Docker Compose (Stack completo local)

```bash
# Modo 1: Solo la app FastAPI (Ollama debe estar instalado)
docker compose up -d

# Modo 2: App + Ollama en contenedores (todo en Docker)
docker compose -f docker/docker-compose.ollama.yml up -d

# Ver logs
docker compose logs -f

# Verificar salud
curl http://localhost:8000/health
```

### 4. Probar la API

```bash
# Health check
curl http://localhost:8000/health

# Listar modelos disponibles
curl http://localhost:8000/models

# Chat con el LLM
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Qué es Kubernetes y para qué sirve?",
    "model": "llama3.2:3b",
    "temperature": 0.7
  }'

# Generar embeddings
curl -X POST http://localhost:8000/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Infraestructura cloud para LLMs",
    "model": "llama3.2:3b"
  }'
```

---

## ☁️ Despliegue en la Nube (Mismo Ejercicio, 3 Nubes)

El principio clave de esta sesión: **el código no cambia, solo cambia la infraestructura cloud**.

| Componente | Azure | GCP | AWS |
|-----------|-------|-----|-----|
| Registro Docker | Azure Container Registry (ACR) | Artifact Registry | Elastic Container Registry (ECR) |
| Contenedores | Azure Container Instances (ACI) | Cloud Run | ECS Fargate |
| Kubernetes | AKS | GKE | EKS |
| LLM API | Azure OpenAI | Vertex AI | Amazon Bedrock |
| Secretos | Azure Key Vault | Secret Manager | AWS Secrets Manager |

### Desplegar en Azure

```bash
chmod +x docker/deploy-azure.sh
./docker/deploy-azure.sh
```

### Desplegar en GCP

```bash
chmod +x docker/deploy-gcp.sh
./docker/deploy-gcp.sh
```

### Desplegar en AWS

```bash
chmod +x docker/deploy-aws.sh
./docker/deploy-aws.sh
```

---

## 📊 Análisis de Costos

Ejecuta la calculadora de costos multi-cloud:

```bash
python scripts/cost-calculator.py
```

Ver el análisis completo en [docs/COST_ANALYSIS.md](docs/COST_ANALYSIS.md)

---

## 🧪 Tests

```bash
# Correr todos los tests
pytest tests/ -v

# Test de integración con Ollama
pytest tests/test_ollama.py -v

# Test de la API REST
pytest tests/test_api.py -v
```

---

## 📚 Documentación Adicional

- [Guía Ollama Local](docs/OLLAMA_GUIDE.md)
- [Guía Docker Completa](docs/DOCKER_GUIDE.md)
- [Guía Kubernetes Completa](docs/KUBERNETES_GUIDE.md)
- [Análisis de Costos y ROI](docs/COST_ANALYSIS.md)

---

## 🤝 Contribuciones

Este repositorio es material educativo del BSG Institute. Para reporte de errores o mejoras, abre un issue.

---

**BSG Institute** | Curso: Diseño de Infraestructura Escalable para LLMs | Sesión 3
