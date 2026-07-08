# 📖 Guía de Autoescalado en Kubernetes

## Los 3 tipos de autoescalado en K8s

```
┌─────────────────────────────────────────────────────────────┐
│                    K8s Autoscalers                          │
├──────────────────┬──────────────────┬──────────────────────┤
│       HPA        │       VPA        │   Cluster Autoscaler │
│  (Pods →)        │  (↕ Recursos)    │   (Nodos →)          │
├──────────────────┼──────────────────┼──────────────────────┤
│ Agrega/quita     │ Ajusta CPU/RAM   │ Agrega/quita         │
│ RÉPLICAS         │ de cada pod      │ NODOS (VMs)          │
│                  │                  │                      │
│ Métrica: CPU     │ Recomienda       │ Se activa cuando     │
│ RAM, custom      │ valores óptimos  │ pods no caben        │
│                  │                  │                      │
│ Tiempo: ~30 seg  │ Tiempo: min      │ Tiempo: 5-10 min     │
│                  │ (requiere        │ (Karpenter: 2 min)   │
│                  │  reinicio pod)   │                      │
└──────────────────┴──────────────────┴──────────────────────┘
```

## HPA — HorizontalPodAutoscaler

### Fórmula de escalado

```
deseadas_replicas = ceil(replicas_actuales × (métrica_actual / objetivo))

Ejemplo:
  replicas_actuales = 2
  CPU_actual = 90%
  CPU_objetivo = 70%

  deseadas = ceil(2 × (90/70)) = ceil(2.57) = 3 pods
```

### Flujo de decisión HPA

```
[Metrics Server] → recolecta CPU/RAM cada 15s
       │
       ▼
[HPA Controller] → evalúa cada 15s
       │
       ├── CPU promedio > 70%?  → Escalar ARRIBA ↑
       ├── CPU promedio < 50%?  → Escalar ABAJO ↓ (tras 5 min)
       └── CPU promedio OK?     → Mantener igual
       │
       ▼
[Deployment] → ajusta replicas
       │
       ▼
[Pods nuevos] → readiness probe OK → reciben tráfico
```

### Demo: Ver HPA en acción (Minikube)

```bash
# Terminal 1: Desplegar
minikube start --cpus=4 --memory=8192
minikube addons enable metrics-server
kubectl apply -f kubernetes/local/
kubectl apply -f kubernetes/local/hpa.yaml

# Esperar pods listos
kubectl wait --for=condition=ready pod -l app=llm-gateway -n llm-prod --timeout=120s

# Terminal 2: Monitorear HPA
watch -n 2 kubectl get hpa,pods -n llm-prod

# Terminal 3: Generar carga
k6 run loadtesting/k6/load-test.js

# Lo que verás en Terminal 2:
# NAME               TARGETS    MINPODS  MAXPODS  REPLICAS
# llm-gateway-hpa   15%/70%    2        10       2      ← Sin carga
# llm-gateway-hpa   85%/70%    2        10       4      ← Con carga (escala!)
# llm-gateway-hpa   65%/70%    2        10       4      ← Se estabiliza
# llm-gateway-hpa   20%/70%    2        10       2      ← Baja tras 5 min
```

---

## KEDA — Kubernetes Event-Driven Autoscaling

### ¿Por qué KEDA además de HPA?

| HPA estándar | KEDA |
|-------------|------|
| Mínimo 1 réplica | **Escalar a 0** (save cost!) |
| Solo CPU/RAM | Cualquier métrica externa |
| Solo métricas K8s | HTTP traffic, Redis, queues, Kafka |
| Control plane nativo | Requiere instalación extra |

### KEDA con HTTP traffic (AKS)

```yaml
# KEDA escala a 0 cuando no hay requests
apiVersion: http.keda.sh/v1alpha1
kind: HTTPScaledObject
spec:
  targetPendingRequests: 10  # 1 pod por cada 10 requests pendientes
  replicas:
    min: 0   # Cero pods cuando no hay tráfico
    max: 20  # Hasta 20 pods en pico
```

**Caso de uso perfecto para LLMs:** API usada solo en horario laboral (8h-18h):
- Sin KEDA: 2 pods corriendo 24/7 = 720 pod-hours/mes
- Con KEDA: ~330 pod-hours/mes (scale to 0 de 18h a 8h) = **54% de ahorro**

---

## Comparativa Cloud: HPA en AKS vs GKE vs EKS

| Característica | AKS | GKE | EKS |
|----------------|-----|-----|-----|
| **HPA básico** | ✅ Nativo | ✅ Nativo | ✅ Nativo |
| **Metrics Server** | Addon | Pre-instalado | Manual |
| **Cluster Autoscaler** | ✅ Integrado | ✅ Integrado | Addon |
| **KEDA** | ✅ Addon oficial | Community | Community |
| **VPA** | Community | ✅ Integrado | Community |
| **Scale to zero** | KEDA | KEDA / GKE Autopilot | Karpenter |
| **Node provisioning** | CA / NAP | Autopilot | CA / Karpenter |
| **Velocidad scale-up** | ~5 min | Autopilot: ~2 min | Karpenter: <2 min |

### GKE Autopilot — K8s serverless para nodos

```bash
# En GKE Autopilot, no gestionas nodos:
# - No hay nodeGroups que configurar
# - Pagas por pod (CPU + RAM solicitados), no por nodo
# - Los nodos escalan automáticamente en <2 minutos
# - VPA pre-instalado y recomendaciones automáticas

gcloud container clusters create-auto mi-cluster --region us-central1
# Eso es todo — K8s completamente gestionado
```

### Karpenter en EKS — Provisionador de nodos ultra-rápido

```yaml
# Karpenter elige el tipo de instancia óptimo automáticamente
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]  # Prefiere spot (90% más barato)
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["t3.medium", "t3.large", "m5.large"]  # Varios tipos
  limits:
    cpu: "100"                            # Máximo 100 vCPU en el pool
  disruption:
    consolidationPolicy: WhenUnderutilized  # Consolida pods para usar menos nodos
```

---

## Troubleshooting: HPA no escala

### Problema 1: `<unknown>` en TARGETS

```bash
kubectl get hpa -n llm-prod
# NAME    TARGETS         MINPODS  MAXPODS  REPLICAS  AGE
# hpa     <unknown>/70%   2        10       2         5m

# Causa: Metrics Server no instalado o pods sin resource requests
# Solución:
minikube addons enable metrics-server
# O verificar que el Deployment tiene resources.requests.cpu definido
```

### Problema 2: HPA no reduce pods

```bash
# Normal — HPA espera 5 minutos por defecto antes de escalar abajo
# Ver el cooldown en el campo scaleDown.stabilizationWindowSeconds

# Forzar reducción (solo en desarrollo):
kubectl scale deployment llm-gateway --replicas=2 -n llm-prod
```

### Problema 3: Pods en Pending (no suficientes recursos en nodos)

```bash
kubectl describe pod <pod-name> -n llm-prod
# Eventos: "Insufficient cpu" o "Insufficient memory"

# Solución: Cluster Autoscaler agregará nodos automáticamente
# O reducir resources.requests en el Deployment
```
