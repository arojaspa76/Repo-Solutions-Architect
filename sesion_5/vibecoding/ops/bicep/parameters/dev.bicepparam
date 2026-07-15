// Project:     GenAIDemo
// Component:   Bicep parameters (dev)
// Description: Parameter values for the dev environment deployment
// Owner:       Andrés Felipe Rojas Parra
// Created:     2026-07

using '../main.bicep'

param projectName = 'genaidemo'
param environment = 'dev'
param location = 'eastus2'
param tags = {
  project: 'GenAIDemo'
  environment: 'dev'
  managedBy: 'Bicep'
  owner: 'andres.rojas@techcorp.com'
}
