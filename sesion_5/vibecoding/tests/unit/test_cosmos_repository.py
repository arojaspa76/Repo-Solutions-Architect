# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for src/services/cosmos.py CosmosRepository
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from src.services.cosmos import CosmosRepository


def _make_repo() -> CosmosRepository:
    with patch("src.services.cosmos.CosmosClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.from_connection_string.return_value = mock_client
        repo = CosmosRepository("fake-connection-string")
    repo.container = MagicMock()
    return repo


@pytest.mark.asyncio
async def test_get_conversation_returns_none_when_not_found() -> None:
    """get_conversation should swallow CosmosResourceNotFoundError and return None."""
    repo = _make_repo()
    repo.container.read_item = AsyncMock(side_effect=CosmosResourceNotFoundError())
    result = await repo.get_conversation("conv-1", "user-1")
    assert result is None


@pytest.mark.asyncio
async def test_get_conversation_returns_item() -> None:
    """get_conversation should return the document when found."""
    repo = _make_repo()
    repo.container.read_item = AsyncMock(return_value={"id": "conv-1"})
    result = await repo.get_conversation("conv-1", "user-1")
    assert result == {"id": "conv-1"}


@pytest.mark.asyncio
async def test_upsert_conversation() -> None:
    """upsert_conversation should delegate to container.upsert_item."""
    repo = _make_repo()
    repo.container.upsert_item = AsyncMock(return_value={"id": "conv-1"})
    result = await repo.upsert_conversation({"id": "conv-1"})
    assert result == {"id": "conv-1"}


@pytest.mark.asyncio
async def test_append_message_raises_when_conversation_missing() -> None:
    """append_message should raise if the target conversation does not exist."""
    repo = _make_repo()
    repo.container.read_item = AsyncMock(side_effect=CosmosResourceNotFoundError())
    with pytest.raises(CosmosResourceNotFoundError):
        await repo.append_message("missing", "user-1", {"content": "hi"})


@pytest.mark.asyncio
async def test_delete_conversation() -> None:
    """delete_conversation should delegate to container.delete_item."""
    repo = _make_repo()
    repo.container.delete_item = AsyncMock()
    await repo.delete_conversation("conv-1", "user-1")
    repo.container.delete_item.assert_awaited_once_with(item="conv-1", partition_key="user-1")
