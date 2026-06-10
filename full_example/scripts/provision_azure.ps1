# =============================================================================
# scripts/provision_azure.ps1
# Aprovisionamiento completo del curso — PowerShell (Windows)
# VERSION 3 — corrige errores encontrados en pruebas reales:
#   - Spot node pool: REMOVIDO del aprovisionamiento inicial.
#     Se crea manualmente en el Capitulo 4 como ejercicio de optimizacion.
#     Razon: capacidad spot variable por region; no bloquea el resto del curso.
#   - Redis: az redis retirado -> az redisenterprise con --public-network-access Enabled
#   - Redis: requiere crear la database 'default' en paso separado
#
# Uso:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#   .\scripts\provision_azure.ps1
# =============================================================================

#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────
function New-HexSuffix {
    param([int]$Length = 6)
    $bytes = New-Object byte[] ($Length / 2)
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Write-Step { param([string]$Cap,[string]$Msg) Write-Host "`n[$Cap] $Msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$m) Write-Host "  OK   $m" -ForegroundColor Green }
function Write-Warn { param([string]$m) Write-Host "  WARN $m" -ForegroundColor Yellow }
function Write-Info { param([string]$m) Write-Host "       $m" -ForegroundColor Gray }

# ── Configuracion global ──────────────────────────────────────────────────────
$RESOURCE_GROUP  = "rg-bsg-techcorp-llm"
$LOCATION        = "centralus"
$ACR_NAME        = "acrtechcorp$(New-HexSuffix)"
$AKS_CLUSTER     = "aks-techcorp"
$SEARCH_NAME     = "srch-techcorp$(New-HexSuffix)"
$COSMOS_NAME     = "cosmos-techcorp$(New-HexSuffix)"
$FUNCTION_APP    = "fn-techcorp-summary"
$STORAGE_ACCOUNT = "stgtechcorp$(New-HexSuffix -Length 8)"
$REDIS_NAME      = "redis-techcorp$(New-HexSuffix)"

$TODAY      = Get-Date
$START_DATE = (Get-Date -Year $TODAY.Year -Month $TODAY.Month -Day 1).ToString("yyyy-MM-dd")
$END_DATE   = (Get-Date -Year ($TODAY.Year + 1) -Month $TODAY.Month -Day 1).ToString("yyyy-MM-dd")

# Banner
Write-Host "`n================================================================" -ForegroundColor Blue
Write-Host "   TechCorp LLM - Aprovisionamiento Azure (PowerShell v3)"         -ForegroundColor Blue
Write-Host "================================================================"   -ForegroundColor Blue
Write-Host "   Region : $LOCATION"
Write-Host "   Grupo  : $RESOURCE_GROUP"
Write-Host "================================================================`n" -ForegroundColor Blue

# ── PRE: Registrar resource providers ────────────────────────────────────────
Write-Step "PRE" "Registrando resource providers..."
Write-Info "Esto evita el error MissingSubscriptionRegistration en cuentas nuevas."

@(
    "Microsoft.ContainerRegistry", "Microsoft.ContainerService",
    "Microsoft.Web", "Microsoft.Search", "Microsoft.DocumentDB",
    "Microsoft.Cache", "Microsoft.CognitiveServices",
    "Microsoft.Cdn", "Microsoft.Storage", "Microsoft.Insights",
    "Microsoft.OperationalInsights"
) | ForEach-Object {
    az provider register --namespace $_ | Out-Null
    Write-Info "Registrado: $_"
}

Write-Info "Esperando 30s para que propaguen los registros..."
Start-Sleep -Seconds 30
Write-OK "Providers registrados."

# ── PRE: Verificar login ──────────────────────────────────────────────────────
Write-Step "PRE" "Verificando sesion Azure CLI..."
$account = az account show --query "user.name" -o tsv 2>$null
if (-not $account) {
    az login --use-device-code
    $account = az account show --query "user.name" -o tsv
}
Write-OK "Conectado como: $account"

# =============================================================================
# CAPITULO 1 — Grupo de recursos
# =============================================================================
Write-Step "CAP 1" "Creando grupo de recursos '$RESOURCE_GROUP' en '$LOCATION'..."

az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION `
    --tags proyecto=techcorp-llm curso=infraestructura-llms `
    --output table

Write-OK "Grupo de recursos listo."

# =============================================================================
# CAPITULO 2 — ACR y AKS
# =============================================================================
Write-Step "CAP 2" "Creando Azure Container Registry '$ACR_NAME'..."

az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $ACR_NAME `
    --sku Basic `
    --admin-enabled true `
    --output table

Write-OK "ACR listo: $ACR_NAME.azurecr.io"

# ── AKS ───────────────────────────────────────────────────────────────────────
Write-Step "CAP 2" "Creando cluster AKS '$AKS_CLUSTER' (5-8 min)..."
Write-Info "Nodos: 2 x Standard_D4s_v3 | Autoscaler: 2-8"

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

Write-OK "Cluster AKS listo."

Write-Info "Configurando kubectl..."
az aks get-credentials `
    --resource-group $RESOURCE_GROUP `
    --name $AKS_CLUSTER `
    --overwrite-existing
Write-OK "kubectl configurado. Verifica con: kubectl get nodes"

# ── NOTA spot pool ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  NOTA CAP 4 — Spot Node Pool" -ForegroundColor Yellow
Write-Host "  El spot pool se crea manualmente desde el portal Azure en el Capitulo 4." -ForegroundColor Yellow
Write-Host "  La disponibilidad spot varia por region y tipo de suscripcion." -ForegroundColor Yellow
Write-Host "  Configuracion validada para centralus:" -ForegroundColor Yellow
Write-Host "    Portal: AKS -> Node pools -> Add -> Virtual Machine Scale Set node pool" -ForegroundColor Gray
Write-Host "    Azure Spot instances: Enabled" -ForegroundColor Gray
Write-Host "    Eviction type: Capacity only" -ForegroundColor Gray
Write-Host "    Eviction policy: Delete" -ForegroundColor Gray
Write-Host "    Node size: Standard_D2ls_v5 (eviction rate 0-5%, USD 0.01774/hr)" -ForegroundColor Gray
Write-Host "    Availability zones: None | Mode: User | OS: Ubuntu | Count: 1" -ForegroundColor Gray

# =============================================================================
# CAPITULO 3 — Azure Functions
# =============================================================================
Write-Step "CAP 3" "Creando Storage Account '$STORAGE_ACCOUNT'..."

az storage account create `
    --name $STORAGE_ACCOUNT `
    --resource-group $RESOURCE_GROUP `
    --sku Standard_LRS `
    --output table

Write-OK "Storage Account listo."

Write-Step "CAP 3" "Creando Function App '$FUNCTION_APP' (Python 3.11, plan consumo)..."

az functionapp create `
    --resource-group $RESOURCE_GROUP `
    --consumption-plan-location $LOCATION `
    --runtime python `
    --runtime-version 3.11 `
    --functions-version 4 `
    --os-type Linux `
    --name $FUNCTION_APP `
    --storage-account $STORAGE_ACCOUNT `
    --output table

Write-OK "Function App '$FUNCTION_APP' listo."

# =============================================================================
# CAPITULO 4 — Azure Managed Redis
# FIX v3: az redis retirado -> az redisenterprise
#         Requiere --public-network-access Enabled (API 2025-07-01)
#         Requiere crear la database 'default' en paso separado
# =============================================================================
Write-Step "CAP 4" "Instalando extension redisenterprise en Azure CLI..."
az extension add --name redisenterprise --upgrade --yes 2>$null
Write-OK "Extension redisenterprise lista."

Write-Step "CAP 4" "Creando Azure Managed Redis '$REDIS_NAME' (Balanced_B0, ~10 min)..."
Write-Info "FIX: az redis fue retirado. Usamos az redisenterprise (Azure Managed Redis)."
Write-Info "FIX: --public-network-access Enabled requerido desde API 2025-07-01."

az redisenterprise create `
    --name $REDIS_NAME `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku Balanced_B0 `
    --public-network-access Enabled `
    --output table

Write-OK "Cluster Redis creado. Creando database 'default'..."

az redisenterprise database create `
    --cluster-name $REDIS_NAME `
    --resource-group $RESOURCE_GROUP `
    --client-protocol Encrypted `
    --eviction-policy VolatileLRU `
    --output table

Write-OK "Azure Managed Redis '$REDIS_NAME' listo."

# ── Presupuesto ───────────────────────────────────────────────────────────────
Write-Step "CAP 4" "Configurando presupuesto USD 100/mes con alerta al 80%..."
try {
    az consumption budget create `
        --budget-name "budget-techcorp-llm" `
        --amount 100 `
        --time-grain Monthly `
        --start-date $START_DATE `
        --end-date $END_DATE `
        --resource-group $RESOURCE_GROUP `
        --threshold 80 `
        --contact-emails "arquitecto@techcorp.com" `
        --output table 2>$null
    Write-OK "Presupuesto configurado."
} catch {
    Write-Warn "El presupuesto requiere permisos de billing."
    Write-Info "Configurar manualmente: Portal Azure -> Cost Management -> Budgets -> Add."
}

# =============================================================================
# CAPITULO 5 — Azure Front Door
# =============================================================================
Write-Step "CAP 5" "Creando perfil Azure Front Door 'afd-techcorp'..."

az afd profile create `
    --profile-name "afd-techcorp" `
    --resource-group $RESOURCE_GROUP `
    --sku Standard_AzureFrontDoor `
    --output table

Write-OK "Azure Front Door listo."

# =============================================================================
# CAPITULO 6 — Azure AI Search y Cosmos DB
# =============================================================================
Write-Step "CAP 6" "Creando Azure AI Search '$SEARCH_NAME' (Standard S1)..."

az search service create `
    --name $SEARCH_NAME `
    --resource-group $RESOURCE_GROUP `
    --sku Standard `
    --partition-count 1 `
    --replica-count 1 `
    --output table

Write-OK "Azure AI Search listo."

Write-Step "CAP 6" "Creando Azure Cosmos DB '$COSMOS_NAME' (serverless)..."

az cosmosdb create `
    --name $COSMOS_NAME `
    --resource-group $RESOURCE_GROUP `
    --locations regionName=$LOCATION `
    --capabilities EnableServerless `
    --default-consistency-level Session `
    --output table

az cosmosdb sql database create `
    --account-name $COSMOS_NAME `
    --resource-group $RESOURCE_GROUP `
    --name "techcorp-chatbot" `
    --output table

az cosmosdb sql container create `
    --account-name $COSMOS_NAME `
    --resource-group $RESOURCE_GROUP `
    --database-name "techcorp-chatbot" `
    --name "conversations" `
    --partition-key-path "/session_id" `
    --output table

Write-OK "Cosmos DB listo (DB + contenedor conversations)."

# =============================================================================
# RESUMEN FINAL — obtener claves y generar .env
# =============================================================================
Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "   APROVISIONAMIENTO COMPLETADO" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green

Write-Host "`nRecursos en '$RESOURCE_GROUP':" -ForegroundColor Cyan
az resource list `
    --resource-group $RESOURCE_GROUP `
    --query "[].{Nombre:name, Tipo:type}" `
    --output table

# Obtener claves
Write-Host "`n[Leyendo claves de los servicios...]" -ForegroundColor Gray

$ACR_USER   = az acr credential show --name $ACR_NAME `
                  --query "username" -o tsv 2>$null
$ACR_PASS   = az acr credential show --name $ACR_NAME `
                  --query "passwords[0].value" -o tsv 2>$null

$SEARCH_KEY = az search admin-key show `
                  --service-name $SEARCH_NAME `
                  --resource-group $RESOURCE_GROUP `
                  --query "primaryKey" -o tsv 2>$null

$COSMOS_KEY = az cosmosdb keys list `
                  --name $COSMOS_NAME `
                  --resource-group $RESOURCE_GROUP `
                  --query "primaryMasterKey" -o tsv 2>$null

# Redis Managed: endpoint formato <nombre>.<region>.redis.azure.net:10000
$REDIS_ENDPOINT = "$REDIS_NAME.$LOCATION.redis.azure.net"
try {
    $REDIS_KEY = az redisenterprise database list-keys `
                     --cluster-name $REDIS_NAME `
                     --resource-group $RESOURCE_GROUP `
                     --query "primaryKey" -o tsv 2>$null
} catch {
    $REDIS_KEY = "<obtener desde portal: Redis -> Authentication -> Access keys>"
}

# Construir bloque .env
$envContent = @"
# ─────────────────────────────────────────────────────────────────
# Generado por provision_azure.ps1 v3 — $(Get-Date -Format "yyyy-MM-dd HH:mm")
# Copiar al archivo: rag-orchestrator/.env
# NUNCA subir este archivo a Git (.gitignore ya lo excluye)
# ─────────────────────────────────────────────────────────────────

# Docker / Azure Container Registry
ACR_REGISTRY=$ACR_NAME.azurecr.io
ACR_USERNAME=$ACR_USER
ACR_PASSWORD=$ACR_PASS

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://$SEARCH_NAME.search.windows.net
AZURE_SEARCH_KEY=$SEARCH_KEY
AZURE_SEARCH_INDEX=knowledge-base

# Azure Cosmos DB
COSMOS_ENDPOINT=https://$COSMOS_NAME.documents.azure.com:443/
COSMOS_KEY=$COSMOS_KEY
COSMOS_DATABASE=techcorp-chatbot
COSMOS_CONTAINER=conversations

# Azure Managed Redis (puerto 10000, TLS obligatorio)
REDIS_CONNECTION_STRING=${REDIS_ENDPOINT}:10000,password=$REDIS_KEY,ssl=True,abortConnect=False

# Azure OpenAI Service (crear manualmente en portal — requiere aprobacion Microsoft)
# Solicitar acceso en: https://aka.ms/oai/access
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.openai.azure.com/
AZURE_OPENAI_KEY=<completar-desde-portal>
AZURE_OPENAI_CHAT_MODEL=gpt-4o
AZURE_OPENAI_EMBED_MODEL=text-embedding-3-small

# Azure Monitor / Application Insights (crear en portal)
APPLICATIONINSIGHTS_CONNECTION_STRING=<completar-desde-portal>

# Configuracion de la aplicacion
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
"@

# Mostrar en consola
Write-Host "`n================================================================" -ForegroundColor Yellow
Write-Host "   VALORES PARA rag-orchestrator/.env" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host $envContent

# Guardar en archivo junto al script
$envFile = Join-Path $PSScriptRoot "env_generado.txt"
$envContent | Out-File -FilePath $envFile -Encoding utf8 -Force
Write-Host "`nArchivo guardado en: $envFile" -ForegroundColor Green

# ── Instrucciones finales ─────────────────────────────────────────────────────
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "   PROXIMOS PASOS" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  1. Copiar env_generado.txt -> rag-orchestrator/.env"
Write-Host "  2. Completar AZURE_OPENAI_* y APPLICATIONINSIGHTS_* desde el portal"
Write-Host "  3. kubectl get nodes              # verificar nodos AKS"
Write-Host "  4. az acr list --output table     # verificar ACR"
Write-Host ""
Write-Host "  CAP 4 — Spot pool: crear desde el portal Azure (la disponibilidad spot" -ForegroundColor Yellow
Write-Host "          varia por region — CLI puede fallar con SkuNotAvailable)." -ForegroundColor Yellow
Write-Host "    AKS -> Node pools -> Add -> Virtual Machine Scale Set node pool" -ForegroundColor Gray
Write-Host "    Spot: Enabled | Eviction: Delete | Size: Standard_D2ls_v5 | Mode: User" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para ELIMINAR todos los recursos al terminar el curso:" -ForegroundColor Red
Write-Host "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
Write-Host ""
