# Sprint 0 — Base Infrastructure

Goal: production-grade Azure infrastructure foundation for GenAIDemo, deployable
with a single command per environment.

## Deliverables

- [x] D1: Azure Bicep IaC (main.bicep + modules)
- [x] D2: Azure DevOps CI/CD pipeline (azure-pipelines.yml + templates)
- [x] D3: Kubernetes manifests (ops/k8s/)
- [x] D4: Infrastructure validation tests (tests/integration/test_infra.py + conftest.py)
- [x] D5: Helper scripts (ops/scripts/deploy.ps1, validate_infra.py)
- [x] D6: Repository initialization script (ops/scripts/init_structure.ps1)

## Deliverable Log

- PBI-01: CI/CD pipeline (azure-pipelines.yml, build/push/deploy templates) — 2026-07-14
- PBI-02: Kubernetes manifests for genaidemo-dev namespace — 2026-07-14
- PBI-03: Infrastructure integration tests + conftest fixtures — 2026-07-14
- PBI-04: Helper scripts (deploy.ps1, validate_infra.py) — 2026-07-14
- PBI-05: Repository structure initialization script — 2026-07-14
- PBI-06: Bicep folder/module stubs created; awaiting module specs from user — 2026-07-14
- PBI-07: Full Bicep implementation (main.bicep + keyvault/acr/cosmosdb/redis/aks modules, dev/staging params) authored by Claude per initial_prompt.md spec — 2026-07-14
- PBI-08: .env and .env.example created for local dev configuration — 2026-07-14
- PBI-09: pyproject.toml populated with GenAIDemo dependencies (FastAPI, Semantic Kernel, Azure SDKs, 70% coverage gate) and .gitignore extended for coverage/node/bicep-json/IDE artifacts — 2026-07-14

## Development Setup

### Creating a Python virtual environment with uv

This project uses `uv` for environment and dependency management, with `pyproject.toml` and `uv.lock` as the source of truth.

1. Install uv (if not already installed):
   ```powershell
   irm https://astral.sh/uv/install.ps1 | iex
   ```
2. From the project root (where `pyproject.toml` lives), create the virtual environment:
   ```powershell
   uv venv
   ```
3. Activate the environment:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
4. Install dependencies from the lockfile:
   ```powershell
   uv sync
   ```
5. Verify the environment:
   ```powershell
   uv run python --version
   ```
