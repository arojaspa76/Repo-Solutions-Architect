// Project:     GenAIDemo
// Component:   Key Vault module
// Description: RBAC-authorized Key Vault for storing GenAIDemo secrets
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

@description('Name of the Key Vault resource.')
@minLength(3)
@maxLength(24)
param name string

@description('Azure region for the Key Vault.')
param location string

@description('Deployment environment (dev, staging, production).')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string

@description('Resource tags applied to the Key Vault.')
param tags object

@description('Tenant ID used for RBAC authorization.')
param tenantId string = subscription().tenantId

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: environment == 'production' ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: environment == 'production' ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
  }
}

@description('Name of the deployed Key Vault.')
output keyVaultName string = keyVault.name

@description('URI of the deployed Key Vault.')
output keyVaultUri string = keyVault.properties.vaultUri
