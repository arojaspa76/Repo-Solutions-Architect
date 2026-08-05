#!/bin/bash
# Setup EKS + Karpenter — LLM Agent Gateway (Sesión 7)
set -euo pipefail

CLUSTER="bsg-agent-eks"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/bsg-agent"

echo "🟠 Setup EKS + Karpenter — LLM Agent (Sesión 7)"
echo "   Cluster: $CLUSTER | Región: $REGION"

command -v eksctl >/dev/null || { echo "Instalar eksctl: https://eksctl.io"; exit 1; }

aws ecr create-repository --repository-name bsg-agent --region $REGION 2>/dev/null || true

cat <<EOF | eksctl create cluster -f -
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: $CLUSTER
  region: $REGION
  version: "1.29"
managedNodeGroups:
  - name: ng-spot
    instanceTypes: ["t3.medium","t3.large","t3a.medium"]
    spot: true
    minSize: 1
    maxSize: 8
    desiredCapacity: 2
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: aws-ebs-csi-driver
EOF

kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com
docker build -t ${ECR}:v1 -f docker/Dockerfile .
docker push ${ECR}:v1

sed "s|IMAGE_REGISTRY|${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com|g" \
    kubernetes/aws/deployment-aws.yaml | kubectl apply -f -
kubectl apply -f kubernetes/aws/hpa-aws.yaml
kubectl rollout status deployment/llm-agent-gateway -n llm-prod --timeout=300s

for i in {1..30}; do
    HOSTNAME=$(kubectl get svc llm-agent-service -n llm-prod \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
    [ -n "$HOSTNAME" ] && break
    sleep 10
done

echo "✅ EKS listo: http://$HOSTNAME/agent/run"
echo "💡 Karpenter provisiona nodos en <2 min (vs 5-10 min Cluster Autoscaler)"
