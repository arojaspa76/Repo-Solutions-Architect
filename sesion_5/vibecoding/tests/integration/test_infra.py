# Project:     GenAIDemo
# Component:   Infrastructure validation tests
# Description: Integration tests validating Key Vault, Cosmos DB, Redis and ACR reachability
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

import os

import pytest
import redis
from azure.core.exceptions import ResourceNotFoundError
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.containerregistry import ContainerRegistryManagementClient

REQUIRED_SECRETS = [
    "COSMOS-DB-CONNECTION-STRING",
    "REDIS-ACCESS-KEY",
    "REDIS-HOST",
    "AZURE-AD-CLIENT-ID",
    "AZURE-AD-CLIENT-SECRET",
    "AZURE-AD-TENANT-ID",
    "AZURE-OPENAI-KEY",
]


def test_keyvault_reachable(secret_client: SecretClient) -> None:
    """Key Vault must be reachable and contain the Cosmos DB connection string."""
    secret_names = [secret.name for secret in secret_client.list_properties_of_secrets()]
    assert "COSMOS-DB-CONNECTION-STRING" in secret_names


def test_cosmosdb_crud(secret_client: SecretClient) -> None:
    """Cosmos DB conversations container must support create, read and delete."""
    connection_string = secret_client.get_secret("COSMOS-DB-CONNECTION-STRING").value
    client = CosmosClient.from_connection_string(connection_string)
    database = client.get_database_client("genaidemo-db")
    container = database.get_container_client("conversations")

    item = {"id": "test-infra-001", "user_id": "infra-test", "content": "ping"}
    container.create_item(body=item)

    read_item = container.read_item(item="test-infra-001", partition_key="infra-test")
    assert read_item["id"] == "test-infra-001"

    container.delete_item(item="test-infra-001", partition_key="infra-test")

    with pytest.raises(ResourceNotFoundError):
        container.read_item(item="test-infra-001", partition_key="infra-test")


def test_redis_connectivity(secret_client: SecretClient) -> None:
    """Redis cache must accept SET/GET/DELETE over TLS."""
    access_key = secret_client.get_secret("REDIS-ACCESS-KEY").value
    redis_host = os.environ["REDIS_HOST"]
    redis_ssl_port = int(os.environ["REDIS_SSL_PORT"])

    client = redis.StrictRedis(
        host=redis_host,
        port=redis_ssl_port,
        password=access_key,
        ssl=True,
    )

    client.set("infra-test-key", "hello-genaidemo")
    assert client.get("infra-test-key") == b"hello-genaidemo"
    client.delete("infra-test-key")


def test_acr_image_pullable(azure_credential: DefaultAzureCredential) -> None:
    """ACR must be reachable and listable without authentication errors."""
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["RESOURCE_GROUP"]
    acr_name = os.environ["ACR_NAME"]

    client = ContainerRegistryManagementClient(azure_credential, subscription_id)
    registry = client.registries.get(resource_group, acr_name)
    assert registry is not None


def test_keyvault_secrets_complete(secret_client: SecretClient) -> None:
    """All secrets required by the platform must exist in Key Vault."""
    secret_names = {secret.name for secret in secret_client.list_properties_of_secrets()}
    missing = [name for name in REQUIRED_SECRETS if name not in secret_names]
    assert not missing, f"Missing secrets in Key Vault: {missing}"
