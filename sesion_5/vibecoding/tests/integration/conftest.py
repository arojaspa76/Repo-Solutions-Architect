# Project:     GenAIDemo
# Component:   Infrastructure validation tests
# Description: Shared pytest fixtures for Azure infrastructure integration tests
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

import os

import pytest
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@pytest.fixture(scope="session")
def azure_credential() -> DefaultAzureCredential:
    """Provide a DefaultAzureCredential shared across the test session."""
    return DefaultAzureCredential()


@pytest.fixture(scope="session")
def secret_client(azure_credential: DefaultAzureCredential) -> SecretClient:
    """Provide a SecretClient bound to the environment's Key Vault."""
    key_vault_name = os.environ["KEY_VAULT_NAME"]
    vault_url = f"https://{key_vault_name}.vault.azure.net"
    return SecretClient(vault_url=vault_url, credential=azure_credential)
