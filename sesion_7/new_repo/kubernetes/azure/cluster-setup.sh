#!/bin/bash
# =============================================================
# Setup AKS — LLM Agent Gateway con KEDA (Sesión 7)
# BSG Institute
# =============================================================
set -euo pipefail

RG="rg-bsg-session7"
LOCATION="eastus"
CLUSTER="bsg-agent-aks"
NODE_VM="Standard_B2s"
NODE_COUNT=2
ACR_NAME="bsgagentacr$(date +%s | tail -c 6)"

echo "=================================================="
echo "🔵 Setup AKS — LLM Agent Gateway + KEDA"
echo "   Cluster:  $CLUSTER"
echo "   Location: $LOCATION"
echo "=================================================="

az group create --name $RG --location $LOCATION -o none

az acr create --resource-group $RG --name $ACR_NAME --sku Basic -o none
echo "✅ ACR: $ACR_NAME"

az aks create \
    --resource-group $RG \
    --name $CLUSTER \
    --location $LOCATION \
    --node-count $NODE_COUNT \
    --node-vm-size $NODE_VM \
    --enable-cluster-autoscaler \
    --min-count 1 --max-count 6 \
    --enable-addons monitoring \
    --enable-keda \
    --attach-acr $ACR_NAME \
    --generate-ssh-keys \
    --output none

echo "✅ AKS creado con KEDA"

az aks get-credentials --resource-group $RG --name $CLUSTER --overwrite-existing

echo ""
echo "🐳 Build y push del agente..."
az acr login --name $ACR_NAME
docker build -t $ACR_NAME.azurecr.io/llm-agent-gateway:v1 -f docker/Dockerfile .
docker push $ACR_NAME.azurecr.io/llm-agent-gateway:v1

echo ""
echo "🚀 Deploy en AKS..."
sed "s|IMAGE_REGISTRY|$ACR_NAME.azurecr.io|g" kubernetes/azure/deployment-azure.yaml | kubectl apply -f -
kubectl apply -f kubernetes/azure/hpa-azure.yaml
kubectl apply -f kubernetes/azure/keda-scaler.yaml

kubectl rollout status deployment/llm-agent-gateway -n llm-prod --timeout=300s

for i in {1..30}; do
    IP=$(kubectl get svc llm-agent-service -n llm-prod \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    [ -n "$IP" ] && break
    sleep 10
done

echo ""
echo "=================================================="
echo "✅ AKS LISTO"
echo "🌐 API:    http://$IP"
echo "🤖 Agente: http://$IP/agent/run"
echo "📊 Docs:   http://$IP/docs"
echo ""
echo "🧪 Test del agente:"
echo "   curl -X POST http://$IP/agent/run \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"input\": \"¿Cuánto es 1000 * 365?\"}'"
echo ""
echo "⚡ Load test:"
echo "   k6 run -e BASE_URL=http://$IP loadtesting/k6/load-test.js"
echo "=================================================="
