// Project:     GenAIDemo
// Component:   Redis module
// Description: Azure Cache for Redis for session state and semantic cache
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

@description('Name of the Azure Cache for Redis instance.')
@minLength(1)
@maxLength(63)
param name string

@description('Azure region for the Redis cache.')
param location string

@description('Deployment environment (dev, staging, production).')
@allowed([
  'dev'
  'staging'
  'production'
])
param environment string

@description('Resource tags applied to the Redis cache.')
param tags object

@description('Name of the Key Vault where Redis secrets are stored.')
param keyVaultName string

@description('Redis SKU family (C = Basic/Standard).')
param skuFamily string = 'C'

@description('Redis SKU name.')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param skuName string = 'Standard'

@description('Redis SKU capacity (0-6 for C family).')
param skuCapacity int = 1

resource redisCache 'Microsoft.Cache/redis@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: skuName
      family: skuFamily
      capacity: skuCapacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisVersion: '6'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource redisAccessKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'REDIS-ACCESS-KEY'
  properties: {
    value: redisCache.listKeys().primaryKey
  }
}

resource redisHostSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'REDIS-HOST'
  properties: {
    value: '${redisCache.properties.hostName}:${redisCache.properties.sslPort}'
  }
}

@description('Host name of the deployed Redis cache.')
output redisHostName string = redisCache.properties.hostName

@description('SSL port of the deployed Redis cache.')
output redisSslPort int = redisCache.properties.sslPort
