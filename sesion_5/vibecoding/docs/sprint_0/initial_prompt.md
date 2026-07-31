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

```
vibecoding/
├── azure-pipelines.yml             ← CI/CD pipeline (root of repo)
├── azure-pipelines/
│   └── templates/
│       ├── build-backend.yml
│       ├── build-frontend.yml
│       ├── push-acr.yml
│       └── deploy-aks.yml
├── Makefile                        ← cross-platform (Windows 11 Git Bash + Ubuntu 24.04)
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
│   └── scripts/
│       ├── init_structure.ps1
│       ├── deploy.ps1
│       └── validate_infra.py
├── docs/
│   ├── architecture/               ← ADRs, diagrams (Mermaid/draw.io),
│   │                                  OpenAPI specs, auth flows — timeless docs
│   └── sprint_0/                   ← Created NOW for Sprint 0
│       ├── backlog.md
│       ├── validation.md
│       └── decisions.md
└── tests/
    └── integration/
        ├── conftest.py
        └── test_infra.py
```

## Documentation convention — apply to every sprint

For every sprint, create a dedicated folder: docs/sprint_{N}/
where N is the zero-padded sprint number (sprint_0, sprint_1, sprint_2...).

Rules:
- docs/architecture/  → timeless artifacts: ADRs, system diagrams,
                         OpenAPI specs, auth flows, data models.
                         These are NEVER sprint-specific.
- docs/sprint_{N}/    → everything scoped to that sprint:
                         backlog, validation reports, sign-off checklists,
                         meeting notes, spike results, demo scripts.

When starting a new sprint, CREATE the sprint_{N}/ folder as the
very first action before writing any code. Pre-populate it with:
  - backlog.md        (sprint goal, PBIs in scope, story points)
  - validation.md     (empty template: test results table, sign-off checklist)
  - decisions.md      (empty template: decisions made during the sprint)

Never mix sprint-specific content into docs/architecture/.
Never put architecture diagrams inside a sprint folder.

---

## CODING STANDARDS — apply to every file you create

- Bicep: use @description(), @minLength, @allowed decorators on every parameter;
  no inline comments that reveal internal naming conventions or personal data
- Python: type hints on all functions, docstrings on all test functions,
  black-compatible formatting (88 char line limit), no bare except clauses
- YAML: 2-space indent, explicit types where ambiguous, no trailing spaces
- PowerShell: use approved verbs, -ErrorAction Stop on critical az calls,
  Write-Host with [INFO] / [OK] / [ERROR] prefixes (no ANSI codes)
- All files must include a header comment block:
    # Project:     GenAIDemo
    # Component:   <component name>
    # Description: <one line>
    # Owner:       Andrés Felipe Rojas Parra
    # Created:     2026-07
- No hardcoded values anywhere: every environment-specific value must come
  from a parameter, environment variable, or Key Vault reference

---

## DELIVERABLE 1 — Azure Bicep IaC

### General rules for ALL Bicep files
- targetScope = 'resourceGroup' on main.bicep; modules inherit scope
- Every module receives: name, location, tags, environment parameters
- Standard tags object applied to every resource:
    project:     'GenAIDemo'
    environment: <parameter>
    managedBy:   'Bicep'
    owner:       'andres.rojas@techcorp.com'
- No hardcoded secrets — use Key Vault references or output chaining
- Use @description() decorators on every parameter
- Use @minLength / @maxLength / @allowed where applicable
- All resource names follow the pattern: {projectName}-{resourceType}-{environment}
  Examples: genaidemo-kv-dev, genaidemo-acr-dev, genaidemo-cosmos-dev

### main.bicep
- Accepts parameters: projectName, environment, location, tags (object)
- Calls each module in dependency order:
    1. Key Vault  (no dependencies)
    2. ACR        (no dependencies)
    3. Cosmos DB  (stores connection string into Key Vault)
    4. Redis      (stores access key into Key Vault)
    5. AKS        (needs ACR reference for AcrPull role assignment)
- Passes outputs between modules (e.g. keyVaultName flows into cosmosdb
  and redis modules so they can write their own secrets into Key Vault)
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
- capability: EnableServerless for dev (parameterized to switch to provisioned)
- consistencyPolicy: Session
- locations: single region for dev (parameter-driven)
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
- Also store the hostname as a Key Vault secret:
    secret name: REDIS-HOST
- Output: redisHostName, redisSslPort

### modules/aks.bicep
- Kubernetes version: 1.29 (parameterized)
- Default node pool: Standard_D2s_v3, nodeCount: 2 for dev
- enableAutoScaling: true, minCount: 2, maxCount: 5
- networkPlugin: azure
- identity: SystemAssigned (managed identity)
- Addons: azureKeyvaultSecretsProvider with enableSecretRotation: true
- After creation, assign AcrPull role to the AKS kubelet identity on the ACR resource
- Output: aksClusterName, aksOidcIssuerUrl, aksManagedIdentityPrincipalId

### parameters/dev.bicepparam
- All values for the dev environment
- NO secrets — only non-sensitive configuration values
- location: 'eastus2'
- environment: 'dev'
- Appropriate SKUs: Redis C1, AKS 2 nodes Standard_D2s_v3

### parameters/staging.bicepparam
- Same structure as dev, different values
- location: 'eastus2'
- environment: 'staging'
- Larger SKUs: Redis C2, AKS 3 nodes Standard_D4s_v3

---

## DELIVERABLE 2 — Azure DevOps CI/CD Pipeline

### azure-pipelines.yml  (root of repo)
- trigger:
    branches: include [develop, main]
    paths:    exclude [docs/**, '*.md', '*.txt']
- pr:
    branches: include [develop, main]
    paths:    exclude [docs/**, '*.md', '*.txt']
- variables:
    - group: genaidemo-kv-dev   (linked to Key Vault via Library — comment explains setup)
    - name/value pairs for non-secret config:
        ACR_NAME, AKS_CLUSTER_NAME, RESOURCE_GROUP, LOCATION, ENVIRONMENT
- stages in order:
    1. validate   — az bicep lint on main.bicep +
                    az deployment group what-if (dry run, non-blocking warning on failure)
    2. build      — backend and frontend as parallel jobs using templates
    3. push       — push images to ACR
                    condition: and(succeeded(), ne(variables['Build.Reason'], 'PullRequest'))
    4. deploy     — deploy to AKS dev
                    condition: and(succeeded(), eq(variables['Build.SourceBranchName'], 'develop'))

### azure-pipelines/templates/build-backend.yml
- parameters: imageTag (string), acrName (string)
- Python 3.12 via UsePythonVersion task
- pip install uv
- uv sync --frozen --no-dev
- pytest tests/unit --junitxml=$(Agent.TempDirectory)/backend-test-results.xml
         --cov=src --cov-report=xml:$(Agent.TempDirectory)/backend-coverage.xml
- PublishTestResults: testResultsFormat JUnit, searchFolder Agent.TempDirectory
- PublishCodeCoverageResults: codecoverageTool Cobertura
- docker build -t $(acrName).azurecr.io/genaidemo-backend:$(imageTag) .
  using services/backend/Dockerfile
- Output variable: BACKEND_IMAGE = $(acrName).azurecr.io/genaidemo-backend:$(imageTag)

### azure-pipelines/templates/build-frontend.yml
- parameters: imageTag (string), acrName (string)
- NodeTool: 20
- corepack enable && pnpm install --frozen-lockfile
- pnpm run test:ci  (expects JUnit output to $(Agent.TempDirectory)/frontend-test-results.xml)
- PublishTestResults
- pnpm run build
- docker build -t $(acrName).azurecr.io/genaidemo-frontend:$(imageTag) .
  using services/frontend/Dockerfile
- Output variable: FRONTEND_IMAGE = $(acrName).azurecr.io/genaidemo-frontend:$(imageTag)

### azure-pipelines/templates/push-acr.yml
- parameters: imageTag (string), acrName (string)
- az acr login --name $(acrName)
- Docker@2 task: push genaidemo-backend with tags $(imageTag) and latest
- Docker@2 task: push genaidemo-frontend with tags $(imageTag) and latest

### azure-pipelines/templates/deploy-aks.yml
- parameters: environment (string), resourceGroup (string), aksClusterName (string)
- az aks get-credentials --resource-group $(resourceGroup) --name $(aksClusterName)
- KubernetesManifest@1: deploy namespace.yaml
- KubernetesManifest@1: deploy configmap.yaml
- KubernetesManifest@1: deploy secret-provider.yaml
- KubernetesManifest@1: deploy backend-deployment.yaml and frontend-deployment.yaml
- KubernetesManifest@1: deploy services.yaml
- Smoke test step: kubectl exec a backend pod and curl http://localhost:8000/api/health
  if exit code != 0: kubectl rollout undo deployment/genaidemo-backend -n genaidemo-$(environment)
                      kubectl rollout undo deployment/genaidemo-frontend -n genaidemo-$(environment)
                      then fail the stage

---

## DELIVERABLE 3 — Kubernetes Manifests  (ops/k8s/)

### namespace.yaml
- name: genaidemo-dev
- labels: project=genaidemo, environment=dev, managed-by=bicep

### configmap.yaml
- namespace: genaidemo-dev
- name: genaidemo-config
- data:
    ENVIRONMENT: "dev"
    PROJECT_NAME: "genaidemo"
    AZURE_OPENAI_ENDPOINT: "https://placeholder.openai.azure.com/"
    NEXT_PUBLIC_API_URL: "http://genaidemo-backend:8000"

### secret-provider.yaml
- apiVersion: secrets-store.csi.x-k8s.io/v1
- kind: SecretProviderClass
- namespace: genaidemo-dev
- name: genaidemo-kv-secrets
- spec.provider: azure
- parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityID: ""    ← comment: replace with AKS kubelet managed identity client ID
    keyvaultName: ""              ← comment: replace with Key Vault name from Bicep output
    tenantId: ""                  ← comment: replace with Azure tenant ID
    objects: |
      array:
        - |
          objectName: COSMOS-DB-CONNECTION-STRING
          objectType: secret
        - |
          objectName: REDIS-ACCESS-KEY
          objectType: secret
        - |
          objectName: REDIS-HOST
          objectType: secret
        - |
          objectName: AZURE-AD-CLIENT-ID
          objectType: secret
        - |
          objectName: AZURE-AD-CLIENT-SECRET
          objectType: secret
        - |
          objectName: AZURE-AD-TENANT-ID
          objectType: secret
        - |
          objectName: AZURE-OPENAI-KEY
          objectType: secret
- secretObjects:
    - secretName: genaidemo-secrets
      type: Opaque
      data mapping for each objectName → data key (camelCase env var name)

### backend-deployment.yaml
- namespace: genaidemo-dev
- replicas: 2
- selector: app=genaidemo-backend
- image: REPLACE_WITH_ACR_LOGIN_SERVER/genaidemo-backend:latest
  (KubernetesManifest imageSubstitution will replace this)
- resources:
    requests: cpu=250m, memory=512Mi
    limits:   cpu=1000m, memory=1Gi
- readinessProbe: httpGet /api/health port 8000
    initialDelaySeconds: 15, periodSeconds: 10, failureThreshold: 3
- livenessProbe: httpGet /api/health port 8000
    initialDelaySeconds: 30, periodSeconds: 30, failureThreshold: 3
- envFrom:
    - secretRef: genaidemo-secrets
    - configMapRef: genaidemo-config
- volumes: CSI volume referencing SecretProviderClass genaidemo-kv-secrets
- volumeMounts: /mnt/secrets-store readonly

### frontend-deployment.yaml
- namespace: genaidemo-dev
- replicas: 2
- selector: app=genaidemo-frontend
- image: REPLACE_WITH_ACR_LOGIN_SERVER/genaidemo-frontend:latest
- resources:
    requests: cpu=100m, memory=256Mi
    limits:   cpu=500m, memory=512Mi
- readinessProbe: httpGet / port 3000
    initialDelaySeconds: 10, periodSeconds: 10
- livenessProbe: httpGet / port 3000
    initialDelaySeconds: 20, periodSeconds: 30
- env:
    - name: NEXT_PUBLIC_API_URL
      valueFrom: configMapKeyRef genaidemo-config NEXT_PUBLIC_API_URL

### services.yaml
- Service genaidemo-backend:
    type: ClusterIP
    port: 8000, targetPort: 8000
    selector: app=genaidemo-backend
- Service genaidemo-frontend:
    type: LoadBalancer
    port: 80, targetPort: 3000
    selector: app=genaidemo-frontend

---

## DELIVERABLE 4 — Infrastructure Validation Tests

### tests/integration/conftest.py
- session-scoped fixture: azure_credential() → DefaultAzureCredential
- session-scoped fixture: secret_client(azure_credential) → SecretClient
  reads KEY_VAULT_URI from env var (fail fast with clear message if missing)
- session-scoped fixture: cosmos_client(secret_client) → CosmosClient
  reads connection string from Key Vault secret COSMOS-DB-CONNECTION-STRING
- function-scoped fixture: conversations_container(cosmos_client)
  returns the container client for database=genaidemo-db, container=conversations
- Required env vars (assert at session start with clear error messages):
    KEY_VAULT_URI, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
    COSMOS_DB_ENDPOINT, REDIS_SSL_PORT, ACR_NAME, RESOURCE_GROUP

### tests/integration/test_infra.py
Use pytest. All credentials from fixtures in conftest.py. Never hardcode values.
Write these test functions with full docstrings:

1. test_keyvault_reachable(secret_client)
   """Verify Key Vault is accessible and the CSI secrets exist."""
   - List secrets properties (first page only)
   - Assert no exception is raised
   - Assert COSMOS-DB-CONNECTION-STRING exists in the list

2. test_keyvault_secrets_complete(secret_client)
   """Verify all required secrets are present in Key Vault."""
   - Check each of these secret names exists (get_secret by name):
       COSMOS-DB-CONNECTION-STRING, REDIS-ACCESS-KEY, REDIS-HOST,
       AZURE-AD-CLIENT-ID, AZURE-AD-CLIENT-SECRET, AZURE-AD-TENANT-ID,
       AZURE-OPENAI-KEY
   - Collect all missing secrets and fail with a clear list if any are missing

3. test_cosmosdb_crud(conversations_container)
   """Verify Cosmos DB CRUD operations on the conversations container."""
   - Create item: {"id": "infra-test-001", "user_id": "infra-test",
                   "content": "ping", "timestamp": <ISO 8601 now>}
   - Read it back: assert item["id"] == "infra-test-001"
   - Delete it: conversations_container.delete_item("infra-test-001",
                                                    partition_key="infra-test")
   - Confirm deletion: read again, expect CosmosResourceNotFoundError

4. test_redis_connectivity(secret_client)
   """Verify Redis TLS connectivity and basic SET/GET/DEL operations."""
   - Read REDIS-ACCESS-KEY and REDIS-HOST from Key Vault
   - Connect: redis.StrictRedis(host, port=int(REDIS_SSL_PORT),
                                password=access_key, ssl=True,
                                ssl_cert_reqs=None, decode_responses=True)
   - SET "infra-test-key" "hello-genaidemo"
   - GET "infra-test-key" → assert == "hello-genaidemo"
   - DEL "infra-test-key"
   - Assert key no longer exists (GET returns None)

5. test_acr_reachable(azure_credential)
   """Verify ACR exists and is reachable via management API."""
   - Use ContainerRegistryManagementClient with DefaultAzureCredential
   - Read ACR_NAME and RESOURCE_GROUP from env vars
   - Call registries.get(resource_group, acr_name)
   - Assert registry.provisioning_state == 'Succeeded'
   - This test PASSES even if no images exist yet

---

## DELIVERABLE 5 — Helper Scripts  (ops/scripts/)

### ops/scripts/deploy.ps1
PowerShell deployment script. Requirements:
- Parameters: -Environment (Mandatory, ValidateSet dev,staging),
              -ResourceGroup (Mandatory),
              -Location (default 'eastus2')
- Header comment block with project metadata
- Login check: az account show --output none 2>&1
  if exit code != 0: Write-Error "Not logged in. Run: az login" and exit 1
- Show subscription info before deploying (az account show --output table)
- Deployment name: "genaidemo-$Environment-$(Get-Date -Format 'yyyyMMddHHmm')"
- Run: az deployment group create
         --resource-group $ResourceGroup
         --template-file ops/bicep/main.bicep
         --parameters ops/bicep/parameters/$Environment.bicepparam
         --name $DeploymentName
         --output json
- On success: parse JSON output and print all outputs as a formatted table
  using Format-Table
- On failure: print [ERROR] Deployment failed. Check Azure Portal for details.
  and exit 1
- Execution time: measure with Measure-Command and print at the end

### ops/scripts/validate_infra.py
Python script (not pytest) that:
- Runs all integration tests via subprocess calling pytest with --json-report
- Parses the JSON report
- Generates docs/sprint_0/validation.md with:
    # Sprint 0 — Validation Report
    Generated: <timestamp>
    Environment: <from ENV var or 'dev'>

    ## Test Results
    | Test Name | Status | Duration (s) | Notes |
    |-----------|--------|--------------|-------|
    | ...       | PASS   | 1.23         |       |

    ## Sign-off Checklist
    - [ ] All resources in Succeeded state in Azure Portal
    - [ ] All integration tests PASS
    - [ ] Pipeline CI/CD executed end-to-end without errors
    - [ ] Entra ID login validated from web app
    - [ ] Key Vault secrets populated
    - [ ] Tech Lead sign-off: _________________________ Date: _______
- Prints PASS / FAIL summary to stdout with counts
- Exit code 0 if all tests pass, 1 otherwise

### ops/scripts/init_structure.ps1
PowerShell script that:
- Header comment block
- Creates every folder in the vibecoding structure using New-Item -ItemType Directory -Force
  (idempotent — -Force does not fail if folder exists)
- Creates .gitkeep in each leaf folder using New-Item -ItemType File -Force
- Counts: how many folders were already existing vs newly created
- Prints a summary table: Folder | Status (Created / Already existed)
- At the end: [OK] Structure initialized. X new folders created, Y already existed.

---

## DELIVERABLE 6 — Sprint 0 Documentation  (docs/sprint_0/)

### docs/sprint_0/backlog.md
```markdown
# Sprint 0 — Backlog

**Sprint Goal:** Provision the complete Azure base infrastructure for GenAIDemo
so that subsequent sprints can deploy application code immediately.

**Duration:** 2 weeks  
**Story Points:** 37 (34 Must Have · 3 Should Have)  
**Engineer:** Andrés Felipe Rojas Parra

## PBIs in Scope

| ID      | Title                                    | Points | Priority    |
|---------|------------------------------------------|--------|-------------|
| PBI-001 | Bicep scaffold (ops/bicep/ structure)    | 3      | Must Have   |
| PBI-002 | Azure Key Vault                          | 3      | Must Have   |
| PBI-003 | Azure Container Registry                 | 2      | Must Have   |
| PBI-004 | Azure Cosmos DB                          | 5      | Must Have   |
| PBI-005 | Azure Cache for Redis                    | 3      | Should Have |
| PBI-006 | Entra ID App Registration                | 5      | Must Have   |
| PBI-007 | CI Pipeline (azure-pipelines.yml)        | 5      | Must Have   |
| PBI-008 | CD Pipeline (AKS deploy)                 | 5      | Must Have   |
| PBI-009 | Repo structure (vibecoding)              | 3      | Must Have   |
| PBI-010 | Infra validation tests + sign-off        | 3      | Must Have   |
```

### docs/sprint_0/validation.md
```markdown
# Sprint 0 — Validation & Sign-off

**Environment:** dev  
**Date:** _____________  
**Engineer:** Andrés Felipe Rojas Parra

## Integration Test Results

| Test Name                      | Status | Duration (s) | Notes |
|--------------------------------|--------|--------------|-------|
| test_keyvault_reachable        |        |              |       |
| test_keyvault_secrets_complete |        |              |       |
| test_cosmosdb_crud             |        |              |       |
| test_redis_connectivity        |        |              |       |
| test_acr_reachable             |        |              |       |

## Azure Resources Checklist

- [ ] genaidemo-kv-dev       — Key Vault          — Succeeded
- [ ] genaidemo-acr-dev      — Container Registry — Succeeded
- [ ] genaidemo-cosmos-dev   — Cosmos DB          — Succeeded
- [ ] genaidemo-redis-dev    — Redis Cache        — Succeeded
- [ ] genaidemo-aks-dev      — AKS Cluster        — Succeeded

## Pipeline Checklist

- [ ] Stage: validate — PASS
- [ ] Stage: build    — PASS
- [ ] Stage: push     — PASS
- [ ] Stage: deploy   — PASS
- [ ] Pods Running in namespace genaidemo-dev

## Sign-off

Tech Lead: _________________________ Date: _______
```

### docs/sprint_0/decisions.md
```markdown
# Sprint 0 — Decisions & Notes

## ADR-001: Cosmos DB Serverless for dev environment
**Date:** 2026-07  
**Status:** Accepted  
**Decision:** Use EnableServerless capability for the dev Cosmos DB account.  
**Rationale:** Zero cost when idle; dev workloads are intermittent.  
**Consequence:** Serverless cannot be combined with multi-region writes.
Switch to provisioned throughput (400 RU/s auto-scale) for staging/prod.

## ADR-002: Key Vault RBAC authorization model
**Date:** 2026-07  
**Status:** Accepted  
**Decision:** enableRbacAuthorization: true on Key Vault (no legacy access policies).  
**Rationale:** RBAC is the current Microsoft recommended approach; provides
audit trail via Azure Activity Log; integrates with PIM for just-in-time access.  
**Consequence:** All access must be granted via role assignments
(Key Vault Secrets Officer / User), not access policy entries.

## Sprint Notes

<!-- Add meeting notes, blockers, and decisions made during Sprint 0 here -->
```

---

## DELIVERABLE 7 — Makefile (cross-platform: Windows 11 Git Bash + Ubuntu 24.04)

### Critical cross-platform rules — violations will break Windows Git Bash
- Use echo "" instead of echo. (echo. is cmd.exe only and fails in sh.exe)
- Use forward slashes in ALL paths (ops/bicep/main.bicep, never ops\bicep)
- Use mkdir -p (never md or mkdir without -p)
- Use rm -rf (never del or rmdir /s)
- NEVER use ANSI escape codes (\033[...) — use plain text prefixes:
  [INFO], [OK], [ERROR], [WARN]
- Use $(shell ...) for command substitution, never backticks
- Use ifeq ($(OS),Windows_NT) only when strictly necessary;
  prefer portable sh commands over OS branches
- Do NOT use .ONESHELL — behavior differs across make versions on Windows
- Each recipe line is a separate shell invocation;
  use && to chain commands that must share state within one line
- Quote paths that may contain spaces: "$(BICEP_MAIN)"

### Variables block
```makefile
PROJECT      := genaidemo
ENV          ?= dev
RG           ?= rg-$(PROJECT)-$(ENV)
LOCATION     ?= eastus2
BICEP_MAIN   := ops/bicep/main.bicep
PARAMS       := ops/bicep/parameters/$(ENV).bicepparam
ACR_NAME     := $(PROJECT)acr$(ENV)
BACKEND_IMG  := $(ACR_NAME).azurecr.io/$(PROJECT)-backend
FRONTEND_IMG := $(ACR_NAME).azurecr.io/$(PROJECT)-frontend
PYTHON       := python
PYTEST       := pytest
SPRINT       ?=
```

### Required targets with exact descriptions for help output

```
help           Show all available targets and their descriptions
infra-lint     Run az bicep lint on main.bicep
infra-whatif   Dry-run Bicep deployment (az deployment group what-if)
infra-deploy   Deploy Bicep to Azure  (usage: make infra-deploy ENV=dev RG=rg-genaidemo-dev)
infra-destroy  DESTRUCTIVE: delete the resource group after confirmation prompt
docker-build   Build backend and frontend Docker images locally
docker-push    Login to ACR and push both images  (usage: make docker-push ENV=dev)
k8s-deploy     Apply all Kubernetes manifests in ops/k8s/ in correct order
k8s-status     Show pods, services, and configmaps in genaidemo-$(ENV) namespace
test-unit      Run tests/unit/ with pytest
test-infra     Run tests/integration/test_infra.py with pytest
test-all       Run test-unit then test-infra sequentially
pipeline-lint  Validate azure-pipelines.yml (requires az devops extension)
init           Initialize folder structure via ops/scripts/init_structure.ps1
docs-sprint    Create docs/sprint_$(SPRINT)/ with standard templates
               usage: make docs-sprint SPRINT=1
clean          Remove __pycache__, .pytest_cache, *.pyc, dist/, .next/
format         Run ruff format on src/ and tests/
lint           Run ruff check on src/ and tests/
```

### Special rules for docs-sprint target
- If SPRINT is not set: print [ERROR] SPRINT is required. Usage: make docs-sprint SPRINT=1
  and exit with code 1
- mkdir -p docs/sprint_$(SPRINT)
- For each of the three template files, use a shell guard to avoid overwriting:
    test -f docs/sprint_$(SPRINT)/backlog.md || echo "# Sprint $(SPRINT) — Backlog" > docs/sprint_$(SPRINT)/backlog.md
    test -f docs/sprint_$(SPRINT)/validation.md || echo "# Sprint $(SPRINT) — Validation & Sign-off" > docs/sprint_$(SPRINT)/validation.md
    test -f docs/sprint_$(SPRINT)/decisions.md || echo "# Sprint $(SPRINT) — Decisions & Notes" > docs/sprint_$(SPRINT)/decisions.md
- Print [OK] docs/sprint_$(SPRINT)/ ready with standard templates

### infra-destroy target
- Print [WARN] This will DELETE resource group $(RG) and ALL resources inside it.
- Prompt for confirmation: read -p "Type the resource group name to confirm: " confirm
- Compare: if [ "$$confirm" != "$(RG)" ]; then echo "[ERROR] Aborted."; exit 1; fi
- Run: az group delete --name $(RG) --yes --no-wait
- Print [INFO] Deletion initiated. Monitor in Azure Portal.

### .PHONY declaration
Declare ALL targets as .PHONY (one line listing all target names).

### help target implementation
Parse ## comments from the Makefile itself using this portable pattern:
```makefile
help:
	@grep -E "^[a-zA-Z_-]+:.*?## .*$$" $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'
```
Every target must have an inline ## comment on the same line as the target definition.

---

## START INSTRUCTIONS — execute in this exact order

1. Create docs/sprint_0/ and populate backlog.md, validation.md, decisions.md
   with the content specified in Deliverable 6.

2. Create ALL other files as stubs (header comment block only) so the
   full folder structure is visible from the start.

3. Generate azure-pipelines.yml and all four pipeline templates in full.

4. Generate all six Kubernetes manifests in ops/k8s/ in full.

5. Generate tests/integration/conftest.py and test_infra.py in full.

6. Generate ops/scripts/deploy.ps1, validate_infra.py,
   and init_structure.ps1 in full.

7. Generate the Makefile in full with all targets and cross-platform rules.

8. STOP before writing any content into the five .bicep files.
   Print the following checklist and wait:

---
[READY] All non-Bicep files generated. Awaiting Bicep module specifications.

Files created:
[ ] azure-pipelines.yml
[ ] azure-pipelines/templates/build-backend.yml
[ ] azure-pipelines/templates/build-frontend.yml
[ ] azure-pipelines/templates/push-acr.yml
[ ] azure-pipelines/templates/deploy-aks.yml
[ ] Makefile
[ ] ops/k8s/namespace.yaml
[ ] ops/k8s/configmap.yaml
[ ] ops/k8s/secret-provider.yaml
[ ] ops/k8s/backend-deployment.yaml
[ ] ops/k8s/frontend-deployment.yaml
[ ] ops/k8s/services.yaml
[ ] ops/bicep/main.bicep                ← STUB only, awaiting your spec
[ ] ops/bicep/modules/keyvault.bicep    ← STUB only, awaiting your spec
[ ] ops/bicep/modules/acr.bicep         ← STUB only, awaiting your spec
[ ] ops/bicep/modules/cosmosdb.bicep    ← STUB only, awaiting your spec
[ ] ops/bicep/modules/redis.bicep       ← STUB only, awaiting your spec
[ ] ops/bicep/modules/aks.bicep         ← STUB only, awaiting your spec
[ ] ops/bicep/parameters/dev.bicepparam ← STUB only, awaiting your spec
[ ] ops/bicep/parameters/staging.bicepparam ← STUB only, awaiting your spec
[ ] ops/scripts/deploy.ps1
[ ] ops/scripts/validate_infra.py
[ ] ops/scripts/init_structure.ps1
[ ] tests/integration/conftest.py
[ ] tests/integration/test_infra.py
[ ] docs/sprint_0/backlog.md
[ ] docs/sprint_0/validation.md
[ ] docs/sprint_0/decisions.md

Please provide the Bicep specification for each module.
Start with: main.bicep
---