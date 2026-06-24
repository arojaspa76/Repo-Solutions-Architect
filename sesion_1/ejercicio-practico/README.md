# Step-by-Step Guide – LLM Solution Deployment on Microsoft Azure
## AKS + ACR + Azure OpenAI + Azure AI Search

**Format:** Markdown | **Level:** Architect / Master's

This guide details the exact actions in the Portal and CLI, with explanations, code, and best practices.

---

## 0) Pre-flight Checklist

1. Verify subscription and permissions (`Owner` / `Contributor`) in Azure Portal.
2. Confirm access to Azure OpenAI in an available region (Central US, Sweden Central, etc.).
3. Local tools: Azure CLI (`>=2.60`), `kubectl`, Docker, Git.
4. Sign in via CLI:

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID_OR_NAME>"
```

---

## 1) Create Resource Group and Network (VNet + Subnets)

**Portal:** Resource groups → Create → Name: `llm-rg` | Region: `Central US`

**CLI equivalent:**

```powershell
az group create -n llm-rg -l centralus

az network vnet create `
  -g llm-rg -n llm-vnet `
  --address-prefixes 10.10.0.0/16 `
  --subnet-name aks-subnet `
  --subnet-prefix 10.10.1.0/24

az network vnet subnet create `
  -g llm-rg --vnet-name llm-vnet `
  -n pe-subnet `
  --address-prefix 10.10.2.0/24
```

---

## 2) Key Vault and Managed Identity (RBAC)

Create a Key Vault and a Managed Identity to avoid exposing keys:

```powershell
az keyvault create `
  -g llm-rg -n llm-kv-001 -l centralus `
  --enable-rbac-authorization true

az identity create -g llm-rg -n llm-mi-aks

# Grant role to read secrets
$principalId = az identity show -g llm-rg -n llm-mi-aks --query principalId -o tsv
$kvScope     = az keyvault show -g llm-rg -n llm-kv-001 --query id -o tsv

az role assignment create `
  --assignee $principalId `
  --role "Key Vault Secrets User" `
  --scope $kvScope
```

---

## 3) Azure AI Search (Vector Search)

**Portal:** Create a resource → Azure AI Search → Name: `llm-search-001` → Pricing tier: `Standard` or higher.

**Networking:** Private endpoint (recommended) → Subnet: `pe-subnet` (optional).

**Create vector index** (JSON example, 1536 dimensions):

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

## 4) Azure OpenAI – Create Resource and Deployments

**Portal:** Create a resource → Azure OpenAI → Name: `llm-aoai-001` → Region (same as others).

**Networking:** Private endpoint (optional, recommended).

Open **Azure AI Studio** → Deployments → Create new deployment:

| Purpose     | Model                   |
|-------------|-------------------------|
| Chat        | `gpt-4o`                |
| Embeddings  | `text-embedding-3-small`|

> Save the **Endpoint URL** and **Deployment Name(s)** to use later.

---

## 5) Azure Container Registry (ACR) and Image Push

Create registry, build and push Docker image:

```powershell
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

**`app.py`** (FastAPI – simplified demo):

> ⚠️ **Corrections applied:**
> - `SearchClient` requires `AzureKeyCredential`, not a plain string.
> - The vector search API uses `VectorizedQuery` (SDK `>=11.4`), not the obsolete `vector={}` dict.

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
    credential=AzureKeyCredential(SEARCH_KEY)   # ← requires AzureKeyCredential
)

class Query(BaseModel):
    q: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(q: Query):
    # In production: generate the embedding of q.q with the embeddings deployment
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
        messages=[{"role": "user", "content": f"Context:\n{context}\nQuestion:\n{q.q}"}]
    )
    return {"answer": resp.choices[0].message.content}
```

**Build & Push:**

```powershell
docker build -t llmacr001.azurecr.io/llmapi:latest .
docker push llmacr001.azurecr.io/llmapi:latest
```

---

## 6) AKS – Create Cluster and Attach ACR

> ⚠️ **Correction applied:** `--assign-identity` is added to associate the Managed Identity created in step 2 to the cluster from the start.

```powershell
$MI_ID = az identity show -g llm-rg -n llm-mi-aks --query id -o tsv

az aks create `
  -g llm-rg -n llm-aks `
  --node-count 2 `
  --enable-addons monitoring `
  --attach-acr llmacr001 `
  --network-plugin azure `
  --assign-identity $MI_ID

az aks get-credentials -g llm-rg -n llm-aks
kubectl get nodes
```

---

## 7) Secrets (Kubernetes Secrets – quick start)

> For production use Key Vault CSI (see Appendix A). Here is a quick initial approach:

```powershell
kubectl create secret generic app-secrets `
  --from-literal=AOAI_ENDPOINT="https://<your-aoai>.openai.azure.com/" `
  --from-literal=AOAI_DEPLOYMENT="gpt4o-deploy" `
  --from-literal=AOAI_KEY="<your_api_key>" `
  --from-literal=SEARCH_ENDPOINT="https://llm-search-001.search.windows.net" `
  --from-literal=SEARCH_KEY="<your_search_key>"
```

---

## 8) Deployment (Deployment + Service)

Create `deployment.yaml` with 2 replicas and expose an internal Service:

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

```powershell
kubectl apply -f deployment.yaml
kubectl get pods
```

---

## 9) Ingress (NGINX) – Expose Publicly

Install NGINX Ingress with Helm and create `ingress.yaml`:

```powershell
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx `
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

```powershell
kubectl apply -f ingress.yaml
kubectl get svc -n ingress-nginx
```

---

## 10) Private Endpoints (Optional – Recommended)

For Azure OpenAI and Azure AI Search:

**Portal:** Resource → Networking → Private endpoint → +Add → VNet: `llm-vnet`, Subnet: `pe-subnet`.

> Verify **Private DNS Zones** and routing. If AKS has no public outbound, add a **NAT Gateway**.

---

## 11) Tests (Smoke Tests)

```powershell
# Health check
curl http://<EXTERNAL-IP>/health

# Chat query
$body = '{"q":"Hello, what can you do?"}'
Invoke-RestMethod -Method Post `
  -Uri "http://<EXTERNAL-IP>/chat" `
  -ContentType "application/json" `
  -Body $body
```

---

## 12) Observability and Scaling

```powershell
# Horizontal Pod Autoscaler
kubectl autoscale deployment llmapi --cpu-percent=70 --min=2 --max=8
kubectl get hpa
```

> Enable **Container Insights** and create latency, error, and cost alerts in **Azure Monitor**.

---

## 13) Load Documents and Embeddings (RAG)

Use the attached notebook to:

1. Read documents (PDF / MD / HTML / TXT).
2. Generate embeddings with Azure OpenAI (embeddings deployment).
3. Upload documents + vectors to Azure AI Search (indexing).

---

## Architecture Diagram – Flow (Azure)

```
User
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

ACR (llmacr001) ──► image llmapi:latest
```

---

## Quick Troubleshooting

| Symptom | Probable Cause | Action |
|---|---|---|
| Pods `CrashLoopBackOff` | Missing variables or permissions | `kubectl logs deploy/llmapi` |
| Ingress with no `EXTERNAL-IP` | Public IP / LoadBalancer quota exhausted | Check quotas in the portal |
| `401`/`403` on Azure OpenAI | Wrong KEY, endpoint, deployment or `api_version` | Verify environment variables |
| Vector dims error in Search | `vectorSearchDimensions` does not match embeddings model | Match dimensions (e.g. 1536) |
| Timeouts with Private Endpoints | Private DNS, NSG or NAT Gateway misconfigured | Review DNS Zones and NSGs |

---

## Cleanup (PoC)

```powershell
az group delete -n llm-rg --yes --no-wait
```

---

## Appendix A — Key Vault CSI + Managed Identity (Production)

**Goal:** Mount secrets from Azure Key Vault into AKS Pods without exposing keys, using Managed Identity and the Key Vault CSI provider.

### A1) Install Secret Store CSI Driver and Azure Provider

```powershell
# Install the CSI driver
helm repo add secrets-store-csi-driver `
  https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo update
helm upgrade --install csi-secrets-store `
  secrets-store-csi-driver/secrets-store-csi-driver `
  --namespace kube-system
```

> ⚠️ **Correction applied:** The original URL pointed to `secretproviderclasspodidentity.yaml` (AAD Pod Identity, deprecated). Replaced with the standard Azure provider deployment:

```powershell
# Install Azure provider (standard deployment)
kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml
```

### A2) Link AKS with Managed Identity

```powershell
# (if not done before)
az identity create -g llm-rg -n llm-mi-aks

# Grant "Key Vault Secrets User" role to the MI on the Key Vault
$principalId = az identity show -g llm-rg -n llm-mi-aks --query principalId -o tsv
$kvScope     = az keyvault show -g llm-rg -n llm-kv-001 --query id -o tsv

az role assignment create `
  --assignee $principalId `
  --role "Key Vault Secrets User" `
  --scope $kvScope
```

### A3) SecretProviderClass (YAML)

Defines which secrets to mount from Key Vault and how to expose them in the Pod:

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
    userAssignedIdentityID: "<CLIENT_ID_OF_YOUR_MI>"   # az identity show ... --query clientId -o tsv
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
  secretObjects:                         # optional: sync to K8s Secret
  - secretName: app-secrets
    type: Opaque
    data:
    - objectName: AOAI-KEY
      key: AOAI_KEY
    - objectName: SEARCH-KEY
      key: SEARCH_KEY
```

### A4) Mount in the Deployment

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
              name: app-secrets    # requires secretObjects defined above
              key: AOAI_KEY
```

> **Tips:** Rotate secrets in Key Vault, use minimum required RBAC, and audit access with Azure AD and Key Vault logs.

---

## Appendix B — Application Gateway Ingress Controller (AGIC) + WAF

**Goal:** Use Azure Application Gateway (with or without WAF) as Ingress for AKS, enabling managed TLS, L7 policies, and Private Link.

### B1) Create Application Gateway (Portal)

Portal → Create a resource → **Application Gateway** → choose SKU (`Standard_v2` or `WAF_v2`), dedicated VNet/Subnet (e.g. `agw-subnet`).

### B2) Enable AGIC on AKS

```powershell
$appgwId = az network application-gateway show `
  -g llm-rg -n <APPGW_NAME> --query id -o tsv

az aks enable-addons -g llm-rg -n llm-aks -a ingress-appgw `
  --appgw-id $appgwId
```

### B3) Ingress for AGIC (annotations)

File: **`ingress-agic-tls.yaml`**

> Replace `<YOUR_HOSTNAME>` with your real domain (e.g. `llmapi.example.com`).
>
> **About TLS:** TLS termination occurs at the Application Gateway (`WAF_v2` / `Standard_v2`). The `secretName: dummy-tls` field is a **placeholder** required by the Kubernetes Ingress spec — AGIC ignores it and uses the certificate configured directly in the App Gateway **Listener**. A real Secret with that name is not required for routing to work.

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
    secretName: dummy-tls    # placeholder – AGIC uses the App Gateway Listener cert
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

### B4) TLS Placeholder Secret (optional)

File: **`dummy-tls-secret.yaml`**

If Kubernetes requires the Secret to exist (some controllers validate it), create an empty one. **This is not the real Gateway certificate.**

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

### B5) Apply the manifests

```powershell
kubectl apply -f dummy-tls-secret.yaml    # optional
kubectl apply -f ingress-agic-tls.yaml
```

> **Final notes:** Configure the Listener / HTTP Settings / Backend Pools in the App Gateway. If using WAF, define rules and exclusions. For Private Link + App Gateway, integrate with Private DNS Zones.

---

## Appendix C — Real Dataset + Chunking for RAG (tiktoken)

**Goal:** Improve RAG retrieval and accuracy by splitting documents into overlapping chunks with metadata.

### C0) Sample Mini Dataset

The guide includes a set of test documents in the `./data/` folder, which must be in the same directory as the `Notebook_Azure_RAG_Indexing.ipynb` notebook:

```
./data/
├── faq_llm.txt       # LLM assistant frequently asked questions
├── policy_llm.txt    # Assistant usage policy
└── howto_llm.txt     # Quick usage guide
```

> If you place the folder in a different path, update the `DATA_DIR` variable in the notebook:
>
> ```python
> DATA_DIR = "./data"   # ← change to the path where the folder is located
> ```

### C1) Packages and Chunking Function

```powershell
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

### C2) Metadata and Upsert

Include metadata such as title, source, page, timestamp, or dataset version for traceability:

```python
import os, glob
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# search_client already initialized with AzureKeyCredential (see step 5)

for path in glob.glob(f"{DATA_DIR}/*.txt"):
    content = open(path, "r", encoding="utf-8", errors="ignore").read()
    parts = chunk_text(content, 400, 60)
    batch = []
    for idx, part in enumerate(parts):
        vec = embed(part)   # function that calls the embeddings deployment
        item = {
            "id":            f"{os.path.basename(path)}#{idx:04d}",
            "content":       part,
            "metadata":      f"file={os.path.basename(path)};chunk={idx}",
            "contentVector": vec
        }
        batch.append({"@search.action": "mergeOrUpload", **item})
    search_client.upload_documents(documents=batch)
```

> **Recommendations:**
> - Evaluate chunk size: 300–600 tokens.
> - Overlap: 40–100 tokens.
> - Normalize text (clean HTML / PDF).
> - Consider splitting by semantic sections when possible.
