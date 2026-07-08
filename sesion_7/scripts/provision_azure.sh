#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/provision_azure.sh
# Script de aprovisionamiento completo para el curso.
# Ejecutar una sola vez al inicio; cada sección corresponde a un capítulo.
#
# Requisitos:
#   - Azure CLI instalado y autenticado (az login)
#   - Suscripción activa (Azure for Students funciona)
#
# Uso:
#   chmod +x provision_azure.sh
#   ./provision_azure.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuración global ──────────────────────────────────────────────────────
RESOURCE_GROUP="rg-techcorp-llm"
LOCATION="eastus2"
ACR_NAME="acrtechcorp$(openssl rand -hex 3)"    # Nombre único
AKS_CLUSTER="aks-techcorp"
SEARCH_NAME="srch-techcorp$(openssl rand -hex 3)"
COSMOS_NAME="cosmos-techcorp$(openssl rand -hex 3)"
OPENAI_NAME="oai-techcorp$(openssl rand -hex 3)"
FUNCTION_APP="fn-techcorp-summary"
STORAGE_ACCOUNT="stgtechcorp$(openssl rand -hex 3 | tr -d '[:alpha:]' | head -c 6)"
REDIS_NAME="redis-techcorp$(openssl rand -hex 3)"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   TechCorp LLM — Aprovisionamiento Azure                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "Región: $LOCATION | Grupo de recursos: $RESOURCE_GROUP"
echo ""

# ── Capítulo 1: Grupo de recursos base ───────────────────────────────────────
echo "📦 [CAP 1] Creando grupo de recursos..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags proyecto=techcorp-llm curso=infraestructura-llms \
    --output table

# ── Capítulo 2: ACR y AKS ────────────────────────────────────────────────────
echo ""
echo "🐳 [CAP 2] Creando Azure Container Registry..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output table

echo ""
echo "☸️  [CAP 2] Creando clúster AKS (esto tarda ~5 minutos)..."
az aks create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --node-count 2 \
    --node-vm-size Standard_D4s_v3 \
    --attach-acr "$ACR_NAME" \
    --enable-managed-identity \
    --network-plugin azure \
    --enable-cluster-autoscaler \
    --min-count 2 \
    --max-count 8 \
    --generate-ssh-keys \
    --tags proyecto=techcorp-llm \
    --output table

echo "🔑 Configurando kubectl..."
az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --overwrite-existing

echo ""
echo "🏊 [CAP 2] Agregando spot node pool para cargas batch..."
az aks nodepool add \
    --resource-group "$RESOURCE_GROUP" \
    --cluster-name "$AKS_CLUSTER" \
    --name spotpool \
    --priority Spot \
    --eviction-policy Delete \
    --spot-max-price -1 \
    --node-count 2 \
    --node-vm-size Standard_D4s_v3 \
    --output table

# ── Capítulo 3: Azure Functions ───────────────────────────────────────────────
echo ""
echo "⚡ [CAP 3] Creando Storage Account para Azure Functions..."
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --sku Standard_LRS \
    --output table

echo "⚡ [CAP 3] Creando Function App..."
az functionapp create \
    --resource-group "$RESOURCE_GROUP" \
    --consumption-plan-location "$LOCATION" \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --name "$FUNCTION_APP" \
    --storage-account "$STORAGE_ACCOUNT" \
    --output table

# ── Capítulo 4: Redis para caché semántica ────────────────────────────────────
echo ""
echo "🔴 [CAP 4] Creando Azure Cache for Redis (C0 tier, ~15 min)..."
az redis create \
    --name "$REDIS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Basic \
    --vm-size c0 \
    --output table

echo "💰 [CAP 4] Configurando presupuesto con alerta al 80%..."
az consumption budget create \
    --budget-name "budget-techcorp-llm" \
    --amount 2000 \
    --time-grain Monthly \
    --start-date "$(date +%Y-%m-01)" \
    --end-date "$(date -d '+1 year' +%Y-%m-01)" \
    --resource-group "$RESOURCE_GROUP" \
    --threshold 80 \
    --contact-emails "arquitecto@techcorp.com" \
    --output table 2>/dev/null || echo "⚠️  Budget requiere permisos de billing. Configurar desde el portal."

# ── Capítulo 5: Azure Front Door ─────────────────────────────────────────────
echo ""
echo "🌐 [CAP 5] Creando perfil Azure Front Door..."
az afd profile create \
    --profile-name "afd-techcorp" \
    --resource-group "$RESOURCE_GROUP" \
    --sku Standard_AzureFrontDoor \
    --output table

# ── Capítulo 6: Azure AI Search y Cosmos DB ───────────────────────────────────
echo ""
echo "🔍 [CAP 6] Creando Azure AI Search (Standard S1)..."
az search service create \
    --name "$SEARCH_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --sku Standard \
    --partition-count 1 \
    --replica-count 1 \
    --output table

echo ""
echo "🌌 [CAP 6] Creando Azure Cosmos DB (modo serverless)..."
az cosmosdb create \
    --name "$COSMOS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --locations regionName="$LOCATION" \
    --capabilities EnableServerless \
    --default-consistency-level Session \
    --output table

az cosmosdb sql database create \
    --account-name "$COSMOS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --name "techcorp-chatbot" \
    --output table

az cosmosdb sql container create \
    --account-name "$COSMOS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --database-name "techcorp-chatbot" \
    --name "conversations" \
    --partition-key-path "/session_id" \
    --output table

# ── Resumen final ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   ✅ Aprovisionamiento completado                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Recursos creados:"
az resource list --resource-group "$RESOURCE_GROUP" \
    --output table --query "[].{Nombre:name, Tipo:type}"

echo ""
echo "⚠️  IMPORTANTE: Copiar los valores de conexión al archivo .env"
echo ""
echo "ACR:     $ACR_NAME.azurecr.io"
echo "AKS:     $AKS_CLUSTER"
echo "Search:  $SEARCH_NAME.search.windows.net"
echo "Cosmos:  $COSMOS_NAME.documents.azure.com"
echo "Redis:   $REDIS_NAME.redis.cache.windows.net"
echo ""
echo "🗑️  Para ELIMINAR todos los recursos al final del curso:"
echo "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
