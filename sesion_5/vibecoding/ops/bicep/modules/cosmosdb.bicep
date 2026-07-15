// Project:     GenAIDemo
// Component:   Cosmos DB module
// Description: Serverless Cosmos DB (NoSQL API) for conversation history storage
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

@description('Name of the Cosmos DB account.')
@minLength(3)
@maxLength(44)
param name string

@description('Azure region for the Cosmos DB account.')
param location string

@description('Deployment environment (dev, staging, production).')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string

@description('Resource tags applied to the Cosmos DB account.')
param tags object

@description('Name of the Key Vault where the connection string secret is stored.')
param keyVaultName string

@description('Use serverless capacity mode. Set to false for staging/production provisioned throughput.')
param serverless bool = true

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: serverless ? [
      {
        name: 'EnableServerless'
      }
    ] : []
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: 'genaidemo-db'
  properties: {
    resource: {
      id: 'genaidemo-db'
    }
  }
}

resource conversationsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'conversations'
  properties: {
    resource: {
      id: 'conversations'
      partitionKey: {
        paths: [
          '/user_id'
        ]
        kind: 'Hash'
      }
      defaultTtl: -1
      indexingPolicy: {
        automatic: true
        indexingMode: 'consistent'
      }
    }
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource cosmosConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'COSMOS-DB-CONNECTION-STRING'
  properties: {
    value: cosmosAccount.listConnectionStrings().connectionStrings[0].connectionString
  }
}

@description('Document endpoint of the deployed Cosmos DB account.')
output cosmosDbEndpoint string = cosmosAccount.properties.documentEndpoint

@description('Name of the deployed Cosmos DB account.')
output cosmosDbAccountName string = cosmosAccount.name
