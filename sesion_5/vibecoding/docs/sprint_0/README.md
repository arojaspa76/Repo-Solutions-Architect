# Sprint 0 — Base Infrastructure

Goal: production-grade Azure infrastructure foundation for GenAIDemo, deployable
with a single command per environment.

## Deliverables

- [ ] D1: Azure Bicep IaC (main.bicep + modules) — **blocked, awaiting module specs**
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
