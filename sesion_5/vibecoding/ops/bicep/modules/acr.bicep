// Project:     GenAIDemo
// Component:   Container Registry module
// Description: Azure Container Registry for GenAIDemo backend/frontend images
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

@description('Name of the Azure Container Registry.')
@minLength(5)
@maxLength(50)
param name string

@description('Azure region for the ACR.')
param location string

@description('Deployment environment (dev, staging, production).')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string

@description('Resource tags applied to the ACR.')
param tags object

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    zoneRedundancy: environment == 'production' ? 'Enabled' : 'Disabled'
    publicNetworkAccess: 'Enabled'
  }
}

@description('Name of the deployed ACR.')
output acrName string = acr.name

@description('Login server FQDN of the deployed ACR.')
output acrLoginServer string = acr.properties.loginServer

@description('Resource ID of the deployed ACR, used for role assignments.')
output acrId string = acr.id
