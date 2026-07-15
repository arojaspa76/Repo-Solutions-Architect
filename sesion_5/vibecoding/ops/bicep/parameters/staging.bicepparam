// Project:     GenAIDemo
// Component:   Bicep parameters (staging)
// Description: Parameter values for the staging environment deployment
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

using '../main.bicep'

param projectName = 'genaidemo'
param environment = 'staging'
param location = 'eastus2'
param tags = {
  project: 'GenAIDemo'
  environment: 'staging'
  managedBy: 'Bicep'
  owner: 'andres.rojas@techcorp.com'
}
