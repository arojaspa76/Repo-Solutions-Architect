# Project:     GenAIDemo
# Component:   Makefile
# Description: Cross-platform developer entrypoint (Windows 11 Git Bash + Ubuntu 24.04)
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

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

.PHONY: help infra-lint infra-whatif infra-deploy infra-destroy docker-build docker-push k8s-deploy k8s-status test-unit test-infra test-all pipeline-lint init docs-sprint clean format lint

help: ## Show all available targets and their descriptions
	@grep -E "^[a-zA-Z0-9_-]+:.*?## .*$$" $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

infra-lint: ## Run az bicep lint on main.bicep
	az bicep lint --file "$(BICEP_MAIN)"

infra-whatif: ## Dry-run Bicep deployment (az deployment group what-if)
	az deployment group what-if --resource-group "$(RG)" --template-file "$(BICEP_MAIN)" --parameters "$(PARAMS)"

infra-deploy: ## Deploy Bicep to Azure  (usage: make infra-deploy ENV=dev RG=rg-genaidemo-dev)
	az deployment group create --resource-group "$(RG)" --template-file "$(BICEP_MAIN)" --parameters "$(PARAMS)"

infra-destroy: ## DESTRUCTIVE: delete the resource group after confirmation prompt
	@echo "[WARN] This will DELETE resource group $(RG) and ALL resources inside it."
	@read -p "Type the resource group name to confirm: " confirm; \
	if [ "$$confirm" != "$(RG)" ]; then echo "[ERROR] Aborted."; exit 1; fi
	az group delete --name "$(RG)" --yes --no-wait
	@echo "[INFO] Deletion initiated. Monitor in Azure Portal."

docker-build: ## Build backend and frontend Docker images locally
	docker build -t "$(BACKEND_IMG):latest" -f apps/api/Dockerfile .
	docker build -t "$(FRONTEND_IMG):latest" -f apps/web/Dockerfile .

docker-push: ## Login to ACR and push both images  (usage: make docker-push ENV=dev)
	az acr login --name "$(ACR_NAME)"
	docker push "$(BACKEND_IMG):latest"
	docker push "$(FRONTEND_IMG):latest"

k8s-deploy: ## Apply all Kubernetes manifests in ops/k8s/ in correct order
	kubectl apply -f ops/k8s/namespace.yaml
	kubectl apply -f ops/k8s/configmap.yaml
	kubectl apply -f ops/k8s/secret-provider.yaml
	kubectl apply -f ops/k8s/backend-deployment.yaml
	kubectl apply -f ops/k8s/frontend-deployment.yaml
	kubectl apply -f ops/k8s/services.yaml

k8s-status: ## Show pods, services, and configmaps in genaidemo-$(ENV) namespace
	kubectl get pods,svc,configmap -n "$(PROJECT)-$(ENV)"

test-unit: ## Run tests/unit/ with pytest
	$(PYTEST) tests/unit

test-infra: ## Run tests/integration/test_infra.py with pytest
	$(PYTEST) tests/integration/test_infra.py

test-all: ## Run test-unit then test-infra sequentially
	$(MAKE) test-unit
	$(MAKE) test-infra

pipeline-lint: ## Validate azure-pipelines.yml (requires az devops extension)
	az pipelines runs list --output none 2>&1 && az devops invoke --area build --resource yamlDefinition --route-parameters project="Proyectos AI" || echo "[WARN] az devops extension not configured"

init: ## Initialize folder structure via ops/scripts/init_structure.ps1
	pwsh -File ops/scripts/init_structure.ps1

docs-sprint: ## Create docs/sprint_$(SPRINT)/ with standard templates
               ## usage: make docs-sprint SPRINT=1
	@if [ -z "$(SPRINT)" ]; then echo "[ERROR] SPRINT is required. Usage: make docs-sprint SPRINT=1"; exit 1; fi
	mkdir -p docs/sprint_$(SPRINT)
	test -f docs/sprint_$(SPRINT)/backlog.md || echo "# Sprint $(SPRINT) — Backlog" > docs/sprint_$(SPRINT)/backlog.md
	test -f docs/sprint_$(SPRINT)/validation.md || echo "# Sprint $(SPRINT) — Validation & Sign-off" > docs/sprint_$(SPRINT)/validation.md
	test -f docs/sprint_$(SPRINT)/decisions.md || echo "# Sprint $(SPRINT) — Decisions & Notes" > docs/sprint_$(SPRINT)/decisions.md
	@echo "[OK] docs/sprint_$(SPRINT)/ ready with standard templates"

clean: ## Remove __pycache__, .pytest_cache, *.pyc, dist/, .next/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache dist .next
	find . -type f -name "*.pyc" -delete

format: ## Run ruff format on src/ and tests/
	ruff format src/ tests/

lint: ## Run ruff check on src/ and tests/
	ruff check src/ tests/
