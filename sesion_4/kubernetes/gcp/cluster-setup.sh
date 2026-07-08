#!/bin/bash
# =============================================================
# Setup GKE Autopilot + HPA — Sesión 4
# BSG Institute — Alta Disponibilidad para LLMs
# =============================================================
# GKE Autopilot: Kubernetes serverless — no gestionas nodos,
# pagas solo por pods en ejecución (CPU + RAM solicitados).
# VPA (Vertical Pod Autoscaler) ajusta recursos automáticamente.
# =============================================================

set -euo pipefail

PROJECT=$(gcloud config get-value project)
REGION="${GCP_REGION:-us-central1}"
CLUSTER="bsg-llm-gke"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/bsg-llm"

echo "=================================================="
echo "🟡 Setup GKE Autopilot + HPA — Sesión 4"
echo "   Proyecto: $PROJECT"
echo "   Región:   $REGION"
echo "   Cluster:  $CLUSTER"
echo "=================================================="

# Habilitar APIs
gcloud services enable \
    container.googleapis.com \
    artifactregistry.googleapis.com \
    --quiet

# Artifact Registry
echo "📦 Creando Artifact Registry..."
gcloud artifacts repositories create bsg-llm \
    --repository-format=docker \
    --location=$REGION \
    --quiet 2>/dev/null || echo "Registry ya existe"

# GKE Autopilot — serverless K8s (pagas por pod, no por nodo)
echo "⚙️  Creando clúster GKE Autopilot..."
gcloud container clusters create-auto $CLUSTER \
    --region $REGION \
    --project $PROJECT \
    --quiet

echo "✅ GKE Autopilot creado"

# kubectl credentials
gcloud container clusters get-credentials $CLUSTER --region $REGION --project $PROJECT

# Build y push
echo ""
echo "🐳 Build y push..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
docker build -t ${REGISTRY}/llm-gateway:v1 -f ../../docker/Dockerfile ../..
docker push ${REGISTRY}/llm-gateway:v1

# Deploy
echo ""
echo "🚀 Desplegando en GKE..."
sed "s|REGISTRY|${REGISTRY}|g" deployment-gcp.yaml | kubectl apply -f -
kubectl apply -f hpa-gcp.yaml

kubectl rollout status deployment/llm-gateway -n llm-prod --timeout=300s

# External IP
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get svc llm-gateway-service -n llm-prod \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    [ -n "$EXTERNAL_IP" ] && break
    sleep 10
done

echo ""
echo "=================================================="
echo "✅ GKE AUTOPILOT LISTO"
echo "🌐 API: http://$EXTERNAL_IP"
echo ""
echo "💡 GKE Autopilot escala automáticamente los NODOS."
echo "   HPA escala los PODS. Ambos trabajan juntos."
echo ""
echo "📊 Ver VPA recommendations:"
echo "   kubectl describe vpa llm-gateway-vpa -n llm-prod"
echo "=================================================="
