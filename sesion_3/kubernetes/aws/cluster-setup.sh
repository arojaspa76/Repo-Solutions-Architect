#!/bin/bash
# ============================================================
# aws/cluster-setup.sh — Crear clúster EKS
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================

set -euo pipefail
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }

AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
CLUSTER_NAME="eks-llm-session3"
NAMESPACE="llm-session3"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ☸️  CREANDO CLUSTER EKS — AMAZON WEB SERVICES       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Verificar eksctl
if ! command -v eksctl &>/dev/null; then
    log_info "Instalando eksctl..."
    curl --silent --location \
        "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | \
        tar xz -C /tmp
    sudo mv /tmp/eksctl /usr/local/bin
fi

log_info "Creando clúster EKS: $CLUSTER_NAME (puede tardar 15-20 minutos)..."
eksctl create cluster \
    --name "$CLUSTER_NAME" \
    --region "$AWS_REGION" \
    --nodegroup-name standard-workers \
    --node-type t3.medium \
    --nodes 2 \
    --nodes-min 2 \
    --nodes-max 5 \
    --managed \
    --asg-access \
    --full-ecr-access \
    --alb-ingress-access
log_success "Clúster EKS creado"

log_info "Desplegando aplicación..."
kubectl apply -f kubernetes/aws/
kubectl wait --for=condition=ready pod \
    --selector=app=llm-gateway \
    --namespace="$NAMESPACE" \
    --timeout=120s
log_success "Aplicación desplegada"

EXTERNAL_HOST=""
for i in {1..24}; do
    EXTERNAL_HOST=$(kubectl get service llm-gateway-service \
        --namespace="$NAMESPACE" \
        --output=jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    [ -n "$EXTERNAL_HOST" ] && break
    echo "  Esperando hostname... ($i/24)"; sleep 10
done

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ CLÚSTER EKS LISTO                               ║"
echo "║   URL: http://${EXTERNAL_HOST:-<pendiente>}          ║"
echo "╚═══════════════════════════════════════════════════════╝"

echo ""
echo "📌 Comandos útiles:"
echo "   kubectl get pods -n $NAMESPACE"
echo "   eksctl delete cluster --name $CLUSTER_NAME --region $AWS_REGION  # Eliminar"
