#!/bin/bash
# ============================================================
# azure/cluster-setup.sh — Crear clúster AKS
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================
#
# Crea un clúster Kubernetes en Azure Kubernetes Service (AKS)
# y despliega la LLM Gateway API.
#
# Uso:
#   chmod +x kubernetes/azure/cluster-setup.sh
#   ./kubernetes/azure/cluster-setup.sh
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }

# ── Configuración ─────────────────────────────────────────────────────────────
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-llm-session3}"
CLUSTER_NAME="aks-llm-session3"
LOCATION="${AZURE_LOCATION:-eastus}"
NODE_COUNT=2
NODE_VM_SIZE="Standard_D2s_v3"    # 2 vCPU, 8GB RAM
NAMESPACE="llm-session3"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ☸️  CREANDO CLUSTER AKS — MICROSOFT AZURE           ║"
echo "║   BSG Institute — Sesión 3                            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Paso 1: Crear Resource Group ─────────────────────────────────────────────
log_info "Creando Resource Group: $RESOURCE_GROUP..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
log_success "Resource Group listo"

# ── Paso 2: Crear clúster AKS ────────────────────────────────────────────────
log_info "Creando clúster AKS: $CLUSTER_NAME (puede tardar 5-10 minutos)..."
az aks create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --node-count "$NODE_COUNT" \
    --node-vm-size "$NODE_VM_SIZE" \
    --enable-addons monitoring \
    --enable-cluster-autoscaler \
    --min-count 2 \
    --max-count 5 \
    --generate-ssh-keys \
    --output none
log_success "Clúster AKS creado: $CLUSTER_NAME"

# ── Paso 3: Obtener credenciales ─────────────────────────────────────────────
log_info "Obteniendo credenciales kubectl..."
az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --overwrite-existing
log_success "Credenciales configuradas en ~/.kube/config"

# ── Paso 4: Verificar conexión ────────────────────────────────────────────────
log_info "Verificando conexión al clúster..."
kubectl get nodes
echo ""

# ── Paso 5: Desplegar la aplicación ──────────────────────────────────────────
log_info "Desplegando LLM Gateway en AKS..."
kubectl apply -f kubernetes/azure/
log_success "Manifiestos aplicados"

# ── Paso 6: Esperar a que los pods estén listos ───────────────────────────────
log_info "Esperando a que los pods inicien..."
kubectl wait \
    --for=condition=ready pod \
    --selector=app=llm-gateway \
    --namespace="$NAMESPACE" \
    --timeout=120s
log_success "Pods listos"

# ── Paso 7: Obtener IP externa ────────────────────────────────────────────────
log_info "Obteniendo IP externa del Load Balancer (puede tardar 2-3 min)..."
for i in {1..18}; do
    EXTERNAL_IP=$(kubectl get service llm-gateway-service \
        --namespace="$NAMESPACE" \
        --output=jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [ -n "$EXTERNAL_IP" ]; then
        break
    fi
    echo "  Esperando asignación de IP... ($i/18)"
    sleep 10
done

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ CLÚSTER AKS LISTO                               ║"
echo "╠═══════════════════════════════════════════════════════╣"
echo "║   Clúster: $CLUSTER_NAME"
echo "║   URL: http://${EXTERNAL_IP:-<pendiente>}"
echo "║   Docs: http://${EXTERNAL_IP:-<pendiente>}/docs"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Comandos útiles
echo "📌 Comandos útiles:"
echo "   kubectl get pods -n $NAMESPACE"
echo "   kubectl get services -n $NAMESPACE"
echo "   kubectl logs -f deployment/llm-gateway -n $NAMESPACE"
echo "   kubectl scale deployment/llm-gateway --replicas=4 -n $NAMESPACE"
echo "   az aks delete --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --yes  # Eliminar clúster"
