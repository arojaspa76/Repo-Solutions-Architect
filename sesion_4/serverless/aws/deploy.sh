#!/bin/bash
# =============================================================
# Deploy AWS Lambda — LLM Summarizer (via AWS SAM)
# BSG Institute — Sesión 4
# =============================================================
# Prerrequisitos:
#   - AWS CLI configurado: aws configure
#   - SAM CLI: pip install aws-sam-cli
#   - S3 bucket para artifacts (se crea automáticamente)
# =============================================================

set -euo pipefail

STACK_NAME="bsg-llm-session4"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BUCKET="bsg-sam-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 000000000000)"

echo "=================================================="
echo "🟠 Deploy AWS Lambda — LLM Summarizer"
echo "   Stack:   $STACK_NAME"
echo "   Región:  $REGION"
echo "   Bucket:  $S3_BUCKET"
echo "=================================================="

echo ""
echo "✅ Verificando credenciales AWS..."
aws sts get-caller-identity --query "{Account:Account,User:Arn}" --output table

# Crear bucket S3 si no existe
echo ""
echo "💾 Verificando bucket S3 para artifacts..."
aws s3 mb "s3://$S3_BUCKET" --region "$REGION" 2>/dev/null || echo "Bucket ya existe"

# Build
echo ""
echo "🔨 Compilando con SAM..."
sam build

# Deploy
echo ""
echo "🚀 Desplegando con SAM..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides "BedrockModelId=anthropic.claude-3-5-sonnet-20241022-v2:0"

# Obtener URL
FUNCTION_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='LLMApiUrl'].OutputValue" \
    --output text 2>/dev/null || echo "Ver outputs en CloudFormation")

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
echo "     -d '{\"text\": \"Kubernetes es un orquestador...\", \"language\": \"es\"}'"
echo ""
echo "🔍 Ver logs:"
echo "   sam logs -n LLMFunction --stack-name $STACK_NAME --tail"
echo ""
echo "💰 Monitoreo costos:"
echo "   AWS Console → Cost Explorer → Service: Lambda"
echo "=================================================="

echo "AWS_FUNCTION_URL=$FUNCTION_URL" >> ../../.env.outputs
