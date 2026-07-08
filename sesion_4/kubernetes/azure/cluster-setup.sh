#!/bin/bash
# =============================================================
# Setup AKS + HPA + KEDA — Sesión 4
# BSG Institute — Alta Disponibilidad para LLMs
# =============================================================
# KEDA (Kubernetes Event-driven Autoscaling) extiende HPA con:
#   - Escalar a 0 pods cuando no hay requests (ahorra costo)
#   - Trigger por métricas externas: HTTP, Redis, Queue, etc.
#   - Integración nativa con Azure Service Bus, Event Hub, etc.
# =============================================================

set -euo pipefail

RG="rg-bsg-session4"
LOCATION="eastus"
CLUSTER="bsg-llm-aks"
NODE_VM="Standard_B2s"
NODE_COUNT=2
K8S_VERSION="1.29"
ACR_NAME="bsgllmacr$(date +%s | tail -c 6)"

echo "=================================================="
echo "🔵 Setup AKS con KEDA — Sesión 4"
echo "   Cluster: $CLUSTER"
echo "   VM:      $NODE_VM"
echo "   Nodos:   $NODE_COUNT"
echo "=================================================="

# Resource Group
az group create --name $RG --location $LOCATION -o none

# ACR (Container Registry)
echo "📦 Creando Azure Container Registry..."
az acr create --resource-group $RG --name $ACR_NAME --sku Basic -o none

# AKS Cluster con KEDA y métricas habilitadas
echo "⚙️  Creando clúster AKS..."
az aks create \
    --resource-group $RG \
    --name $CLUSTER \
    --location $LOCATION \
    --kubernetes-version $K8S_VERSION \
    --node-count $NODE_COUNT \
    --node-vm-size $NODE_VM \
    --enable-cluster-autoscaler \
    --min-count 1 \
    --max-count 5 \
    --enable-addons monitoring \
    --enable-keda \
    --attach-acr $ACR_NAME \
    --generate-ssh-keys \
    --output none

echo "✅ Clúster AKS creado con KEDA y Cluster Autoscaler"

# Credenciales kubectl
az aks get-credentials --resource-group $RG --name $CLUSTER --overwrite-existing
echo "✅ kubectl configurado para AKS"

# Construir y push imagen
echo ""
echo "🐳 Build y push de imagen al ACR..."
az acr login --name $ACR_NAME
docker build -t $ACR_NAME.azurecr.io/llm-gateway:v1 -f ../../docker/Dockerfile ../..
docker push $ACR_NAME.azurecr.io/llm-gateway:v1

# Sustituir REGISTRY en los YAMLs y aplicar
echo ""
echo "🚀 Desplegando en AKS..."
sed "s|REGISTRY|$ACR_NAME.azurecr.io|g" deployment-azure.yaml | kubectl apply -f -
kubectl apply -f hpa-azure.yaml
kubectl apply -f keda-scaler.yaml

# Esperar pods listos
echo "⏳ Esperando pods..."
kubectl rollout status deployment/llm-gateway -n llm-prod --timeout=300s

# IP pública
echo ""
echo "⏳ Esperando IP pública del LoadBalancer..."
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get svc llm-gateway-service -n llm-prod \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    [ -n "$EXTERNAL_IP" ] && break
    echo "  ... intento $i/30"
    sleep 10
done

echo ""
echo "=================================================="
echo "✅ AKS LISTO"
echo ""
echo "🌐 API disponible en: http://$EXTERNAL_IP"
echo ""
echo "📊 Monitorear HPA:"
echo "   kubectl get hpa -n llm-prod -w"
echo ""
echo "📊 Ver KEDA ScaledObject:"
echo "   kubectl get scaledobject -n llm-prod"
echo ""
echo "🧪 Test de carga para ver autoescalado:"
echo "   k6 run -e BASE_URL=http://$EXTERNAL_IP ../../loadtesting/k6/load-test.js"
echo "=================================================="
