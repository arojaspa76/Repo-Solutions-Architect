#!/bin/bash
# ============================================================
# deploy-gcp.sh — Despliegue en Google Cloud Platform
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================
#
# Este script despliega la LLM Gateway API en GCP usando:
# 1. Artifact Registry — almacena la imagen Docker
# 2. Cloud Run — ejecuta el contenedor (serverless)
#
# Pre-requisitos:
#   - gcloud CLI: https://cloud.google.com/sdk/docs/install
#   - Docker instalado
#   - Proyecto GCP creado y configurado
#
# Uso:
#   chmod +x docker/deploy-gcp.sh
#   ./docker/deploy-gcp.sh
# ============================================================

set -euo pipefail

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Configuración ─────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
REPO_NAME="llm-session3"
IMAGE_NAME="llm-gateway"
IMAGE_TAG="latest"
SERVICE_NAME="llm-gateway-service"
REGISTRY="${REGION}-docker.pkg.dev"
FULL_IMAGE="${REGISTRY}/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   🚀 DESPLIEGUE LLM GATEWAY → GOOGLE CLOUD           ║"
echo "║   BSG Institute — Sesión 3                            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Verificaciones ────────────────────────────────────────────────────────────
[ -z "$PROJECT_ID" ] && log_error "GCP_PROJECT_ID no definido. Ejecutar: gcloud config set project TU_PROYECTO"
command -v gcloud &>/dev/null || log_error "gcloud CLI no instalado"
log_success "Proyecto GCP: $PROJECT_ID"

# ── Paso 1: Habilitar APIs necesarias ────────────────────────────────────────
log_info "Habilitando APIs de GCP..."
gcloud services enable \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    --project="$PROJECT_ID" \
    --quiet
log_success "APIs habilitadas"

# ── Paso 2: Crear Artifact Registry ──────────────────────────────────────────
log_info "Creando Artifact Registry: $REPO_NAME..."
gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="LLM Gateway — Sesión 3 BSG Institute" \
    --project="$PROJECT_ID" \
    --quiet 2>/dev/null || log_info "El repositorio ya existe, continuando..."
log_success "Artifact Registry listo: ${REGISTRY}/${PROJECT_ID}/${REPO_NAME}"

# ── Paso 3: Autenticar Docker con GCP ────────────────────────────────────────
log_info "Autenticando Docker con Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
log_success "Docker autenticado"

# ── Paso 4: Build y Push usando Cloud Build ───────────────────────────────────
log_info "Construyendo y publicando imagen con Cloud Build..."
gcloud builds submit . \
    --tag="$FULL_IMAGE" \
    --dockerfile=docker/Dockerfile \
    --project="$PROJECT_ID" \
    --quiet
log_success "Imagen publicada: $FULL_IMAGE"

# ── Paso 5: Desplegar en Cloud Run ────────────────────────────────────────────
log_info "Desplegando en Cloud Run (serverless)..."
gcloud run deploy "$SERVICE_NAME" \
    --image="$FULL_IMAGE" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --port=8000 \
    --cpu=1 \
    --memory=512Mi \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=80 \
    --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO" \
    --project="$PROJECT_ID" \
    --quiet
log_success "Cloud Run service desplegado: $SERVICE_NAME"

# ── Paso 6: Obtener URL y verificar ───────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform=managed \
    --region="$REGION" \
    --format='value(status.url)' \
    --project="$PROJECT_ID")

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ DESPLIEGUE COMPLETADO                            ║"
echo "╠═══════════════════════════════════════════════════════╣"
echo "║   URL: ${SERVICE_URL}"
echo "║   Docs: ${SERVICE_URL}/docs"
echo "║   Health: ${SERVICE_URL}/health"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

log_info "Probando health check..."
sleep 5
if curl -s -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
    log_success "¡La API está respondiendo en GCP Cloud Run!"
else
    echo -e "${YELLOW}[WARN]${NC} La API necesita un momento para iniciar (Cold start de Cloud Run)"
fi
