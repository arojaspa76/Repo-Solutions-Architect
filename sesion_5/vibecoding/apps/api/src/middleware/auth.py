# Project:     GenAIDemo
# Component:   Auth middleware
# Description: Entra ID JWT validation (fastapi-azure-auth) and current-user dependency
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from fastapi import Depends
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer

from src.config.settings import Settings, get_settings

from ..schemas import User


def build_azure_scheme(settings: Settings) -> SingleTenantAzureAuthorizationCodeBearer:
    """Build the Entra ID bearer-token scheme for the configured single tenant app."""
    return SingleTenantAzureAuthorizationCodeBearer(
        app_client_id=settings.azure_ad_client_id,
        tenant_id=settings.azure_ad_tenant_id,
        scopes={
            f"api://{settings.azure_ad_client_id}/Chat.ReadWrite": "Chat.ReadWrite",
            f"api://{settings.azure_ad_client_id}/History.Read": "History.Read",
        },
    )


azure_scheme = build_azure_scheme(get_settings())


async def get_current_user(token_claims: dict = Depends(azure_scheme)) -> User:
    """Resolve the authenticated User from validated JWT claims."""
    return User.from_token(token_claims)
