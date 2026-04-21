# Guía Paso a Paso – Despliegue de una Solución LLM en Microsoft Azure
## AKS + ACR + Azure OpenAI + Azure AI Search

**Formato:** Word (docx) | **Nivel:** Arquitecto / Maestría

Esta guía detalla las acciones exactas en Portal y CLI, con explicaciones, código y buenas prácticas.

---

## 0) Pre-flight Checklist

1. Verifica suscripción y permisos (`Owner` / `Contributor`) en Azure Portal.
2. Confirma acceso a Azure OpenAI en una región disponible (East US, Sweden Central, etc.).
3. Herramientas locales: Azure CLI (`>=2.60`), `kubectl`, Docker, Git.
4. Inicia sesión en CLI:

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID_OR_NAME>"
```

---

## 1) Crear Resource Group y Red (VNet + Subnets)

**Portal:** Resource groups → Create → Name: `llm-rg` | Region: `East US`

**CLI equivalente:**

```bash
az group create -n llm-rg -l eastus

az network vnet create \
  -g llm-rg -n llm-vnet \
  --address-prefixes 10.10.0.0/16 \
  --subnet-name aks-subnet \
  --subnet-prefix 10.10.1.0/24

az network vnet subnet create \
  -g llm-rg --vnet-name llm-vnet \
  -n pe-subnet \
  --address-prefix 10.10.2.0/24
```

---

## 2) Key Vault y Managed Identity (RBAC)

Crear Key Vault y una Managed Identity para evitar exponer llaves:

```bash
az keyvault create \
  -g llm-rg -n llm-kv-001 -l eastus \
  --enable-rbac-authorization true

az identity create -g llm-rg -n llm-mi-aks

# Conceder rol para leer secretos
az role assignment create \
  --assignee $(az identity show -g llm-rg -n llm-mi-aks --query principalId -o tsv) \
  --role "Key Vault Secrets User" \
  --scope $(az keyvault show -g llm-rg -n llm-kv-001 --query id -o tsv)
```

---

## 3) Azure AI Search (Vector Search)

**Portal:** Create a resource → Azure AI Search → Name: `llm-search-001` → Pricing tier: `Standard` o superior.

**Networking:** Private endpoint (recomendado) → Subnet: `pe-subnet` (opcional).

**Crear índice vectorial** (ejemplo JSON, 1536 dimensiones):

```json
{
  "name": "docs-index",
  "fields": [
    {"name": "id",            "type": "Edm.String",                 "key": true,  "filterable": true},
    {"name": "content",       "type": "Edm.String",                 "searchable": true},
    {"name": "metadata",      "type": "Edm.String",                 "searchable": true, "filterable": true},
    {
      "name": "contentVector",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "vectorSearchDimensions": 1536,
      "vectorSearchProfile": "vector-profile"
    }
  ],
  "vectorSearch": {
    "profiles":    [{"name": "vector-profile", "algorithmConfiguration": "hnsw-config"}],
    "algorithms":  [{"name": "hnsw-config",    "kind": "hnsw"}]
  }
}
```

---

## 4) Azure OpenAI – Crear Recurso y Deployments

**Portal:** Create a resource → Azure OpenAI → Name: `llm-aoai-001` → Region (igual a los demás).

**Networking:** Private endpoint (opcional recomendado).

Abrir **Azure AI Studio** → Deployments → Create new deployment:

| Propósito   | Modelo                  |
|-------------|-------------------------|
| Chat        | `gpt-4o`                |
| Embeddings  | `text-embedding-3-small`|

> Guarda el **Endpoint URL** y los **Deployment Name(s)** para usarlos más adelante.

---

## 5) Azure Container Registry (ACR) y Push de Imagen

Crear registro, construir y subir imagen Docker:

```bash
az acr create -g llm-rg -n llmacr001 --sku Basic
az acr login -n llmacr001
```

**Dockerfile** (FastAPI + Azure SDKs):

```dockerfile
FROM python:3.10-slim
WORKDIR /app
RUN pip install fastapi uvicorn azure-identity azure-search-documents openai
COPY app.py .
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**`app.py`** (FastAPI – demo simplificado):

> ⚠️ **Correcciones aplicadas:**
> - `SearchClient` requiere `AzureKeyCredential`, no un string directo.
> - La API de búsqueda vectorial usa `VectorizedQuery` (SDK `>=11.4`), no el dict `vector={}` obsoleto.

```python
import os
from fastapi import FastAPI
from pydantic import BaseModel
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

app = FastAPI()

AOAI_ENDPOINT   = os.getenv("AOAI_ENDPOINT")
AOAI_DEPLOYMENT = os.getenv("AOAI_DEPLOYMENT")
AOAI_KEY        = os.getenv("AOAI_KEY")
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
SEARCH_INDEX    = os.getenv("SEARCH_INDEX", "docs-index")
SEARCH_KEY      = os.getenv("SEARCH_KEY")

aoai_client = AzureOpenAI(
    api_key=AOAI_KEY,
    api_version="2024-06-01",
    azure_endpoint=AOAI_ENDPOINT
)

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_KEY)   # ← requiere AzureKeyCredential
)

class Query(BaseModel):
    q: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(q: Query):
    # En producción: genera el embedding de q.q con el deployment de embeddings
    dummy_vector = [0.0] * 1536
    vector_query = VectorizedQuery(
        vector=dummy_vector,
        k_nearest_neighbors=3,
        fields="contentVector"
    )
    results = search_client.search(search_text=None, vector_queries=[vector_query])
    context = "\n".join([r["content"] for r in results])

    resp = aoai_client.chat.completions.create(
        model=AOAI_DEPLOYMENT,
        messages=[{"role": "user", "content": f"Contexto:\n{context}\nPregunta:\n{q.q}"}]
    )
    return {"answer": resp.choices[0].message.content}
```

**Build & Push:**

```bash
docker build -t llmacr001.azurecr.io/llmapi:latest .
docker push llmacr001.azurecr.io/llmapi:latest
```

---

## 6) AKS – Crear Clúster y Conectar ACR

> ⚠️ **Corrección aplicada:** Se agrega `--assign-identity` para asociar la Managed Identity creada en el paso 2 al clúster desde el inicio.

```bash
MI_ID=$(az identity show -g llm-rg -n llm-mi-aks --query id -o tsv)

az aks create \
  -g llm-rg -n llm-aks \
  --node-count 2 \
  --enable-addons monitoring \
  --attach-acr llmacr001 \
  --network-plugin azure \
  --assign-identity "$MI_ID"

az aks get-credentials -g llm-rg -n llm-aks
kubectl get nodes
```

---

## 7) Secretos (Kubernetes Secrets – atajo inicial)

> Para producción usa Key Vault CSI (ver Apéndice A). Aquí un atajo inicial:

```bash
kubectl create secret generic app-secrets \
  --from-literal=AOAI_ENDPOINT="https://<tu-aoai>.openai.azure.com/" \
  --from-literal=AOAI_DEPLOYMENT="gpt4o-deploy" \
  --from-literal=AOAI_KEY="<tu_api_key>" \
  --from-literal=SEARCH_ENDPOINT="https://llm-search-001.search.windows.net" \
  --from-literal=SEARCH_KEY="<tu_search_key>"
```

---

## 8) Despliegue (Deployment + Service)

Crea `deployment.yaml` con 2 réplicas y expone un Service interno:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llmapi
spec:
  replicas: 2
  selector:
    matchLabels: { app: llmapi }
  template:
    metadata:
      labels: { app: llmapi }
    spec:
      containers:
      - name: llmapi
        image: llmacr001.azurecr.io/llmapi:latest
        ports:
        - containerPort: 8080
        envFrom:
        - secretRef: { name: app-secrets }
---
apiVersion: v1
kind: Service
metadata:
  name: llmapi-svc
spec:
  selector: { app: llmapi }
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

```bash
kubectl apply -f deployment.yaml
kubectl get pods
```

---

## 9) Ingress (NGINX) – Exponer Públicamente

Instala Ingress NGINX con Helm y crea `ingress.yaml`:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace
```

**`ingress.yaml`:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llmapi-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: llmapi-svc
            port:
              number: 80
```

```bash
kubectl apply -f ingress.yaml
kubectl get svc -n ingress-nginx
```

---

## 10) Private Endpoints (Opcional Recomendado)

Para Azure OpenAI y Azure AI Search:

**Portal:** Resource → Networking → Private endpoint → +Add → VNet: `llm-vnet`, Subnet: `pe-subnet`.

> Verifica **Private DNS Zones** y enroutamiento. Si AKS no tiene salida pública, agrega un **NAT Gateway**.

---

## 11) Pruebas (Smoke Tests)

```bash
# Health check
curl http://<EXTERNAL-IP>/health

# Consulta de chat
curl -X POST http://<EXTERNAL-IP>/chat \
  -H "Content-Type: application/json" \
  -d '{"q":"Hola, ¿qué puedes hacer?"}'
```

---

## 12) Observabilidad y Escalado

```bash
# Horizontal Pod Autoscaler
kubectl autoscale deployment llmapi --cpu-percent=70 --min=2 --max=8
kubectl get hpa
```

> Habilita **Container Insights** y crea alertas de latencia, errores y costos en **Azure Monitor**.

---

## 13) Cargar Documentos y Embeddings (RAG)

Usa el notebook adjunto para:

1. Leer documentos (PDF / MD / HTML / TXT).
2. Generar embeddings con Azure OpenAI (deployment de embeddings).
3. Subir documentos + vectores a Azure AI Search (indexación).

---

## Diagrama de Arquitectura – Flujo (Azure)

```
Usuario
  │
  ▼
Application Gateway / NGINX Ingress
  │
  ▼
AKS (llm-aks)
  ├─ Pod: llmapi (FastAPI)
  │    ├─ Azure OpenAI  ──► gpt-4o (chat)
  │    └─ Azure AI Search ─► docs-index (vector)
  │
  └─ Secrets ◄── Key Vault (CSI / Managed Identity)

ACR (llmacr001) ──► imagen llmapi:latest
```

---

## Troubleshooting Rápido

| Síntoma | Causa probable | Acción |
|---|---|---|
| Pods `CrashLoopBackOff` | Variables faltantes o permisos | `kubectl logs deploy/llmapi` |
| Ingress sin `EXTERNAL-IP` | Cuota de Public IPs / LoadBalancers agotada | Revisar cuotas en el portal |
| `401`/`403` en Azure OpenAI | KEY, endpoint, deployment o `api_version` incorrectos | Verificar variables de entorno |
| Error vector dims en Search | `vectorSearchDimensions` no coincide con el modelo de embeddings | Igualar dimensiones (ej. 1536) |
| Timeouts con Private Endpoints | Private DNS, NSG o NAT Gateway mal configurados | Revisar DNS Zones y NSGs |

---

## Limpieza (PoC)

```bash
az group delete -n llm-rg --yes --no-wait
```

---

## Apéndice A — Key Vault CSI + Managed Identity (Producción)

**Objetivo:** montar secretos desde Azure Key Vault en Pods de AKS sin exponer llaves, usando Managed Identity y el proveedor CSI de Key Vault.

### A1) Instalar Secret Store CSI Driver y Provider Azure

```bash
# Instalar el driver CSI
helm repo add secrets-store-csi-driver \
  https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo update
helm upgrade --install csi-secrets-store \
  secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system
```

> ⚠️ **Corrección aplicada:** La URL original apuntaba a `secretproviderclasspodidentity.yaml` (AAD Pod Identity, deprecado). Se reemplaza por el deployment estándar del provider de Azure:

```bash
# Instalar provider de Azure (deployment estándar)
kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml
```

### A2) Vincular AKS con Managed Identity

```bash
# (si no lo hiciste antes)
az identity create -g llm-rg -n llm-mi-aks

# Dar rol de "Key Vault Secrets User" a la MI sobre el Key Vault
az role assignment create \
  --assignee $(az identity show -g llm-rg -n llm-mi-aks --query principalId -o tsv) \
  --role "Key Vault Secrets User" \
  --scope $(az keyvault show -g llm-rg -n llm-kv-001 --query id -o tsv)
```

### A3) SecretProviderClass (YAML)

Define qué secretos montar desde el Key Vault y cómo exponerlos en el Pod:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: kv-secrets
spec:
  provider: azure
  parameters:
    usePodIdentity:         "false"
    useVMManagedIdentity:   "true"
    userAssignedIdentityID: "<CLIENT_ID_DE_TU_MI>"   # az identity show ... --query clientId -o tsv
    keyvaultName:           "llm-kv-001"
    cloudName:              ""
    objects: |
      array:
        - |
          objectName: AOAI-KEY
          objectType: secret
        - |
          objectName: SEARCH-KEY
          objectType: secret
    tenantId: "<TENANT_ID>"
  secretObjects:                         # opcional: sincronizar a K8s Secret
  - secretName: app-secrets
    type: Opaque
    data:
    - objectName: AOAI-KEY
      key: AOAI_KEY
    - objectName: SEARCH-KEY
      key: SEARCH_KEY
```

### A4) Montaje en el Deployment

```yaml
spec:
  template:
    spec:
      volumes:
      - name: kv
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: "kv-secrets"
      containers:
      - name: llmapi
        image: llmacr001.azurecr.io/llmapi:latest
        volumeMounts:
        - name: kv
          mountPath: "/mnt/secrets"
          readOnly: true
        env:
        - name: AOAI_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets    # requiere secretObjects definido arriba
              key: AOAI_KEY
```

> **Tips:** rota secretos en Key Vault, usa RBAC mínimo necesario y audita accesos con Azure AD y Key Vault logs.

---

## Apéndice B — Application Gateway Ingress Controller (AGIC) + WAF

**Objetivo:** usar Azure Application Gateway (con o sin WAF) como Ingress para AKS, habilitando TLS administrado, políticas L7 y Private Link.

### B1) Crear Application Gateway (Portal)

Portal → Create a resource → **Application Gateway** → elige SKU (`Standard_v2` o `WAF_v2`), VNet/Subnet dedicadas (p. ej. `agw-subnet`).

### B2) Habilitar AGIC en AKS

```bash
az aks enable-addons -g llm-rg -n llm-aks -a ingress-appgw \
  --appgw-id $(az network application-gateway show \
    -g llm-rg -n <APPGW_NAME> --query id -o tsv)
```

### B3) Ingress para AGIC (anotaciones)

Archivo: **`ingress-agic-tls.yaml`**

> Reemplaza `<YOUR_HOSTNAME>` por tu dominio real (ej. `llmapi.example.com`).
>
> **Sobre el TLS:** la terminación TLS ocurre en el Application Gateway (`WAF_v2` / `Standard_v2`). El campo `secretName: dummy-tls` es un **placeholder** requerido por el spec de Kubernetes Ingress — AGIC lo ignora y usa el certificado configurado directamente en el **Listener** del App Gateway. No es necesario que exista un Secret real con ese nombre para que el enrutamiento funcione.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llmapi-agic
  annotations:
    kubernetes.io/ingress.class: azure/application-gateway
spec:
  tls:
  - hosts: ["<YOUR_HOSTNAME>"]
    secretName: dummy-tls    # placeholder – AGIC usa el cert del App Gateway Listener
  rules:
  - host: <YOUR_HOSTNAME>
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: llmapi-svc
            port:
              number: 80
```

### B4) Secret TLS Placeholder (opcional)

Archivo: **`dummy-tls-secret.yaml`**

Si Kubernetes requiere que el Secret exista (algunos controladores lo validan), crea uno vacío. **No es el certificado real del Gateway.**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dummy-tls
type: kubernetes.io/tls
data:
  tls.crt: ""
  tls.key: ""
```

### B5) Aplicar los manifiestos

```bash
kubectl apply -f dummy-tls-secret.yaml    # opcional
kubectl apply -f ingress-agic-tls.yaml
```

> **Notas finales:** configura el Listener / HTTP Settings / Backend Pools en el App Gateway. Si usas WAF, define reglas y exclusiones. Para Private Link + App Gateway, integra con Private DNS Zones.

---

## Apéndice C — Dataset Real + Chunking para RAG (tiktoken)

**Objetivo:** mejorar la recuperación y precisión RAG partiendo documentos en fragmentos ("chunks") con solapamiento y metadatos.

### C0) Mini Dataset de Ejemplo

La guía incluye un conjunto de documentos de prueba en la carpeta `./data/`, que debe estar en el mismo directorio que el notebook `Notebook_Azure_RAG_Indexing.ipynb`:

```
./data/
├── faq_llm.txt       # Preguntas frecuentes del asistente LLM
├── policy_llm.txt    # Política de uso del asistente
└── howto_llm.txt     # Guía rápida de uso
```

> Si ubicas la carpeta en otra ruta, ajusta la variable `DATA_DIR` en el notebook:
>
> ```python
> DATA_DIR = "./data"   # ← cambia a la ruta donde esté la carpeta
> ```

### C1) Paquetes y Función de Chunking

```bash
pip install tiktoken unstructured
```

```python
import tiktoken

def chunk_text(
    text: str,
    chunk_size_tokens: int = 400,
    chunk_overlap_tokens: int = 60,
    encoding_name: str = "cl100k_base"
) -> list[str]:
    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text)
    chunks = []
    i = 0
    while i < len(tokens):
        window = tokens[i : i + chunk_size_tokens]
        chunks.append(enc.decode(window))
        i += (chunk_size_tokens - chunk_overlap_tokens)
    return chunks
```

### C2) Metadatos y Upsert

Incluye metadatos como título, fuente, página, timestamp o versión del dataset para trazabilidad:

```python
import os, glob
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# search_client ya inicializado con AzureKeyCredential (ver paso 5)

for path in glob.glob(f"{DATA_DIR}/*.txt"):
    content = open(path, "r", encoding="utf-8", errors="ignore").read()
    parts = chunk_text(content, 400, 60)
    batch = []
    for idx, part in enumerate(parts):
        vec = embed(part)   # función que llama al deployment de embeddings
        item = {
            "id":            f"{os.path.basename(path)}#{idx:04d}",
            "content":       part,
            "metadata":      f"file={os.path.basename(path)};chunk={idx}",
            "contentVector": vec
        }
        batch.append({"@search.action": "mergeOrUpload", **item})
    search_client.upload_documents(documents=batch)
```

> **Recomendaciones:**
> - Evalúa tamaño de chunk: 300–600 tokens.
> - Overlap: 40–100 tokens.
> - Normaliza texto (limpieza HTML / PDF).
> - Considera particionar por secciones semánticas si es posible.
