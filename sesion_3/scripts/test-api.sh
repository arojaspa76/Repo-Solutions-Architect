#!/bin/bash
# ============================================================
# test-api.sh — Pruebas rápidas de la API
# Sesión 3: BSG Institute
# ============================================================
# Uso: chmod +x scripts/test-api.sh && ./scripts/test-api.sh

BASE_URL="${API_URL:-http://localhost:8000}"
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║  🧪 PRUEBAS DE LA LLM GATEWAY API    ║"
echo "║  BSG Institute — Sesión 3             ║"
echo "╚═══════════════════════════════════════╝"
echo -e "  URL: ${BLUE}${BASE_URL}${NC}"
echo ""

pass=0; fail=0

check() {
    local name=$1; local url=$2; local method=${3:-GET}; local data=$4
    echo -n "  ▶ $name... "
    if [ "$method" = "POST" ]; then
        HTTP_CODE=$(curl -s -o /tmp/api_resp.json -w "%{http_code}" \
            -X POST "$url" -H "Content-Type: application/json" -d "$data")
    else
        HTTP_CODE=$(curl -s -o /tmp/api_resp.json -w "%{http_code}" "$url")
    fi
    if [[ "$HTTP_CODE" -ge 200 && "$HTTP_CODE" -lt 300 ]]; then
        echo -e "${GREEN}✅ OK ($HTTP_CODE)${NC}"
        ((pass++))
    else
        echo -e "\033[0;31m❌ FAIL ($HTTP_CODE)${NC}"
        cat /tmp/api_resp.json 2>/dev/null | head -3
        ((fail++))
    fi
}

check "Root endpoint"  "$BASE_URL/"
check "Health check"   "$BASE_URL/health"
check "List models"    "$BASE_URL/models"
check "Chat básico"    "$BASE_URL/chat" "POST" \
    '{"message":"Hola, di una sola palabra","model":"llama3.2:3b","max_tokens":10}'
check "Chat con system prompt" "$BASE_URL/chat" "POST" \
    '{"message":"¿Qué es Docker?","model":"llama3.2:3b","system_prompt":"Responde en máximo 10 palabras."}'
check "Embeddings"     "$BASE_URL/embeddings" "POST" \
    '{"text":"Kubernetes orquesta contenedores Docker","model":"llama3.2:3b"}'
check "Docs Swagger"   "$BASE_URL/docs"
check "OpenAPI JSON"   "$BASE_URL/openapi.json"

echo ""
echo "────────────────────────────────────────"
echo -e "  Resultado: ${GREEN}$pass pasados${NC} | \033[0;31m$fail fallados\033[0m"
echo ""
[ $fail -gt 0 ] && echo "  💡 Si fallan los tests de chat/embeddings, verifica que Ollama esté corriendo:" && \
    echo "     ollama serve" && echo "     ollama pull llama3.2:3b"
echo ""
