#!/bin/bash
# ============================================================
# deploy-azure.sh — Despliegue en Microsoft Azure
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================
#
# Este script despliega la LLM Gateway API en Azure usando:
# 1. Azure Container Registry (ACR) — almacena la imagen Docker
# 2. Azure Container Instances (ACI) — ejecuta el contenedor
#
# Pre-requisitos:
#   - Azure CLI instalado: https://docs.microsoft.com/cli/azure/install-azure-cli
#   - Docker instalado y corriendo
#   - Sesión activa: az login
#
# Uso:
#   chmod +x docker/deploy-azure.sh
#   ./docker/deploy-azure.sh
# ============================================================

set -euo pipefail  # Salir si cualquier comando falla

# ── Colores para output ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin color

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Configuración ─────────────────────────────────────────────────────────────
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-llm-session3}"
LOCATION="${AZURE_LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-llmsession3acr}"            # Nombre único globalmente
IMAGE_NAME="llm-gateway"
IMAGE_TAG="latest"
CONTAINER_NAME="llm-gateway-aci"
DNS_LABEL="llm-gateway-bsg"                        # URL pública: $DNS_LABEL.$LOCATION.azurecontainer.io

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   🚀 DESPLIEGUE LLM GATEWAY → MICROSOFT AZURE        ║"
echo "║   BSG Institute — Sesión 3                            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Paso 1: Verificar Azure CLI ───────────────────────────────────────────────
log_info "Verificando Azure CLI..."
if ! command -v az &> /dev/null; then
    log_error "Azure CLI no instalado. Instalar en: https://docs.microsoft.com/cli/azure/install-azure-cli"
fi

# Verificar sesión activa
ACCOUNT=$(az account show --query "name" -o tsv 2>/dev/null || echo "")
if [ -z "$ACCOUNT" ]; then
    log_error "No hay sesión Azure activa. Ejecutar: az login"
fi
log_success "Conectado a cuenta: $ACCOUNT"

# ── Paso 2: Crear Resource Group ─────────────────────────────────────────────
log_info "Creando Resource Group: $RESOURCE_GROUP en $LOCATION..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none
log_success "Resource Group listo: $RESOURCE_GROUP"

# ── Paso 3: Crear Azure Container Registry ────────────────────────────────────
log_info "Creando Container Registry: $ACR_NAME..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true \
    --output none
log_success "ACR creado: ${ACR_NAME}.azurecr.io"

# ── Paso 4: Build y Push de la imagen ────────────────────────────────────────
log_info "Construyendo imagen Docker..."
# Usamos ACR Tasks para construir directamente en la nube (no requiere Docker local con ARM)
az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_NAME}:${IMAGE_TAG}" \
    --file docker/Dockerfile \
    . \
    --output none
log_success "Imagen publicada: ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

# ── Paso 5: Obtener credenciales del ACR ─────────────────────────────────────
log_info "Obteniendo credenciales del ACR..."
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query "username" -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
ACR_SERVER="${ACR_NAME}.azurecr.io"

# ── Paso 6: Desplegar en Azure Container Instances ───────────────────────────
log_info "Desplegando contenedor en Azure Container Instances..."
az container create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --image "${ACR_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}" \
    --registry-login-server "$ACR_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --cpu 1 \
    --memory 1.5 \
    --ports 8000 \
    --protocol TCP \
    --dns-name-label "$DNS_LABEL" \
    --environment-variables \
        ENVIRONMENT=production \
        LOG_LEVEL=INFO \
    --restart-policy Always \
    --output none
log_success "Contenedor desplegado: $CONTAINER_NAME"

# ── Paso 7: Verificar despliegue ─────────────────────────────────────────────
log_info "Esperando que el contenedor inicie..."
sleep 30

FQDN=$(az container show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --query "ipAddress.fqdn" \
    -o tsv)

STATE=$(az container show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CONTAINER_NAME" \
    --query "instanceView.state" \
    -o tsv)

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ DESPLIEGUE COMPLETADO                            ║"
echo "╠═══════════════════════════════════════════════════════╣"
echo "║   Estado: $STATE"
echo "║   URL: http://$FQDN:8000"
echo "║   Docs: http://$FQDN:8000/docs"
echo "║   Health: http://$FQDN:8000/health"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Probar health check
log_info "Probando health check..."
if curl -s -f "http://${FQDN}:8000/health" > /dev/null 2>&1; then
    log_success "¡La API está respondiendo correctamente!"
else
    log_warning "La API no responde todavía (puede necesitar más tiempo para iniciar)"
    log_info "Verifica los logs con: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
fi
