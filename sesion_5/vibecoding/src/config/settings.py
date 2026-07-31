# Project:     GenAIDemo
# Component:   Configuration
# Description: Pydantic Settings singleton, secrets loaded from Azure Key Vault at startup
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRET_TO_ATTR = {
    "COSMOS-DB-CONNECTION-STRING": "cosmos_connection_string",
    "REDIS-HOST": "redis_host",
    "REDIS-ACCESS-KEY": "redis_access_key",
    "AZURE-AD-CLIENT-ID": "azure_ad_client_id",
    "AZURE-AD-TENANT-ID": "azure_ad_tenant_id",
    "AZURE-OPENAI-ENDPOINT": "azure_openai_endpoint",
    "AZURE-OPENAI-KEY": "azure_openai_key",
}


class Settings(BaseSettings):
    """Application configuration. Non-secret values come from env vars; secrets are
    populated from Azure Key Vault via load_from_key_vault() during app startup."""

    key_vault_uri: str = ""
    environment: str = "dev"
    project_name: str = "genaidemo"
    redis_ssl_port: int = 6380

    cosmos_connection_string: str = ""
    redis_host: str = ""
    redis_access_key: str = ""
    azure_ad_client_id: str = ""
    azure_ad_tenant_id: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def load_from_key_vault(self) -> None:
        """Populate secret-backed attributes from Azure Key Vault using DefaultAzureCredential."""
        if not self.key_vault_uri:
            raise RuntimeError("KEY_VAULT_URI is not set; cannot load secrets from Key Vault.")
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=self.key_vault_uri, credential=credential)
        for secret_name, attr_name in _SECRET_TO_ATTR.items():
            secret = client.get_secret(secret_name)
            setattr(self, attr_name, secret.value)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return Settings()
