#!/bin/bash
# Setup GKE Autopilot — LLM Agent Gateway (Sesión 7)
set -euo pipefail

PROJECT=$(gcloud config get-value project)
REGION="${GCP_REGION:-us-central1}"
CLUSTER="bsg-agent-gke"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/bsg-agent"

echo "🟡 Setup GKE Autopilot — LLM Agent (Sesión 7)"
echo "   Proyecto: $PROJECT | Región: $REGION"

gcloud services enable container.googleapis.com artifactregistry.googleapis.com --quiet

gcloud artifacts repositories create bsg-agent \
    --repository-format=docker --location=$REGION --quiet 2>/dev/null || true

gcloud container clusters create-auto $CLUSTER \
    --region $REGION --project $PROJECT --quiet

gcloud container clusters get-credentials $CLUSTER --region $REGION --project $PROJECT

gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
docker build -t ${REGISTRY}/llm-agent-gateway:v1 -f docker/Dockerfile .
docker push ${REGISTRY}/llm-agent-gateway:v1

sed "s|IMAGE_REGISTRY|${REGISTRY}|g" kubernetes/gcp/deployment-gcp.yaml | kubectl apply -f -
kubectl apply -f kubernetes/gcp/hpa-gcp.yaml
kubectl rollout status deployment/llm-agent-gateway -n llm-prod --timeout=300s

for i in {1..30}; do
    IP=$(kubectl get svc llm-agent-service -n llm-prod \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    [ -n "$IP" ] && break
    sleep 10
done

echo "✅ GKE Autopilot listo: http://$IP/agent/run"
echo "💡 GKE Autopilot escala nodos automáticamente — HPA escala pods."
