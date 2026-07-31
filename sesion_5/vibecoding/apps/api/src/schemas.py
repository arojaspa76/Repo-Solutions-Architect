# Project:     GenAIDemo
# Component:   API schemas
# Description: Pydantic request/response models shared across routers
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    """Authenticated caller, built from validated Entra ID JWT claims."""

    oid: str
    tid: str
    email: str
    display_name: str
    roles: list[str] = Field(default_factory=list)

    @classmethod
    def from_token(cls, token_claims: dict) -> "User":
        """Build a User from validated JWT claims."""
        return cls(
            oid=token_claims["oid"],
            tid=token_claims["tid"],
            email=token_claims.get("preferred_username", token_claims.get("upn", "")),
            display_name=token_claims.get("name", ""),
            roles=token_claims.get("roles", []),
        )


class MessageMetadata(BaseModel):
    agent: str | None = None
    tokens_used: int = 0
    sources: list[str] = Field(default_factory=list)
    latency_ms: int = 0


class Message(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime
    message_count: int
    last_agent: str | None = None


class ConversationDetail(ConversationSummary):
    messages: list[Message] = Field(default_factory=list)
    summary: str = ""


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    domain_override: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_archived: bool | None = None
