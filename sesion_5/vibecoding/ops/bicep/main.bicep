// Project:     GenAIDemo
// Component:   Bicep orchestrator
// Description: Deploys the GenAIDemo base infrastructure (Key Vault, ACR, Cosmos DB, Redis, AKS)
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

targetScope = 'resourceGroup'

@description('Short project name used to compose resource names.')
param projectName string = 'genaidemo'

@description('Deployment environment.')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string

@description('Azure region for all resources.')
param location string

@description('Resource tags applied to every resource in this deployment.')
param tags object = {
  project: 'GenAIDemo'
  environment: environment
  managedBy: 'Bicep'
  owner: 'andres.rojas@techcorp.com'
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'deploy-keyvault'
  params: {
    name: '${projectName}-kv-${environment}'
    location: location
    environment: environment
    tags: tags
  }
}

module acr 'modules/acr.bicep' = {
  name: 'deploy-acr'
  params: {
    name: '${projectName}acr${environment}'
    location: location
    environment: environment
    tags: tags
  }
}

module cosmosDb 'modules/cosmosdb.bicep' = {
  name: 'deploy-cosmosdb'
  params: {
    name: '${projectName}-cosmos-${environment}'
    location: location
    environment: environment
    tags: tags
    keyVaultName: keyVault.outputs.keyVaultName
    serverless: environment == 'dev'
  }
}

module redis 'modules/redis.bicep' = {
  name: 'deploy-redis'
  params: {
    name: '${projectName}-redis-${environment}'
    location: location
    environment: environment
    tags: tags
    keyVaultName: keyVault.outputs.keyVaultName
    skuName: environment == 'dev' ? 'Standard' : 'Standard'
    skuCapacity: environment == 'dev' ? 1 : 2
  }
}

module aks 'modules/aks.bicep' = {
  name: 'deploy-aks'
  params: {
    name: '${projectName}-aks-${environment}'
    location: location
    environment: environment
    tags: tags
    acrId: acr.outputs.acrId
    nodeCount: environment == 'dev' ? 2 : 3
  }
}

@description('Name of the deployed Key Vault.')
output keyVaultName string = keyVault.outputs.keyVaultName

@description('Login server of the deployed ACR.')
output acrLoginServer string = acr.outputs.acrLoginServer

@description('Document endpoint of the deployed Cosmos DB account.')
output cosmosDbEndpoint string = cosmosDb.outputs.cosmosDbEndpoint

@description('Name of the deployed AKS cluster.')
output aksClusterName string = aks.outputs.aksClusterName
