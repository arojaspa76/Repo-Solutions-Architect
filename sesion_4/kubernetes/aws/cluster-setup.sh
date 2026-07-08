#!/bin/bash
# =============================================================
# Setup EKS + Karpenter + HPA — Sesión 4
# BSG Institute — Alta Disponibilidad para LLMs
# =============================================================
# Karpenter (AWS): escalador de NODOS más rápido que Cluster Autoscaler
#   - Provisiona nodos en <2 minutos (vs 5-10 min de CA)
#   - Escoge el tipo de instancia óptimo por costo/capacidad
#   - Consolida pods en menos nodos (reduce costo hasta 50%)
# =============================================================

set -euo pipefail

CLUSTER="bsg-llm-eks"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/bsg-llm"

echo "=================================================="
echo "🟠 Setup EKS + Karpenter + HPA — Sesión 4"
echo "   Cluster: $CLUSTER"
echo "   Región:  $REGION"
echo "   Account: $ACCOUNT"
echo "=================================================="

# Verificar herramientas
command -v eksctl >/dev/null || { echo "Instalar eksctl: https://eksctl.io"; exit 1; }
command -v kubectl >/dev/null || { echo "Instalar kubectl"; exit 1; }

# ECR Repository
echo "📦 Creando ECR repository..."
aws ecr create-repository --repository-name bsg-llm --region $REGION 2>/dev/null || true

# Cluster EKS
echo "⚙️  Creando clúster EKS con eksctl..."
cat <<EOF | eksctl create cluster -f -
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: $CLUSTER
  region: $REGION
  version: "1.29"
managedNodeGroups:
  - name: ng-spot
    instanceTypes: ["t3.medium", "t3.large", "t3a.medium"]
    spot: true                  # Instancias spot: hasta 90% más baratas
    minSize: 1
    maxSize: 10
    desiredCapacity: 2
    labels:
      role: worker
    tags:
      Project: bsg-session4
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: aws-ebs-csi-driver
EOF

echo "✅ EKS creado"

# Instalar Metrics Server (requerido para HPA)
echo "📊 Instalando Metrics Server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Instalar Karpenter
echo "⚡ Instalando Karpenter..."
export KARPENTER_VERSION="1.0.0"
helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
    --version "$KARPENTER_VERSION" \
    --namespace kube-system \
    --set settings.clusterName=$CLUSTER \
    --set settings.interruptionQueue=$CLUSTER \
    --wait 2>/dev/null || echo "Karpenter ya instalado"

# Build y push imagen
echo ""
echo "🐳 Build y push a ECR..."
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com
docker build -t ${ECR_REPO}:v1 -f ../../docker/Dockerfile ../..
docker push ${ECR_REPO}:v1

# Deploy
echo ""
echo "🚀 Desplegando en EKS..."
sed "s|REGISTRY|${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com|g" deployment-aws.yaml | kubectl apply -f -
kubectl apply -f hpa-aws.yaml

kubectl rollout status deployment/llm-gateway -n llm-prod --timeout=300s

# External hostname
for i in {1..30}; do
    HOSTNAME=$(kubectl get svc llm-gateway-service -n llm-prod \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    [ -n "$HOSTNAME" ] && break
    sleep 10
done

echo ""
echo "=================================================="
echo "✅ EKS LISTO"
echo "🌐 API: http://$HOSTNAME"
echo ""
echo "💡 Karpenter vs Cluster Autoscaler:"
echo "   CA: reemplaza nodos en 5-10 min"
echo "   Karpenter: provisiona nodos en <2 min"
echo ""
echo "📊 Ver nodos provisionados por Karpenter:"
echo "   kubectl get nodes -l karpenter.sh/provisioner-name=default"
echo "=================================================="
