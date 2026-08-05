#!/bin/bash
# =============================================================
# Setup Local Completo — Sesión 7
# BSG Institute — Diseño de Infraestructura Escalable para LLMs
# =============================================================
# Ejecuta TODO en un solo comando:
#   1. Verifica prerrequisitos
#   2. Crea entorno virtual Python
#   3. Instala dependencias
#   4. Descarga modelo Ollama
#   5. Levanta Docker Compose
#   6. Verifica que todo esté funcionando
#
# Uso:
#   chmod +x scripts/setup-local.sh
#   ./scripts/setup-local.sh
#
# Prerrequisitos (instalar manualmente antes):
#   - Python 3.11+   https://python.org
#   - Docker Desktop https://docker.com
#   - Ollama         https://ollama.ai
#   - k6             https://k6.io/docs/getting-started/installation
# =============================================================

set -euo pipefail

# ── Colores para output legible ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_ok()   { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }
log_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }

echo ""
echo "========================================================"
echo "🤖 BSG Institute — Sesión 7: Setup Local"
echo "   Autoescalado + Pruebas de Carga de Agentes LLM"
echo "========================================================"
echo ""

# ── 1. Verificar prerrequisitos ───────────────────────────────────────────────
log_info "Verificando prerrequisitos..."

# Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    log_err "Python no encontrado. Instalar desde https://python.org"
fi
PYTHON=$(command -v python3 || command -v python)
PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
log_ok "Python $PY_VERSION encontrado"

# Docker
if ! command -v docker &>/dev/null; then
    log_err "Docker no encontrado. Instalar desde https://docker.com"
fi
if ! docker info &>/dev/null 2>&1; then
    log_err "Docker no está corriendo. Iniciar Docker Desktop."
fi
log_ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# Ollama
if ! command -v ollama &>/dev/null; then
    log_warn "Ollama no encontrado. Instalando..."
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        log_err "En Windows, instalar Ollama desde: https://ollama.ai/download"
    fi
fi
log_ok "Ollama $(ollama --version 2>/dev/null || echo 'instalado')"

# k6 (opcional pero recomendado)
if command -v k6 &>/dev/null; then
    log_ok "k6 $(k6 version | head -1)"
else
    log_warn "k6 no encontrado — pruebas de carga no disponibles"
    log_warn "Instalar: https://k6.io/docs/getting-started/installation"
fi

echo ""

# ── 2. Entorno virtual Python ─────────────────────────────────────────────────
log_info "Configurando entorno virtual Python..."

if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    log_ok "Entorno virtual creado"
else
    log_ok "Entorno virtual ya existe"
fi

# Activar según SO
if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
log_ok "Entorno virtual activado"

# ── 3. Instalar dependencias ──────────────────────────────────────────────────
log_info "Instalando dependencias Python..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
log_ok "Dependencias instaladas"

# ── 4. Configurar variables de entorno ────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    log_ok ".env creado desde .env.example"
    log_warn "Revisar .env y completar con tus credenciales cloud (si aplica)"
else
    log_ok ".env ya existe"
fi

# ── 5. Ollama: iniciar y descargar modelo ────────────────────────────────────
log_info "Configurando Ollama..."

# Iniciar Ollama si no está corriendo
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    log_info "Iniciando servidor Ollama..."
    ollama serve &>/dev/null &
    sleep 3
fi

# Verificar si el modelo ya está descargado
if ollama list 2>/dev/null | grep -q "llama3.2:3b"; then
    log_ok "Modelo llama3.2:3b ya descargado"
else
    log_info "Descargando llama3.2:3b (~2GB — puede tardar varios minutos)..."
    ollama pull llama3.2:3b
    log_ok "Modelo llama3.2:3b listo"
fi

echo ""

# ── 6. Docker Compose ────────────────────────────────────────────────────────
log_info "Levantando stack con Docker Compose..."
docker-compose pull -q 2>/dev/null || true
docker-compose up -d

echo ""
log_info "Esperando que los servicios estén listos..."
sleep 10

# ── 7. Verificar servicios ───────────────────────────────────────────────────
log_info "Verificando servicios..."

# API
if curl -sf http://localhost:8000/health &>/dev/null; then
    log_ok "API Gateway: http://localhost:8000"
else
    log_warn "API Gateway no responde aún — puede necesitar más tiempo"
fi

# Ollama
if curl -sf http://localhost:11434/api/tags &>/dev/null; then
    log_ok "Ollama: http://localhost:11434"
fi

# Redis
if docker exec bsg-redis redis-cli ping &>/dev/null 2>&1; then
    log_ok "Redis: corriendo"
fi

# Prometheus
if curl -sf http://localhost:9090/-/healthy &>/dev/null; then
    log_ok "Prometheus: http://localhost:9090"
fi

# Grafana
if curl -sf http://localhost:3000/api/health &>/dev/null; then
    log_ok "Grafana: http://localhost:3000 (admin/admin)"
fi

echo ""
echo "========================================================"
echo "✅ SETUP COMPLETO"
echo ""
echo "📖 API Docs:   http://localhost:8000/docs"
echo "📊 Grafana:    http://localhost:3000 (admin/admin)"
echo "🔭 Prometheus: http://localhost:9090"
echo ""
echo "🤖 Probar el agente:"
echo '   curl -X POST http://localhost:8000/agent/run \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"input": "¿Cuánto es 1234 * 5678?"}'"'"''
echo ""
echo "🔬 Correr smoke test:"
echo "   k6 run loadtesting/k6/smoke-test.js"
echo ""
echo "📋 Ver logs:"
echo "   docker-compose logs -f llm-agent"
echo "========================================================"
