# =============================================================================
# scripts/provision_azure.ps1
# Aprovisionamiento completo del curso — version PowerShell (Windows)
#
# Equivalente exacto de provision_azure.sh para estudiantes en Windows.
# Cada seccion corresponde a un capitulo del curso.
#
# Requisitos:
#   - Azure CLI instalado: https://aka.ms/installazurecliwindows
#   - PowerShell 5.1+ o PowerShell 7+ (recomendado)
#   - Sin permisos de administrador necesarios para az CLI
#
# Uso:
#   .\provision_azure.ps1
#
# Si PowerShell bloquea la ejecucion por politica:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# =============================================================================

#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Funcion auxiliar: generar sufijo aleatorio de 6 hex (reemplaza openssl) ──
function New-HexSuffix {
    param([int]$Length = 6)
    $bytes = New-Object byte[] ($Length / 2)
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# ── Funcion auxiliar: imprimir con color ─────────────────────────────────────
function Write-Step {
    param([string]$Emoji, [string]$Cap, [string]$Message)
    Write-Host ""
    Write-Host "$Emoji [$Cap] $Message" -ForegroundColor Cyan
}

function Write-OK   { param([string]$m) Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Warn { param([string]$m) Write-Host "  WARN $m" -ForegroundColor Yellow }
function Write-Info { param([string]$m) Write-Host "       $m" -ForegroundColor Gray }

# ── Configuracion global ──────────────────────────────────────────────────────
$RESOURCE_GROUP   = "rg-techcorp-llm"
$LOCATION         = "eastus2"
$ACR_NAME         = "acrtechcorp$(New-HexSuffix)"
$AKS_CLUSTER      = "aks-techcorp"
$SEARCH_NAME      = "srch-techcorp$(New-HexSuffix)"
$COSMOS_NAME      = "cosmos-techcorp$(New-HexSuffix)"
$FUNCTION_APP     = "fn-techcorp-summary"
# Storage Account: solo letras minusculas y numeros, max 24 chars
$STORAGE_ACCOUNT  = "stgtechcorp$(New-HexSuffix -Length 8)"
$REDIS_NAME       = "redis-techcorp$(New-HexSuffix)"

# Fechas para el presupuesto (equivale a $(date +%Y-%m-01) en bash)
$TODAY        = Get-Date
$START_DATE   = (Get-Date -Year $TODAY.Year -Month $TODAY.Month -Day 1).ToString("yyyy-MM-dd")
$END_DATE     = (Get-Date -Year ($TODAY.Year + 1) -Month $TODAY.Month -Day 1).ToString("yyyy-MM-dd")

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "   TechCorp LLM - Aprovisionamiento Azure (PowerShell)"          -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host "   Region: $LOCATION"
Write-Host "   Grupo:  $RESOURCE_GROUP"
Write-Host "   ACR:    $ACR_NAME"
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""

# ── PRE-REQUISITO: Registrar namespaces (frecuente en cuentas nuevas) ─────────
Write-Step ">" "PRE" "Registrando resource providers de Azure..."
Write-Info "Esto evita el error MissingSubscriptionRegistration."

$namespaces = @(
    "Microsoft.ContainerRegistry",
    "Microsoft.ContainerService",
    "Microsoft.Web",
    "Microsoft.Search",
    "Microsoft.DocumentDB",
    "Microsoft.Cache",
    "Microsoft.CognitiveServices",
    "Microsoft.Cdn",
    "Microsoft.Storage",
    "Microsoft.Insights",
    "Microsoft.OperationalInsights"
)

foreach ($ns in $namespaces) {
    Write-Info "Registrando $ns ..."
    az provider register --namespace $ns | Out-Null
}

Write-Info "Esperando confirmacion de registro (30s)..."
Start-Sleep -Seconds 30

# Verificar que esten en Registered o Registering
foreach ($ns in $namespaces) {
    $state = az provider show --namespace $ns --query "registrationState" -o tsv 2>$null
    if ($state -eq "Registered" -or $state -eq "Registering") {
        Write-OK "$ns -> $state"
    } else {
        Write-Warn "$ns -> $state (puede tardar unos minutos mas)"
    }
}

# ── Verificar login en Azure ──────────────────────────────────────────────────
Write-Step ">" "PRE" "Verificando sesion en Azure CLI..."
$account = az account show --query "user.name" -o tsv 2>$null
if (-not $account) {
    Write-Host "  No hay sesion activa. Iniciando az login..." -ForegroundColor Yellow
    az login --use-device-code
    $account = az account show --query "user.name" -o tsv
}
Write-OK "Conectado como: $account"

# =============================================================================
# CAPITULO 1 — Grupo de recursos base
# =============================================================================
Write-Step "[CAP 1]" "CAP 1" "Creando grupo de recursos..."

az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION `
    --tags proyecto=techcorp-llm curso=infraestructura-llms `
    --output table

Write-OK "Grupo de recursos '$RESOURCE_GROUP' listo."

# =============================================================================
# CAPITULO 2 — Azure Container Registry y AKS
# =============================================================================
Write-Step "[CAP 2]" "CAP 2" "Creando Azure Container Registry..."

az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $ACR_NAME `
    --sku Basic `
    --admin-enabled true `
    --output table

Write-OK "ACR '$ACR_NAME' creado."

# ── AKS ───────────────────────────────────────────────────────────────────────
Write-Step "[CAP 2]" "CAP 2" "Creando cluster AKS (puede tardar 5-8 minutos)..."
Write-Info "VM size: Standard_D4s_v3 | Nodos: 2 | Autoscaler: 2-8"

az aks create `
    --resource-group $RESOURCE_GROUP `
    --name $AKS_CLUSTER `
    --node-count 2 `
    --node-vm-size Standard_D4s_v3 `
    --attach-acr $ACR_NAME `
    --enable-managed-identity `
    --network-plugin azure `
    --enable-cluster-autoscaler `
    --min-count 2 `
    --max-count 8 `
    --generate-ssh-keys `
    --tags proyecto=techcorp-llm `
    --output table

Write-OK "Cluster AKS '$AKS_CLUSTER' creado."

# ── Configurar kubectl ────────────────────────────────────────────────────────
Write-Info "Configurando kubectl..."
az aks get-credentials `
    --resource-group $RESOURCE_GROUP `
    --name $AKS_CLUSTER `
    --overwrite-existing

Write-OK "kubectl configurado. Prueba: kubectl get nodes"

# ── Spot node pool ────────────────────────────────────────────────────────────
Write-Step "[CAP 2]" "CAP 2" "Agregando spot node pool (cargas batch, Cap. 4)..."

az aks nodepool add `
    --resource-group $RESOURCE_GROUP `
    --cluster-name $AKS_CLUSTER `
    --name spotpool `
    --priority Spot `
    --eviction-policy Delete `
    --spot-max-price -1 `
    --node-count 2 `
    --node-vm-size Standard_D4s_v3 `
    --output table

Write-OK "Spot node pool creado."

# =============================================================================
# CAPITULO 3 — Azure Functions (serverless)
# =============================================================================
Write-Step "[CAP 3]" "CAP 3" "Creando Storage Account para Azure Functions..."

az storage account create `
    --name $STORAGE_ACCOUNT `
    --resource-group $RESOURCE_GROUP `
    --sku Standard_LRS `
    --output table

Write-OK "Storage Account '$STORAGE_ACCOUNT' creado."

Write-Step "[CAP 3]" "CAP 3" "Creando Function App (Python 3.11, plan consumo)..."

az functionapp create `
    --resource-group $RESOURCE_GROUP `
    --consumption-plan-location $LOCATION `
    --runtime python `
    --runtime-version 3.11 `
    --functions-version 4 `
    --name $FUNCTION_APP `
    --storage-account $STORAGE_ACCOUNT `
    --output table

Write-OK "Function App '$FUNCTION_APP' creado."

# =============================================================================
# CAPITULO 4 — Optimizacion de costos: Redis + Presupuesto
# =============================================================================
Write-Step "[CAP 4]" "CAP 4" "Creando Azure Cache for Redis C0 (~10-15 min)..."
Write-Info "Tier Basic C0 = suficiente para cache semantica en el curso."

az redis create `
    --name $REDIS_NAME `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku Basic `
    --vm-size c0 `
    --output table

Write-OK "Redis '$REDIS_NAME' creado."

# ── Presupuesto (puede fallar si la cuenta no tiene permisos de billing) ──────
Write-Step "[CAP 4]" "CAP 4" "Configurando presupuesto con alerta al 80%..."
try {
    az consumption budget create `
        --budget-name "budget-techcorp-llm" `
        --amount 2000 `
        --time-grain Monthly `
        --start-date $START_DATE `
        --end-date $END_DATE `
        --resource-group $RESOURCE_GROUP `
        --threshold 80 `
        --contact-emails "arquitecto@techcorp.com" `
        --output table 2>$null

    Write-OK "Presupuesto configurado: USD 2,000/mes, alerta al 80%."
} catch {
    Write-Warn "El presupuesto requiere permisos de billing."
    Write-Info "Configurarlo manualmente: Portal Azure -> Cost Management -> Budgets."
}

# =============================================================================
# CAPITULO 5 — Azure Front Door (HA y distribucion geografica)
# =============================================================================
Write-Step "[CAP 5]" "CAP 5" "Creando perfil Azure Front Door..."

az afd profile create `
    --profile-name "afd-techcorp" `
    --resource-group $RESOURCE_GROUP `
    --sku Standard_AzureFrontDoor `
    --output table

Write-OK "Azure Front Door 'afd-techcorp' creado."

# =============================================================================
# CAPITULO 6 — Azure AI Search y Cosmos DB
# =============================================================================
Write-Step "[CAP 6]" "CAP 6" "Creando Azure AI Search Standard S1..."
Write-Info "Nombre: $SEARCH_NAME"

az search service create `
    --name $SEARCH_NAME `
    --resource-group $RESOURCE_GROUP `
    --sku Standard `
    --partition-count 1 `
    --replica-count 1 `
    --output table

Write-OK "Azure AI Search '$SEARCH_NAME' creado."

Write-Step "[CAP 6]" "CAP 6" "Creando Azure Cosmos DB (modo serverless)..."
Write-Info "Nombre: $COSMOS_NAME"

az cosmosdb create `
    --name $COSMOS_NAME `
    --resource-group $RESOURCE_GROUP `
    --locations regionName=$LOCATION `
    --capabilities EnableServerless `
    --default-consistency-level Session `
    --output table

Write-OK "Cosmos DB '$COSMOS_NAME' creado."

Write-Info "Creando base de datos 'techcorp-chatbot'..."
az cosmosdb sql database create `
    --account-name $COSMOS_NAME `
    --resource-group $RESOURCE_GROUP `
    --name "techcorp-chatbot" `
    --output table

Write-Info "Creando contenedor 'conversations' (partition key: /session_id)..."
az cosmosdb sql container create `
    --account-name $COSMOS_NAME `
    --resource-group $RESOURCE_GROUP `
    --database-name "techcorp-chatbot" `
    --name "conversations" `
    --partition-key-path "/session_id" `
    --output table

Write-OK "Cosmos DB configurado con DB y contenedor."

# =============================================================================
# RESUMEN FINAL — mostrar todos los recursos y valores para el .env
# =============================================================================
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   APROVISIONAMIENTO COMPLETADO" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Recursos creados en '$RESOURCE_GROUP':" -ForegroundColor Cyan
az resource list `
    --resource-group $RESOURCE_GROUP `
    --query "[].{Nombre:name, Tipo:type}" `
    --output table

# ── Obtener claves y endpoints para el .env ───────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host "   VALORES PARA EL ARCHIVO .env" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host ""

# ACR
$ACR_USER = az acr credential show --name $ACR_NAME --query "username" -o tsv 2>$null
$ACR_PASS = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv 2>$null
Write-Host "# Docker / ACR" -ForegroundColor Gray
Write-Host "ACR_REGISTRY=$ACR_NAME.azurecr.io"
Write-Host "ACR_USERNAME=$ACR_USER"
Write-Host "ACR_PASSWORD=$ACR_PASS"
Write-Host ""

# AI Search
$SEARCH_KEY = az search admin-key show --service-name $SEARCH_NAME --resource-group $RESOURCE_GROUP --query "primaryKey" -o tsv 2>$null
Write-Host "# Azure AI Search" -ForegroundColor Gray
Write-Host "AZURE_SEARCH_ENDPOINT=https://$SEARCH_NAME.search.windows.net"
Write-Host "AZURE_SEARCH_KEY=$SEARCH_KEY"
Write-Host "AZURE_SEARCH_INDEX=knowledge-base"
Write-Host ""

# Cosmos DB
$COSMOS_KEY = az cosmosdb keys list --name $COSMOS_NAME --resource-group $RESOURCE_GROUP --query "primaryMasterKey" -o tsv 2>$null
Write-Host "# Azure Cosmos DB" -ForegroundColor Gray
Write-Host "COSMOS_ENDPOINT=https://$COSMOS_NAME.documents.azure.com:443/"
Write-Host "COSMOS_KEY=$COSMOS_KEY"
Write-Host "COSMOS_DATABASE=techcorp-chatbot"
Write-Host "COSMOS_CONTAINER=conversations"
Write-Host ""

# Redis
$REDIS_KEY = az redis list-keys --name $REDIS_NAME --resource-group $RESOURCE_GROUP --query "primaryKey" -o tsv 2>$null
Write-Host "# Azure Cache for Redis" -ForegroundColor Gray
Write-Host "REDIS_CONNECTION_STRING=$REDIS_NAME.redis.cache.windows.net:6380,password=$REDIS_KEY,ssl=True"
Write-Host ""

# Azure OpenAI (pendiente de crear manualmente — requiere aprobacion de Microsoft)
Write-Host "# Azure OpenAI Service (crear manualmente en el portal)" -ForegroundColor Gray
Write-Host "AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.openai.azure.com/"
Write-Host "AZURE_OPENAI_KEY=<completar-desde-portal>"
Write-Host "AZURE_OPENAI_CHAT_MODEL=gpt-4o"
Write-Host "AZURE_OPENAI_EMBED_MODEL=text-embedding-3-small"
Write-Host ""

Write-Host "================================================================" -ForegroundColor Yellow
Write-Host "   NOTA: Azure OpenAI requiere aprobacion manual de Microsoft."  -ForegroundColor Yellow
Write-Host "   Solicitar en: https://aka.ms/oai/access"                       -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host ""

# ── Guardar resumen en archivo ────────────────────────────────────────────────
$envContent = @"
# ─────────────────────────────────────────────────────────────────
# Generado automaticamente por provision_azure.ps1
# Copiar este bloque al archivo rag-orchestrator/.env
# ─────────────────────────────────────────────────────────────────

ACR_REGISTRY=$ACR_NAME.azurecr.io
ACR_USERNAME=$ACR_USER
ACR_PASSWORD=$ACR_PASS

AZURE_SEARCH_ENDPOINT=https://$SEARCH_NAME.search.windows.net
AZURE_SEARCH_KEY=$SEARCH_KEY
AZURE_SEARCH_INDEX=knowledge-base

COSMOS_ENDPOINT=https://$COSMOS_NAME.documents.azure.com:443/
COSMOS_KEY=$COSMOS_KEY
COSMOS_DATABASE=techcorp-chatbot
COSMOS_CONTAINER=conversations

REDIS_CONNECTION_STRING=$REDIS_NAME.redis.cache.windows.net:6380,password=$REDIS_KEY,ssl=True

AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.openai.azure.com/
AZURE_OPENAI_KEY=<completar-desde-portal>
AZURE_OPENAI_CHAT_MODEL=gpt-4o
AZURE_OPENAI_EMBED_MODEL=text-embedding-3-small

APPLICATIONINSIGHTS_CONNECTION_STRING=<completar-desde-portal>
"@

$envFile = Join-Path $PSScriptRoot "env_generado.txt"
$envContent | Out-File -FilePath $envFile -Encoding utf8
Write-Host "Valores guardados en: $envFile" -ForegroundColor Green
Write-Host ""

# ── Instrucciones finales ─────────────────────────────────────────────────────
Write-Host "PROXIMOS PASOS:" -ForegroundColor Cyan
Write-Host "  1. Copiar el contenido de env_generado.txt al archivo rag-orchestrator/.env"
Write-Host "  2. Completar AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_KEY desde el portal"
Write-Host "  3. Ejecutar: kubectl get nodes   (verificar el cluster AKS)"
Write-Host "  4. Ejecutar: az acr list --output table   (verificar el ACR)"
Write-Host ""
Write-Host "Para ELIMINAR todos los recursos al terminar el curso:" -ForegroundColor Red
Write-Host "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
Write-Host ""
