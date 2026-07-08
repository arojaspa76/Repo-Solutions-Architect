#!/bin/bash
# =============================================================
# Deploy Google Cloud Function gen2 — LLM Summarizer
# BSG Institute — Sesión 4
# =============================================================
# Prerrequisitos:
#   - gcloud CLI autenticado: gcloud auth login
#   - Proyecto GCP configurado: gcloud config set project TU_PROYECTO
# =============================================================

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="${GCP_REGION:-us-central1}"
FUNCTION_NAME="bsg-llm-summarize"
RUNTIME="python312"
MEMORY="512MB"      # Aumentar a 2048MB si se usa un modelo local grande
TIMEOUT="300s"

echo "=================================================="
echo "🟡 Deploy Google Cloud Function gen2"
echo "   Proyecto:  $PROJECT_ID"
echo "   Función:   $FUNCTION_NAME"
echo "   Región:    $REGION"
echo "   Runtime:   $RUNTIME"
echo "=================================================="

# Habilitar APIs necesarias
echo ""
echo "⚙️  Habilitando APIs GCP..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    --quiet
echo "✅ APIs habilitadas"

# Deploy
echo ""
echo "🚀 Desplegando Cloud Function gen2..."
gcloud functions deploy "$FUNCTION_NAME" \
    --gen2 \
    --runtime="$RUNTIME" \
    --region="$REGION" \
    --source=. \
    --entry-point=llm_summarize \
    --trigger-http \
    --allow-unauthenticated \
    --memory="$MEMORY" \
    --timeout="$TIMEOUT" \
    --min-instances=0 \
    --max-instances=100 \
    --set-env-vars="USE_OLLAMA=false,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GCP_REGION=${REGION},VERTEX_AI_MODEL=gemini-1.5-flash" \
    --quiet

# Obtener URL
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
    --region="$REGION" \
    --gen2 \
    --format="value(serviceConfig.uri)" 2>/dev/null || \
    echo "https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}")

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
echo "🔍 Ver logs:"
echo "   gcloud functions logs read $FUNCTION_NAME --region=$REGION --gen2 --limit=50"
echo "=================================================="

echo "GCP_FUNCTION_URL=$FUNCTION_URL" >> ../../.env.outputs
