# Sprint 0 — Infraestructura, IaC y CI/CD

## Estado General

All Sprint 0 non-Bicep deliverables are complete. Steps 1–6 from the initial prompt are done; step 7 (Bicep module content) is intentionally on hold per the prompt's explicit instruction to wait for module specs.

---

## Checklist de Archivos Creados

### Bicep folder structure (stubs only — awaiting module specs)

- `ops/bicep/main.bicep`
- `ops/bicep/modules/keyvault.bicep`
- `ops/bicep/modules/acr.bicep`
- `ops/bicep/modules/cosmosdb.bicep`
- `ops/bicep/modules/redis.bicep`
- `ops/bicep/modules/aks.bicep`
- `ops/bicep/parameters/dev.bicepparam`
- `ops/bicep/parameters/staging.bicepparam`

### CI/CD pipeline

- `azure-pipelines.yml`
- `azure-pipelines/templates/build-backend.yml`
- `azure-pipelines/templates/build-frontend.yml`
- `azure-pipelines/templates/push-acr.yml`
- `azure-pipelines/templates/deploy-aks.yml`

### Kubernetes manifests

- `ops/k8s/namespace.yaml`
- `ops/k8s/configmap.yaml`
- `ops/k8s/secret-provider.yaml`
- `ops/k8s/backend-deployment.yaml`
- `ops/k8s/frontend-deployment.yaml`
- `ops/k8s/services.yaml`

### Infra validation tests

- `tests/integration/test_infra.py`
- `tests/integration/conftest.py`

### Helper scripts

- `ops/scripts/deploy.ps1`
- `ops/scripts/validate_infra.py`
- `ops/scripts/init_structure.ps1`

### Sprint docs

- `docs/sprint_0/README.md` (deliverables + log)

---

## PBI-06

### Files Created or Modified

| File Name | Description |
|---|---|
| `azure-pipelines.yml` | Replaced stub with full validate→build→push→deploy pipeline |
| `azure-pipelines/templates/*.yml` | Backend/frontend build, ACR push, AKS deploy w/ rollback |
| `ops/k8s/*.yaml` | Namespace, configmap, CSI secret provider, deployments, services |
| `tests/integration/test_infra.py`, `conftest.py` | 5 pytest tests + shared Azure credential/secret-client fixtures |
| `ops/scripts/deploy.ps1` | Bicep deployment script with login check + formatted output table |
| `ops/scripts/validate_infra.py` | Runs pytest, writes Markdown report to `docs/architecture/` |
| `ops/scripts/init_structure.ps1` | Idempotent folder/.gitkeep initializer |
| `ops/bicep/**/*.bicep`, `*.bicepparam` | Header-only stubs, content withheld pending specs |
| `docs/sprint_0/README.md` | Deliverables checklist + log |

### Validation Performed

| Item | Description |
|---|---|
| `ruff check` | Passed on all 3 new Python files (`test_infra.py`, `conftest.py`, `validate_infra.py`) |
| Bicep/pytest execution | Not run — no live Azure resources/credentials in this environment |

### What the module does

CI/CD pipeline builds and deploys the backend/frontend containers to AKS dev with a smoke-test-gated rollback; K8s manifests define the dev namespace's workloads and Key Vault CSI secret mounting; integration tests validate Key Vault, Cosmos DB, Redis, and ACR reachability post-deploy.

### Risks / Blockers

- No `pyproject.toml` exists yet in the repo, so `azure-identity`, `azure-cosmos`, `azure-keyvault-secrets`, `azure-mgmt-containerregistry`, and `redis` aren't declared as dependencies — needed before tests can actually run. Flagging rather than creating, since it's outside this sprint's explicit file list.
- `test_acr_image_pullable` uses `ContainerRegistryManagementClient.registries.get(...)` rather than a repository listing, since repo listing is a data-plane API not exposed by `azure-mgmt-containerregistry` — functionally validates reachability/auth as the spec intended, but isn't a literal repo list.
- Bicep deliverable (D1) is blocked — waiting for module specs as noted in the initial prompt.

---

## PBI-07/08 — Bicep IaC Completo + `.env`

### Files Created or Modified

| File Name | Description |
|---|---|
| `ops/bicep/main.bicep` | Orchestrator: calls keyvault→acr→cosmosdb→redis→aks in dependency order, wires outputs |
| `ops/bicep/modules/keyvault.bicep` | RBAC-only Key Vault, soft-delete + purge protection, dev/prod network ACL split |
| `ops/bicep/modules/acr.bicep` | Standard SKU ACR, admin disabled, zone redundancy on for prod |
| `ops/bicep/modules/cosmosdb.bicep` | Serverless NoSQL account, genaidemo-db/conversations container, writes connection string to Key Vault |
| `ops/bicep/modules/redis.bicep` | TLS-only Standard cache, writes access key + host:port to Key Vault |
| `ops/bicep/modules/aks.bicep` | Autoscaling AKS (1.29), Key Vault CSI addon, AcrPull role assignment to kubelet identity |
| `ops/bicep/parameters/dev.bicepparam` | Dev environment parameter values |
| `ops/bicep/parameters/staging.bicepparam` | Staging environment parameter values |
| `.env.example`, `.env` | Local dev config template + gitignored local copy |
| `docs/sprint_0/README.md` | Marked D1 complete, appended log entries |

### Validation Performed

| Item | Description |
|---|---|
| `az bicep build --file ops/bicep/main.bicep` | Compiles successfully after fixing an AcrPull role-assignment scope error (needed an existing resource reference instead of a raw `resourceId()` string). 3 remaining cosmetic lint warnings (environment param unused in redis/cosmosdb/aks modules — kept for signature consistency across modules per spec) |
| No live `az deployment group what-if` | Not run — no Azure subscription/credentials in this environment |

### What the module does

Bicep IaC provisions the full dev/staging foundation — Key Vault, ACR, serverless Cosmos DB, TLS Redis, and an autoscaling AKS cluster with AcrPull wired to its kubelet identity — with all connection secrets written to Key Vault rather than exposed as outputs.

### Risks / Blockers

- `.env` was created with empty secret values as a local placeholder; it's already gitignored, but you'll need to fill in real subscription/tenant/client IDs before running anything against Azure.
- Never actually deployed — `what-if` and a real `deploy.ps1` run are the next validation step once you have a resource group and credentials.
- `pyproject.toml` still doesn't exist (flagged previously) — needed before `tests/integration/test_infra.py` can run.

---

## PBI-09 — `.gitignore` y `pyproject.toml`

### Files Created or Modified

| File Name | Description |
|---|---|
| `pyproject.toml` | Renamed project to `genaidemo`; added runtime deps matching CLAUDE.md stack (FastAPI, Semantic Kernel, Azure Identity/KeyVault/Cosmos/Search/ACR mgmt/Monitor, redis, python-jose, msal), dev deps (ruff/black/pytest/pytest-asyncio/pytest-cov), and a 70%-coverage gate under `[tool.coverage]` |
| `.gitignore` | Added `*.pyc`, `.env.*.local`, pytest/coverage artifacts, node_modules/frontend build output, compiled Bicep JSON, and IDE/OS junk |
| `docs/sprint_0/README.md` | Appended PBI-09 log entry |

### Validation Performed

| Item | Description |
|---|---|
| `ruff check` | Passed on `tests/integration` and `ops/scripts/validate_infra.py` after `pyproject.toml` change |
| `pip/uv sync` | Not run — no venv in this environment; dependency versions are unpinned floors, not lockfile-verified |

### What the module does

Declares the actual GenAIDemo Python dependency set (replacing the generic template stub) and keeps generated/local artifacts out of git.

### Risks / Blockers

- No lockfile exists yet (`uv.lock` / `requirements.txt`) — CI's `uv sync --frozen --no-dev` in `build-backend.yml` will fail until one is generated with `uv lock`.
- Dependency versions are floors (`>=`), not exact pins — first `uv sync` should be reviewed before relying on it for reproducible builds.
