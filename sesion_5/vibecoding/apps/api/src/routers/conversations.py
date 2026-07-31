# Project:     GenAIDemo
# Component:   Conversations router
# Description: CRUD + SSE messaging endpoints for conversations, all JWT-protected
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.core.context_manager import ConversationContext
from src.services.cosmos import CosmosRepository

from ..dependencies import get_cosmos, get_orchestrator
from ..middleware.auth import get_current_user
from ..schemas import (
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    MessageCreate,
    User,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _with_summary_fields(conversation: dict) -> dict:
    """Derive message_count/last_agent (not persisted) before returning a document."""
    messages = conversation.get("messages", [])
    last_agent = messages[-1]["metadata"].get("agent") if messages else None
    return {**conversation, "message_count": len(messages), "last_agent": last_agent}


@router.get("/", response_model=list[ConversationSummary])
async def list_conversations(
    user: User = Depends(get_current_user),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> list[dict]:
    """List conversations for the authenticated user."""
    conversations = await cosmos.list_conversations(user_id=user.oid, tenant_id=user.tid)
    return [_with_summary_fields(c) for c in conversations]


@router.post("/", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    user: User = Depends(get_current_user),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> dict:
    """Create a new empty conversation."""
    now = datetime.now(UTC).isoformat()
    conversation = {
        "id": str(uuid4()),
        "user_id": user.oid,
        "tenant_id": user.tid,
        "title": "New conversation",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "summary": "",
        "tags": [],
        "is_archived": False,
    }
    return _with_summary_fields(await cosmos.upsert_conversation(conversation))


@router.get("/search", response_model=list[ConversationSummary])
async def search_conversations(
    q: str,
    user: User = Depends(get_current_user),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> list[dict]:
    """Search conversations by title or message content."""
    conversations = await cosmos.search_conversations(user_id=user.oid, query=q)
    return [_with_summary_fields(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> dict:
    """Get a conversation with all messages."""
    conversation = await cosmos.get_conversation(conversation_id, user.oid)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _with_summary_fields(conversation)


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    orchestrator=Depends(get_orchestrator),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> StreamingResponse:
    """Send a message and stream the orchestrated response via SSE."""
    conversation = await cosmos.get_conversation(conversation_id, user.oid)
    if conversation is None:
        now = datetime.now(UTC).isoformat()
        conversation = {
            "id": conversation_id,
            "user_id": user.oid,
            "tenant_id": user.tid,
            "title": body.content[:60],
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "summary": "",
            "tags": [],
            "is_archived": False,
        }
        await cosmos.upsert_conversation(conversation)

    context = ConversationContext(
        conversation_id=conversation_id,
        user_id=user.oid,
        cosmos_repo=cosmos,
        summary=conversation.get("summary", ""),
    )
    context.messages = conversation.get("messages", [])
    await context.add_message("user", body.content)

    async def event_stream():
        async for chunk in orchestrator.process_stream(body.content, context, user):
            yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.put("/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    user: User = Depends(get_current_user),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> dict:
    """Rename or archive a conversation."""
    conversation = await cosmos.get_conversation(conversation_id, user.oid)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if body.title is not None:
        conversation["title"] = body.title
    if body.is_archived is not None:
        conversation["is_archived"] = body.is_archived
    conversation["updated_at"] = datetime.now(UTC).isoformat()
    return _with_summary_fields(await cosmos.upsert_conversation(conversation))


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    cosmos: CosmosRepository = Depends(get_cosmos),
) -> None:
    """Permanently delete a conversation."""
    await cosmos.delete_conversation(conversation_id, user.oid)
