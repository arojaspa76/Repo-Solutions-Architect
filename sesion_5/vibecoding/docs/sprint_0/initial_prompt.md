You are acting as a senior Azure Solutions Architect and DevOps engineer.
Your task is to implement Sprint 0 of the GenAIDemo project: "Base Infrastructure".
The goal is a fully working, production-grade Azure infrastructure foundation
that can be deployed with a single command per environment.

Read CLAUDE.md before doing anything else. Follow all working principles and editing rules defined there.
Create docs/sprint_0/ now. All documentation you produce during this sprint goes there.

---

## PROJECT CONTEXT

Project name:     GenAIDemo
Organization:     TechCorp Inc.
Azure DevOps org: arojaspa  (project: Proyectos AI)
Repo structure:   vibecoding monorepo (see folder map below)
Primary engineer: Andrés Felipe Rojas Parra
Environments:     dev (deploy now) · staging · production (parameterized, not deployed)

---

## FOLDER MAP — work exclusively inside this structure

vibecoding/
├── ops/
│   ├── bicep/
│   │   ├── main.bicep              ← orchestrator, targetScope = resourceGroup
│   │   ├── modules/
│   │   │   ├── keyvault.bicep
│   │   │   ├── acr.bicep
│   │   │   ├── cosmosdb.bicep
│   │   │   ├── redis.bicep
│   │   │   └── aks.bicep
│   │   └── parameters/
│   │       ├── dev.bicepparam
│   │       └── staging.bicepparam
│   ├── k8s/
│   │   ├── namespace.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── services.yaml
│   │   ├── configmap.yaml
│   │   └── secret-provider.yaml
│   ├── docker/
│   │   └── (Dockerfiles are in services/ — do not create new ones here)
│   └── scripts/
│       ├── init_structure.ps1
│       ├── deploy.ps1
│       └── validate_infra.py
├── azure-pipelines.yml             ← CI/CD pipeline (root of repo)
├── azure-pipelines/
│   └── templates/
│       ├── build-backend.yml
│       ├── build-frontend.yml
│       ├── push-acr.yml
│       └── deploy-aks.yml
└── tests/
    └── integration/
        └── test_infra.py

---

## DELIVERABLE 1 — Azure Bicep IaC

### General rules for ALL Bicep files
- targetScope = 'resourceGroup' on main.bicep; modules inherit scope
- Every module receives: name, location, tags, environment parameters
- Standard tags on every resource:
    project:     'GenAIDemo'
    environment: <parameter>
    managedBy:   'Bicep'
    owner:       'andres.rojas@techcorp.com'
- No hardcoded secrets anywhere — use Key Vault references or output chaining
- Use @description() decorators on every parameter
- Use @minLength / @maxLength / @allowed where applicable
- All resource names follow pattern: {projectName}-{resourceType}-{environment}
  Example: genaidemo-kv-dev, genaidemo-acr-dev, genaidemo-cosmos-dev

### main.bicep
- Accepts parameters: projectName, environment, location, tags (object)
- Calls each module in dependency order:
    1. Key Vault  (no dependencies)
    2. ACR        (no dependencies)
    3. Cosmos DB  (stores connection string → Key Vault)
    4. Redis      (stores access key → Key Vault)
    5. AKS        (needs ACR reference for AcrPull role assignment)
- Passes outputs between modules (e.g. keyVaultName flows into cosmosdb and redis
  modules so they can write their own secrets)
- Outputs: keyVaultName, acrLoginServer, cosmosDbEndpoint, aksClusterName

### modules/keyvault.bicep
- SKU: standard
- enableRbacAuthorization: true  (NO legacy access policies)
- enableSoftDelete: true, softDeleteRetentionInDays: 90
- enablePurgeProtection: true
- publicNetworkAccess: 'Enabled' for dev (parameterized for prod lockdown)
- networkAcls: defaultAction 'Allow' for dev, 'Deny' for prod
- Output: keyVaultName, keyVaultUri

### modules/acr.bicep
- SKU: Standard
- adminUserEnabled: false
- zoneRedundancy: 'Disabled' for dev
- anonymousPullEnabled: false
- Output: acrName, acrLoginServer, acrId (needed for role assignment in AKS module)

### modules/cosmosdb.bicep
- kind: GlobalDocumentDB  (NoSQL API)
- capability: EnableServerless  (dev only; parameterized to switch to provisioned)
- consistencyPolicy: Session
- locations: single region for dev (parameter)
- Database name:  genaidemo-db
- Container name: conversations
  - partitionKey: /user_id
  - defaultTtl: -1  (TTL disabled by default, set per-document)
  - indexingPolicy: automatic
- After creation, store the primary connection string as a Key Vault secret:
    secret name: COSMOS-DB-CONNECTION-STRING
- Output: cosmosDbEndpoint, cosmosDbAccountName

### modules/redis.bicep
- SKU: C1 Standard for dev (parameterized)
- enableNonSslPort: false
- minimumTlsVersion: '1.2'
- redisVersion: '6'
- After creation, store the primary access key as a Key Vault secret:
    secret name: REDIS-ACCESS-KEY
- Also store the host:port as secret: REDIS-HOST
- Output: redisHostName, redisSslPort

### modules/aks.bicep
- Kubernetes version: 1.29 (parameterized)
- Default node pool: Standard_D2s_v3, nodeCount: 2 for dev
- enableAutoScaling: true, minCount: 2, maxCount: 5
- networkPlugin: azure
- managedIdentity: SystemAssigned
- Addons: azureKeyvaultSecretsProvider (enable secret rotation)
- After creation, assign AcrPull role to AKS kubelet identity on the ACR resource
- Output: aksClusterName, aksOidcIssuerUrl, aksManagedIdentityPrincipalId

### parameters/dev.bicepparam
- All values for the dev environment
- NO secrets — reference Key Vault where needed
- location: 'eastus2'

### parameters/staging.bicepparam  
- Same structure as dev, different values
- location: 'eastus2'
- Larger SKUs where relevant (e.g. Redis C2, AKS 3 nodes)

---

## DELIVERABLE 2 — Azure DevOps CI/CD Pipeline

### azure-pipelines.yml  (root of repo)
- trigger: branches include [develop, main]; paths exclude [docs/**, '*.md']
- pr: trigger on PRs to develop and main
- variables:
    - group: genaidemo-kv-dev   (linked to Key Vault via Library)
    - name/value pairs for non-secret config (ACR name, AKS cluster name, etc.)
- stages in order:
    1. validate   — az bicep lint + az deployment group what-if (dry run)
    2. build      — backend and frontend in parallel jobs
    3. push       — push images to ACR (only on develop/main, not PRs)
    4. deploy     — deploy to AKS dev (only on develop/main, not PRs)

### azure-pipelines/templates/build-backend.yml
- Python 3.12 via UsePythonVersion task
- Install uv: pip install uv
- uv sync --frozen --no-dev
- Run: pytest tests/unit --junitxml=$(Agent.TempDirectory)/test-results.xml
              --cov=src --cov-report=xml:$(Agent.TempDirectory)/coverage.xml
- PublishTestResults task
- PublishCodeCoverageResults task
- docker build with tag $(Build.BuildId) and latest
- Output variable: BACKEND_IMAGE_TAG = $(Build.BuildId)

### azure-pipelines/templates/build-frontend.yml
- Node 20 via NodeTool task
- corepack enable && pnpm install --frozen-lockfile
- pnpm run test:ci   (publishes JUnit results)
- pnpm run build
- docker build with tag $(Build.BuildId) and latest
- Output variable: FRONTEND_IMAGE_TAG = $(Build.BuildId)

### azure-pipelines/templates/push-acr.yml
- Condition: and(succeeded(), ne(variables['Build.Reason'], 'PullRequest'))
- Docker@2 task: buildAndPush for genaidemo-backend
- Docker@2 task: buildAndPush for genaidemo-frontend
- Both images tagged: $(Build.BuildId) AND latest

### azure-pipelines/templates/deploy-aks.yml
- Condition: and(succeeded(), eq(variables['Build.SourceBranchName'], 'develop'))
- Use KubernetesManifest@1 task for each manifest in ops/k8s/
- Apply in order: namespace → configmap → secret-provider → deployments → services
- After deploy: run smoke test (curl /api/health on the backend ClusterIP via kubectl exec)
- If smoke test fails: kubectl rollout undo for both deployments

---

## DELIVERABLE 3 — Kubernetes Manifests  (ops/k8s/)

### namespace.yaml
- name: genaidemo-dev
- labels: project=genaidemo, environment=dev

### configmap.yaml
- namespace: genaidemo-dev
- Non-secret environment variables:
    ENVIRONMENT, PROJECT_NAME, COSMOS_DB_ENDPOINT,
    REDIS_HOST (reference — actual value from secret-provider),
    AZURE_OPENAI_ENDPOINT (placeholder, to be filled)

### secret-provider.yaml
- SecretProviderClass for Azure Key Vault CSI driver
- keyvaultName: read from pipeline variable $(KEY_VAULT_NAME)
- Secrets to mount:
    COSMOS-DB-CONNECTION-STRING  → env var COSMOS_DB_CONNECTION_STRING
    REDIS-ACCESS-KEY             → env var REDIS_ACCESS_KEY
    AZURE-AD-CLIENT-ID           → env var AZURE_AD_CLIENT_ID
    AZURE-AD-CLIENT-SECRET       → env var AZURE_AD_CLIENT_SECRET
    AZURE-AD-TENANT-ID           → env var AZURE_AD_TENANT_ID
    AZURE-OPENAI-KEY             → env var AZURE_OPENAI_KEY
- tenantId: read from pipeline variable $(AZURE_TENANT_ID)
- userAssignedIdentityID: AKS kubelet managed identity

### backend-deployment.yaml
- namespace: genaidemo-dev
- replicas: 2
- image: $(ACR_LOGIN_SERVER)/genaidemo-backend:latest
  (will be substituted by KubernetesManifest imageSubstitution)
- resources: requests cpu=250m mem=512Mi / limits cpu=1000m mem=1Gi
- readinessProbe: GET /api/health, initialDelaySeconds=15, periodSeconds=10
- livenessProbe:  GET /api/health, initialDelaySeconds=30, periodSeconds=30
- envFrom: secretRef from secret-provider + configMapRef
- volumeMounts: CSI volume from SecretProviderClass

### frontend-deployment.yaml
- namespace: genaidemo-dev
- replicas: 2
- image: $(ACR_LOGIN_SERVER)/genaidemo-frontend:latest
- resources: requests cpu=100m mem=256Mi / limits cpu=500m mem=512Mi
- readinessProbe: GET /, port 3000
- env: NEXT_PUBLIC_API_URL from configmap

### services.yaml
- backend:  ClusterIP, port 8000 → targetPort 8000
- frontend: LoadBalancer, port 80 → targetPort 3000

---

## DELIVERABLE 4 — Infrastructure Validation Tests  (tests/integration/test_infra.py)

Use pytest. All credentials come from environment variables (never hardcoded).
Required env vars: KEY_VAULT_NAME, AZURE_TENANT_ID, AZURE_CLIENT_ID,
                   AZURE_CLIENT_SECRET, COSMOS_DB_ENDPOINT, REDIS_HOST,
                   REDIS_SSL_PORT, ACR_NAME, RESOURCE_GROUP

Write these test functions:

1. test_keyvault_reachable()
   - Connect with DefaultAzureCredential
   - List secrets (just first page) — assert no exception
   - Assert COSMOS-DB-CONNECTION-STRING exists

2. test_cosmosdb_crud()
   - Read connection string from Key Vault
   - CosmosClient: create item in conversations container
     item = {"id": "test-infra-001", "user_id": "infra-test", "content": "ping"}
   - Read it back, assert id matches
   - Delete it
   - Assert deletion (404 on subsequent read)

3. test_redis_connectivity()
   - Read REDIS-ACCESS-KEY from Key Vault
   - redis.StrictRedis with ssl=True
   - SET infra-test-key "hello-genaidemo"
   - GET infra-test-key → assert == "hello-genaidemo"
   - DELETE infra-test-key

4. test_acr_image_pullable()
   - Use azure-mgmt-containerregistry with DefaultAzureCredential
   - List repositories in ACR_NAME
   - This test PASSES even if the list is empty (ACR exists and is reachable)
   - Assert no AuthenticationError

5. test_keyvault_secrets_complete()
   - Assert ALL of the following secrets exist in Key Vault:
     COSMOS-DB-CONNECTION-STRING, REDIS-ACCESS-KEY, REDIS-HOST,
     AZURE-AD-CLIENT-ID, AZURE-AD-CLIENT-SECRET, AZURE-AD-TENANT-ID,
     AZURE-OPENAI-KEY

Add a pytest fixture: azure_credential() using DefaultAzureCredential.
Add a conftest.py with session-scoped fixture for SecretClient.

---

## DELIVERABLE 5 — Helper Scripts  (ops/scripts/)

### deploy.ps1
PowerShell script to deploy Bicep to Azure. Must:
- Accept parameters: -Environment (dev|staging), -ResourceGroup, -Location
- Login check: az account show (fail fast if not logged in)
- Run: az deployment group create
         --resource-group $ResourceGroup
         --template-file ops/bicep/main.bicep
         --parameters ops/bicep/parameters/$Environment.bicepparam
         --name "genaidemo-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmm')"
- After deployment: print all outputs in a formatted table
- Capture exit code and report PASS / FAIL clearly

### validate_infra.py
Python script (not pytest) that runs all integration tests and outputs
a Markdown-formatted report to docs/architecture/sprint0-validation.md
with columns: Test Name | Status | Duration | Notes

---

## DELIVERABLE 6 — Repository Initialization Script  (ops/scripts/init_structure.ps1)

PowerShell script that creates every folder in the vibecoding structure
with a .gitkeep placeholder. Must be idempotent (re-running does not fail
if folders already exist). Print a summary of created vs already-existing folders.

---

## CODING STANDARDS — apply to every file you create

- Bicep: use @description(), @minLength, @allowed decorators; no inline comments
  that reveal internal naming conventions or personal data
- Python: type hints on all functions, docstrings on all test functions,
  black-compatible formatting, no bare except clauses
- YAML: 2-space indent, explicit types where ambiguous, no trailing spaces
- All files must have a header comment block:
    # Project:     GenAIDemo
    # Component:   <component name>
    # Description: <one line>
    # Owner:       Andrés Felipe Rojas Parra
    # Created:     2026-07
- No hardcoded values: every environment-specific value must come from
  a parameter, environment variable, or Key Vault reference

---

## IMPORTANT NOTES FOR BICEP

I will provide you with the exact Bicep content for each module file before
you write it. Wait for me to paste each module spec before generating it.
For all other files (YAML, Python, PowerShell), generate them immediately
following the specifications above.

Start by:
1. Creating the full folder structure (all files as empty stubs with header comments)
2. Generating azure-pipelines.yml and all pipeline templates
3. Generating all Kubernetes manifests
4. Generating tests/integration/test_infra.py and conftest.py
5. Generating ops/scripts/deploy.ps1 and validate_infra.py
6. Generating ops/scripts/init_structure.ps1
7. WAITING for me to provide Bicep module specs before writing any .bicep file

After completing steps 1–6, print a checklist of all files created
and confirm you are ready to receive the Bicep specifications.