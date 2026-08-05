# 📖 Guía de Autoescalado K8s — Sesión 7

## Los 3 niveles de autoescalado

```
┌──────────────────────────────────────────────────────────────┐
│  NIVEL 1: HPA / KEDA  →  escala PODS (réplicas de tu app)   │
│  NIVEL 2: VPA         →  escala CPU/RAM de cada pod          │
│  NIVEL 3: CAS/Karpenter → escala NODOS (VMs del clúster)    │
└──────────────────────────────────────────────────────────────┘
```

Los 3 trabajan juntos: HPA pide más pods → K8s los ubica en nodos → si no hay espacio, CAS/Karpenter crea nodos.

---

## HPA — Fórmula y configuración

```
replicas_deseadas = ceil(replicas_actuales × métrica_actual / objetivo)

Ejemplo con el agente LLM:
  replicas_actuales = 2
  CPU_actual = 75%
  CPU_objetivo = 60%   ← más bajo que APIs simples (agente consume más)

  replicas = ceil(2 × 75/60) = ceil(2.5) = 3 pods
```

### ¿Por qué 60% de CPU para el agente y no 70%?

El agente hace múltiples llamadas al LLM por request (pasos ReAct). Cada llamada consume CPU para procesar la respuesta, tokenizar el texto, y ejecutar las herramientas. Si esperas al 70%, el sistema ya está saturado antes de que el HPA reaccione.

### Configurar HPA

```bash
# Aplicar HPA local
kubectl apply -f kubernetes/local/hpa.yaml

# Ver estado en tiempo real
watch -n 2 kubectl get hpa -n llm-prod

# Descripción detallada con eventos
kubectl describe hpa llm-agent-hpa -n llm-prod

# Forzar escalado manual (para demos)
kubectl scale deployment llm-agent-gateway --replicas=5 -n llm-prod
```

### Cooldown de scale-down

El HPA espera **5 minutos** antes de reducir réplicas. Esto evita el "flapping" (escalar arriba y abajo continuamente). Configurado en `stabilizationWindowSeconds: 300`.

---

## KEDA — Scale to Zero

KEDA extiende el HPA para llegar a **0 pods** cuando no hay tráfico.

### ¿Cuándo usar KEDA vs HPA puro?

| Situación | Usar |
|-----------|------|
| Tráfico 24/7 relativamente estable | HPA |
| Tráfico solo en horario laboral | KEDA |
| Procesar colas/eventos | KEDA |
| Costo es prioridad | KEDA |

### Instalación de KEDA

```bash
# Helm
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace

# HTTP Add-on (para escalar por tráfico HTTP)
helm install http-add-on kedacore/keda-add-ons-http \
    --namespace keda

# Verificar
kubectl get pods -n keda
```

### Ejemplo de ahorro con KEDA

Agente LLM usado solo en horario laboral (8h–18h, L–V):

```
Sin KEDA:
  2 pods × 24h × 30 días = 1,440 pod-hours/mes

Con KEDA (scale to zero de noche y fin de semana):
  2 pods × 10h × 22 días = 440 pod-hours/mes

Ahorro: ~69% del costo de cómputo
```

---

## Comparativa por Cloud

### Azure AKS

```bash
# Crear cluster con KEDA habilitado
az aks create \
    --name mi-cluster \
    --resource-group mi-rg \
    --enable-keda \
    --enable-cluster-autoscaler \
    --min-count 1 --max-count 5

# Ver KEDA ScaledObjects
kubectl get scaledobject -n llm-prod
kubectl get httpscaledobject -n llm-prod
```

**Ventaja:** KEDA es un addon oficial — soporte nativo de Microsoft.

### GKE Autopilot

```bash
# Crear cluster Autopilot (nodos gestionados automáticamente)
gcloud container clusters create-auto mi-cluster \
    --region us-central1

# VPA viene pre-instalado
kubectl describe vpa llm-agent-vpa -n llm-prod
```

**Ventaja:** No gestionas nodos. Pagas por pods. GKE provisiona nodos en <2 min.

### EKS + Karpenter

```bash
# Ver nodos provisionados por Karpenter
kubectl get nodes -l karpenter.sh/provisioner-name=llm-agent-pool

# Ver decisiones de Karpenter
kubectl logs -n kube-system \
    -l app.kubernetes.io/name=karpenter -f | grep -i "launching\|terminating"

# Ver consolidación (Karpenter moviendo pods para usar menos nodos)
kubectl get events -n llm-prod | grep -i karpenter
```

**Ventaja:** Karpenter escala nodos en <2 min (vs 5-10 min de Cluster Autoscaler) y elige automáticamente el tipo de instancia más barato (spot).

---

## Troubleshooting Común

### HPA muestra `<unknown>` en TARGETS

```bash
# Causa: Metrics Server no instalado
minikube addons enable metrics-server

# O verificar que el Deployment tiene resources.requests definidos
kubectl describe deployment llm-agent-gateway -n llm-prod | grep -A5 "Requests:"
```

### HPA no escala hacia arriba

```bash
# Ver eventos y razón
kubectl describe hpa llm-agent-hpa -n llm-prod | grep -A20 "Events:"

# Causa común: pods en Pending por falta de recursos en nodos
kubectl get pods -n llm-prod | grep Pending
kubectl describe pod <pod-pending> -n llm-prod | grep -A10 "Events:"
```

### Pods en estado Pending

```bash
# Ver qué le pasa al pod
kubectl describe pod <nombre-pod> -n llm-prod

# Si dice "Insufficient cpu/memory" → CAS/Karpenter debe crear nodo
# Verificar que CAS está habilitado:
kubectl get pods -n kube-system | grep cluster-autoscaler
```

### KEDA no escala a 0

```bash
# Verificar ScaledObject
kubectl get scaledobject llm-agent-http-scaler -n llm-prod -o yaml

# Ver logs KEDA
kubectl logs -n keda -l app=keda-operator -f
```
