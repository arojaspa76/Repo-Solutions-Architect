# Project:     GenAIDemo
# Component:   Tests
# Description: Integration tests for the conversations API using httpx.AsyncClient
#              against the ASGI app directly (no real Azure calls, lifespan disabled)
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from apps.api.src.dependencies import get_cosmos, get_orchestrator
from apps.api.src.main import app
from apps.api.src.middleware.auth import get_current_user
from apps.api.src.schemas import User
from src.core.orchestrator import SSEChunk


@pytest.fixture
def fake_user() -> User:
    return User(oid="user-1", tid="tenant-1", email="u@techcorp.com", display_name="U")


@pytest.fixture
def fake_cosmos() -> MagicMock:
    cosmos = MagicMock()
    cosmos.list_conversations = AsyncMock(return_value=[])
    cosmos.upsert_conversation = AsyncMock(side_effect=lambda c: c)
    cosmos.get_conversation = AsyncMock(return_value=None)
    cosmos.append_message = AsyncMock()
    cosmos.delete_conversation = AsyncMock()
    return cosmos


@pytest.fixture
def fake_orchestrator() -> MagicMock:
    orchestrator = MagicMock()

    async def _stream(*args, **kwargs):
        yield SSEChunk(type="agent", data={"domain": "GENERAL"})
        yield SSEChunk(type="delta", data={"text": "hola "})
        yield SSEChunk(type="sources", data={"sources": []})
        yield SSEChunk(type="done", data={})

    orchestrator.process_stream = _stream
    return orchestrator


@pytest.fixture
async def client(fake_user, fake_cosmos, fake_orchestrator):
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_cosmos] = lambda: fake_cosmos
    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations_requires_auth() -> None:
    """Without an auth override, the endpoint must reject the request (no 200)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/conversations/")
    assert response.status_code != 200


@pytest.mark.asyncio
async def test_create_conversation_returns_201(client: httpx.AsyncClient) -> None:
    """Creating a conversation returns 201 with a fresh conversation document."""
    response = await client.post("/api/v1/conversations/")
    assert response.status_code == 201
    assert response.json()["title"] == "New conversation"


@pytest.mark.asyncio
async def test_send_message_streams_sse(client: httpx.AsyncClient) -> None:
    """Sending a message must stream SSE events terminated by [DONE]."""
    async with client.stream(
        "POST", "/api/v1/conversations/conv-1/messages", json={"content": "hola"}
    ) as response:
        body = ""
        async for chunk in response.aiter_text():
            body += chunk
    assert "data: " in body
    assert body.strip().endswith("data: [DONE]")


@pytest.mark.asyncio
async def test_delete_conversation_returns_204(client: httpx.AsyncClient) -> None:
    """Deleting a conversation returns 204 No Content."""
    response = await client.delete("/api/v1/conversations/conv-1")
    assert response.status_code == 204
