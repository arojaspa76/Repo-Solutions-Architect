#!/bin/bash
# ============================================================
# deploy-aws.sh — Despliegue en Amazon Web Services
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================
#
# Este script despliega la LLM Gateway API en AWS usando:
# 1. ECR (Elastic Container Registry) — almacena la imagen
# 2. ECS Fargate — ejecuta el contenedor (serverless)
#
# Pre-requisitos:
#   - AWS CLI v2: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
#   - Docker instalado
#   - aws configure (con credenciales válidas)
#
# Uso:
#   chmod +x docker/deploy-aws.sh
#   ./docker/deploy-aws.sh
# ============================================================

set -euo pipefail

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Configuración ─────────────────────────────────────────────────────────────
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPO="llm-session3/llm-gateway"
IMAGE_TAG="latest"
FULL_IMAGE="${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"
CLUSTER_NAME="llm-session3-cluster"
SERVICE_NAME="llm-gateway-service"
TASK_FAMILY="llm-gateway-task"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   🚀 DESPLIEGUE LLM GATEWAY → AMAZON WEB SERVICES    ║"
echo "║   BSG Institute — Sesión 3                            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── Verificaciones ────────────────────────────────────────────────────────────
[ -z "$AWS_ACCOUNT_ID" ] && log_error "No hay credenciales AWS. Ejecutar: aws configure"
command -v aws &>/dev/null || log_error "AWS CLI no instalado"
log_success "Cuenta AWS: $AWS_ACCOUNT_ID en $AWS_REGION"

# ── Paso 1: Crear repositorio ECR ────────────────────────────────────────────
log_info "Creando repositorio ECR: $ECR_REPO..."
aws ecr create-repository \
    --repository-name "$ECR_REPO" \
    --region "$AWS_REGION" \
    --image-scanning-configuration scanOnPush=true \
    --output none 2>/dev/null || log_info "El repositorio ya existe, continuando..."
log_success "ECR listo: ${ECR_REGISTRY}/${ECR_REPO}"

# ── Paso 2: Autenticar Docker con ECR ────────────────────────────────────────
log_info "Autenticando Docker con ECR..."
aws ecr get-login-password \
    --region "$AWS_REGION" | \
    docker login \
        --username AWS \
        --password-stdin "$ECR_REGISTRY"
log_success "Docker autenticado con ECR"

# ── Paso 3: Build y Push de la imagen ────────────────────────────────────────
log_info "Construyendo imagen Docker..."
docker build -t "${ECR_REPO}:${IMAGE_TAG}" -f docker/Dockerfile .
log_success "Imagen construida localmente"

log_info "Tageando imagen para ECR..."
docker tag "${ECR_REPO}:${IMAGE_TAG}" "$FULL_IMAGE"

log_info "Publicando imagen en ECR (puede tardar varios minutos)..."
docker push "$FULL_IMAGE"
log_success "Imagen publicada: $FULL_IMAGE"

# ── Paso 4: Crear cluster ECS ────────────────────────────────────────────────
log_info "Creando cluster ECS Fargate: $CLUSTER_NAME..."
aws ecs create-cluster \
    --cluster-name "$CLUSTER_NAME" \
    --capacity-providers FARGATE \
    --region "$AWS_REGION" \
    --output none 2>/dev/null || true
log_success "Cluster ECS listo"

# ── Paso 5: Registrar Task Definition ────────────────────────────────────────
log_info "Registrando Task Definition..."

# Crear archivo de task definition
cat > /tmp/task-definition.json << EOF
{
    "family": "${TASK_FAMILY}",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "containerDefinitions": [
        {
            "name": "llm-gateway",
            "image": "${FULL_IMAGE}",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "ENVIRONMENT", "value": "production"},
                {"name": "LOG_LEVEL", "value": "INFO"}
            ],
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 10,
                "retries": 3,
                "startPeriod": 30
            },
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/${TASK_FAMILY}",
                    "awslogs-region": "${AWS_REGION}",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF

# Crear log group
aws logs create-log-group \
    --log-group-name "/ecs/${TASK_FAMILY}" \
    --region "$AWS_REGION" \
    --output none 2>/dev/null || true

# Registrar task definition
TASK_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/task-definition.json \
    --region "$AWS_REGION" \
    --query "taskDefinition.taskDefinitionArn" \
    --output text)
log_success "Task Definition registrada: $TASK_ARN"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ PREPARACIÓN COMPLETADA                           ║"
echo "╠═══════════════════════════════════════════════════════╣"
echo "║   Imagen en ECR: $FULL_IMAGE"
echo "║   Task Definition: $TASK_ARN"
echo "║"
echo "║   SIGUIENTE PASO (manual en AWS Console):"
echo "║   1. Ir a ECS > Clusters > $CLUSTER_NAME"
echo "║   2. Crear Service con la Task Definition"
echo "║   3. Configurar ALB (Application Load Balancer)"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
log_info "Documentación completa: docs/KUBERNETES_GUIDE.md"
