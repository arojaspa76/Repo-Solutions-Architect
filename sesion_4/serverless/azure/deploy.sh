#!/bin/bash
# =============================================================
# Deploy Azure Function — LLM Summarizer
# BSG Institute — Sesión 4: Serverless + Alta Disponibilidad
# =============================================================
# Prerrequisitos:
#   - az cli instalado y autenticado: az login
#   - Azure Functions Core Tools: npm install -g azure-functions-core-tools@4
#   - Python 3.11
# =============================================================

set -euo pipefail

# ── Configuración ─────────────────────────────────────────────────────────────
RESOURCE_GROUP="rg-bsg-session4"
LOCATION="eastus"                       # Región: eastus, westus2, brazilsouth (LATAM)
STORAGE_ACCOUNT="bsgllmstorage$(date +%s | tail -c 6)"
FUNCTION_APP_NAME="bsg-llm-func-$(date +%s | tail -c 6)"
PYTHON_VERSION="3.11"
SKU="Y1"                                # Y1=Consumption (pay-per-use), EP1=Premium

echo "=================================================="
echo "🔵 Deploy Azure Function — LLM Summarizer"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Function App:   $FUNCTION_APP_NAME"
echo "   Location:       $LOCATION"
echo "   Plan:           Consumption (${SKU})"
echo "=================================================="

# ── Verificar login ────────────────────────────────────────────────────────────
echo ""
echo "✅ Verificando autenticación Azure..."
az account show --query "{subscription:name, id:id}" -o table || {
    echo "❌ No autenticado. Ejecutar: az login"
    exit 1
}

# ── Resource Group ────────────────────────────────────────────────────────────
echo ""
echo "📦 Creando Resource Group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
echo "✅ Resource Group listo"

# ── Storage Account (requerido por Azure Functions) ────────────────────────────
echo ""
echo "💾 Creando Storage Account: $STORAGE_ACCOUNT"
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --output none
echo "✅ Storage Account listo"

# ── Function App ───────────────────────────────────────────────────────────────
echo ""
echo "⚡ Creando Function App: $FUNCTION_APP_NAME"
az functionapp create \
    --resource-group "$RESOURCE_GROUP" \
    --consumption-plan-location "$LOCATION" \
    --runtime python \
    --runtime-version "$PYTHON_VERSION" \
    --functions-version 4 \
    --name "$FUNCTION_APP_NAME" \
    --storage-account "$STORAGE_ACCOUNT" \
    --os-type Linux \
    --output none

echo "✅ Function App creada"

# ── App Settings (variables de entorno) ───────────────────────────────────────
echo ""
echo "⚙️  Configurando variables de entorno..."
az functionapp config appsettings set \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings \
        USE_OLLAMA=false \
        AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-}" \
        AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}" \
        AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    --output none
echo "✅ Variables configuradas"

# ── Deploy código ──────────────────────────────────────────────────────────────
echo ""
echo "🚀 Desplegando código..."
func azure functionapp publish "$FUNCTION_APP_NAME" \
    --python \
    --build remote
echo "✅ Código desplegado"

# ── Obtener URL ───────────────────────────────────────────────────────────────
FUNCTION_URL=$(az functionapp function show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$FUNCTION_APP_NAME" \
    --function-name "llm-summarize" \
    --query "invokeUrlTemplate" -o tsv 2>/dev/null || \
    echo "https://${FUNCTION_APP_NAME}.azurewebsites.net/api/llm-summarize")

echo ""
echo "=================================================="
echo "✅ DEPLOY COMPLETADO"
echo ""
echo "🌐 URL del endpoint:"
echo "   $FUNCTION_URL"
echo ""
echo "🧪 Test rápido:"
echo "   curl -X POST \"$FUNCTION_URL\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"text\": \"Kubernetes es un orquestador de contenedores...\", \"language\": \"es\"}'"
echo ""
echo "🔍 Ver logs en tiempo real:"
echo "   az webapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "💰 Monitoreo de costos:"
echo "   Portal Azure → Cost Management → Resource Group: $RESOURCE_GROUP"
echo "=================================================="

# Guardar URL para uso posterior
echo "AZURE_FUNCTION_URL=$FUNCTION_URL" >> ../../.env.outputs
