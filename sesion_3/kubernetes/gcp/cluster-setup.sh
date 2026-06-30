#!/bin/bash
# ============================================================
# gcp/cluster-setup.sh — Crear clúster GKE
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================

set -euo pipefail
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"
CLUSTER_NAME="gke-llm-session3"
NAMESPACE="llm-session3"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ☸️  CREANDO CLUSTER GKE — GOOGLE CLOUD              ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

log_info "Habilitando APIs..."
gcloud services enable container.googleapis.com --project="$PROJECT_ID" --quiet

log_info "Creando clúster GKE: $CLUSTER_NAME..."
gcloud container clusters create "$CLUSTER_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --num-nodes=2 \
    --machine-type=e2-standard-2 \
    --enable-autoscaling \
    --min-nodes=2 \
    --max-nodes=5 \
    --enable-autorepair \
    --enable-autoupgrade \
    --release-channel=regular \
    --workload-pool="${PROJECT_ID}.svc.id.goog" \
    --quiet
log_success "Clúster GKE creado"

log_info "Obteniendo credenciales..."
gcloud container clusters get-credentials "$CLUSTER_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID"
log_success "kubectl configurado"

log_info "Desplegando en GKE..."
kubectl apply -f kubernetes/gcp/
kubectl wait --for=condition=ready pod \
    --selector=app=llm-gateway \
    --namespace="$NAMESPACE" \
    --timeout=120s
log_success "Aplicación desplegada"

EXTERNAL_IP=""
for i in {1..18}; do
    EXTERNAL_IP=$(kubectl get service llm-gateway-service \
        --namespace="$NAMESPACE" \
        --output=jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    [ -n "$EXTERNAL_IP" ] && break
    echo "  Esperando IP... ($i/18)"; sleep 10
done

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ CLÚSTER GKE LISTO                               ║"
echo "║   URL: http://${EXTERNAL_IP:-<pendiente>}            ║"
echo "╚═══════════════════════════════════════════════════════╝"

echo ""
echo "📌 Comandos útiles:"
echo "   kubectl get pods -n $NAMESPACE"
echo "   kubectl get services -n $NAMESPACE"
echo "   gcloud container clusters delete $CLUSTER_NAME --region $REGION --quiet  # Eliminar"
