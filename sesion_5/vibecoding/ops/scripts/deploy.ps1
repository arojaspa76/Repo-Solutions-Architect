# Project:     GenAIDemo
# Component:   Deployment script
# Description: Deploys the Bicep infrastructure template to a target environment
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('dev', 'staging')]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $true)]
    [string]$Location
)

$ErrorActionPreference = 'Stop'

$account = az account show 2>$null
if (-not $account) {
    Write-Host "FAIL: not logged in to Azure. Run 'az login' first." -ForegroundColor Red
    exit 1
}

$deploymentName = "genaidemo-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmm')"
$templateFile = "ops/bicep/main.bicep"
$parametersFile = "ops/bicep/parameters/$Environment.bicepparam"

try {
    $result = az deployment group create `
        --resource-group $ResourceGroup `
        --template-file $templateFile `
        --parameters $parametersFile `
        --name $deploymentName `
        --output json | ConvertFrom-Json

    if ($LASTEXITCODE -ne 0) {
        throw "az deployment group create exited with code $LASTEXITCODE"
    }

    Write-Host "`nDeployment outputs:" -ForegroundColor Cyan
    $result.properties.outputs.PSObject.Properties | ForEach-Object {
        [PSCustomObject]@{
            Output = $_.Name
            Value  = $_.Value.value
        }
    } | Format-Table -AutoSize

    Write-Host "`nPASS: deployment '$deploymentName' succeeded." -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "`nFAIL: deployment '$deploymentName' failed. $_" -ForegroundColor Red
    exit 1
}
