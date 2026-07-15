# Project:     GenAIDemo
# Component:   Repository initialization script
# Description: Idempotently creates the vibecoding folder structure with .gitkeep placeholders
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$folders = @(
    "ops/bicep/modules",
    "ops/bicep/parameters",
    "ops/k8s",
    "ops/docker",
    "ops/scripts",
    "azure-pipelines/templates",
    "apps/api/src/middleware",
    "apps/api/src/routers",
    "apps/web/src/auth",
    "apps/web/src/components",
    "apps/web/src/hooks",
    "apps/web/src/locales",
    "apps/web/src/constants",
    "src/agents/tools",
    "src/common",
    "src/config",
    "src/core",
    "src/data/synthetic",
    "src/domain",
    "src/observability",
    "src/pipelines",
    "src/rag",
    "src/services",
    "configs/prompts/agents",
    "configs/security",
    "data/raw",
    "data/interim",
    "data/processed/rag_eval",
    "data/external",
    "docs/architecture",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
    "tests/load"
)

$created = 0
$existing = 0

foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        $created++
    }
    else {
        $existing++
    }

    $gitkeep = Join-Path $folder ".gitkeep"
    if (-not (Test-Path $gitkeep)) {
        New-Item -ItemType File -Path $gitkeep | Out-Null
    }
}

Write-Host "`nRepository structure initialization summary:" -ForegroundColor Cyan
Write-Host "  Folders created:         $created"
Write-Host "  Folders already existed: $existing"
Write-Host "  Total folders processed: $($folders.Count)"
