# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for apps/api/src/middleware/auth.py and User model
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

import pytest

from apps.api.src.middleware.auth import get_current_user
from apps.api.src.schemas import User


def test_user_from_token_claims() -> None:
    """User.from_token should map standard Entra ID JWT claims onto the User model."""
    claims = {
        "oid": "user-object-id",
        "tid": "tenant-id",
        "preferred_username": "andres@techcorp.com",
        "name": "Andrés Rojas",
        "roles": ["Chat.ReadWrite"],
    }
    user = User.from_token(claims)
    assert user.oid == "user-object-id"
    assert user.tid == "tenant-id"
    assert user.email == "andres@techcorp.com"
    assert user.display_name == "Andrés Rojas"
    assert user.roles == ["Chat.ReadWrite"]


def test_user_from_token_missing_optional_claims_defaults_empty() -> None:
    """Missing optional claims (name, roles) should default rather than raise."""
    user = User.from_token({"oid": "id", "tid": "tid"})
    assert user.display_name == ""
    assert user.roles == []


@pytest.mark.asyncio
async def test_valid_jwt_returns_user() -> None:
    """get_current_user should build a User from already-validated token claims."""
    claims = {"oid": "abc", "tid": "def", "preferred_username": "u@techcorp.com", "name": "U"}
    user = await get_current_user(claims)
    assert isinstance(user, User)
    assert user.oid == "abc"
