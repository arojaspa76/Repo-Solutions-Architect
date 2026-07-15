// Project:     GenAIDemo
// Component:   AKS module
// Description: AKS cluster hosting GenAIDemo backend/frontend workloads
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

@description('Name of the AKS cluster.')
@minLength(1)
@maxLength(63)
param name string

@description('Azure region for the AKS cluster.')
param location string

@description('Deployment environment (dev, staging, production).')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string

@description('Resource tags applied to the AKS cluster.')
param tags object

@description('Resource ID of the ACR the AKS kubelet identity needs AcrPull access to.')
param acrId string

@description('Kubernetes version for the AKS cluster.')
param kubernetesVersion string = '1.29'

@description('VM size for the default node pool.')
param nodeVmSize string = 'Standard_D2s_v3'

@description('Initial node count for the default node pool.')
param nodeCount int = 2

@description('Minimum node count for cluster autoscaling.')
param minNodeCount int = 2

@description('Maximum node count for cluster autoscaling.')
param maxNodeCount int = 5

@description('DNS prefix for the AKS cluster API server.')
param dnsPrefix string = '${name}-dns'

var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')

resource aks 'Microsoft.ContainerService/managedClusters@2024-02-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: dnsPrefix
    agentPoolProfiles: [
      {
        name: 'systempool'
        count: nodeCount
        vmSize: nodeVmSize
        mode: 'System'
        enableAutoScaling: true
        minCount: minNodeCount
        maxCount: maxNodeCount
        osType: 'Linux'
        type: 'VirtualMachineScaleSets'
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
    }
    oidcIssuerProfile: {
      enabled: true
    }
    addonProfiles: {
      azureKeyvaultSecretsProvider: {
        enabled: true
        config: {
          enableSecretRotation: 'true'
        }
      }
    }
  }
}

resource acrRef 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: last(split(acrId, '/'))
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, aks.id, acrPullRoleDefinitionId)
  scope: acrRef
  properties: {
    roleDefinitionId: acrPullRoleDefinitionId
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the deployed AKS cluster.')
output aksClusterName string = aks.name

@description('OIDC issuer URL of the deployed AKS cluster.')
output aksOidcIssuerUrl string = aks.properties.oidcIssuerProfile.issuerURL

@description('Principal ID of the AKS managed identity.')
output aksManagedIdentityPrincipalId string = aks.identity.principalId
