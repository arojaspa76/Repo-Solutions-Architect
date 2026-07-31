# Project:     GenAIDemo
# Component:   Conversation context manager
# Description: Token-windowed conversation context with Cosmos persistence and
#              summarization of older turns once the token budget is exceeded
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import tiktoken
from semantic_kernel import Kernel

if TYPE_CHECKING:
    from src.services.cosmos import CosmosRepository

SUMMARIZE_PROMPT = "Summarize this conversation in 3 sentences in Spanish:\n\n{transcript}"


class ConversationContext:
    """Holds the in-memory message window for a single conversation, backed by Cosmos DB."""

    MAX_CONTEXT_TOKENS: int = 16_000
    SUMMARY_THRESHOLD: int = 12_000
    ENCODING: str = "cl100k_base"

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        cosmos_repo: "CosmosRepository",
        summary: str = "",
        summarizer_kernel: Kernel | None = None,
    ) -> None:
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.cosmos = cosmos_repo
        self.messages: list[dict] = []
        self.summary: str = summary
        self._summarizer_kernel = summarizer_kernel
        self._enc = tiktoken.get_encoding(self.ENCODING)

    def _count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def _total_tokens(self) -> int:
        return sum(self._count_tokens(m["content"]) for m in self.messages)

    def get_windowed_messages(self, max_tokens: int | None = None) -> list[dict]:
        """Return messages fitting within the token budget, oldest-to-newest, prefixed
        by the running summary as a system message when one exists."""
        budget = max_tokens or self.MAX_CONTEXT_TOKENS
        windowed: list[dict] = []
        used = 0
        for message in reversed(self.messages):
            tokens = self._count_tokens(message["content"])
            if used + tokens > budget:
                break
            windowed.append(message)
            used += tokens
        windowed.reverse()
        if self.summary:
            windowed.insert(0, {"role": "system", "content": self.summary})
        return windowed

    async def add_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        """Add a message, persist it to Cosmos DB, and summarize older turns if the
        token budget has been exceeded."""
        message = {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)
        await self.cosmos.append_message(self.conversation_id, self.user_id, message)
        if self._total_tokens() > self.SUMMARY_THRESHOLD:
            await self._summarize_older_messages()

    async def _summarize_older_messages(self) -> None:
        """Summarize the first half of messages using GPT-4o-mini and drop them from
        the in-memory window (they remain persisted in Cosmos DB)."""
        if self._summarizer_kernel is None:
            return
        midpoint = len(self.messages) // 2
        older = self.messages[:midpoint]
        if not older:
            return
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in older)
        service = self._summarizer_kernel.get_service("agent-general")
        response = await service.get_chat_message_content(
            chat_history=SUMMARIZE_PROMPT.format(transcript=transcript)
        )
        self.summary = str(response)
        self.messages = self.messages[midpoint:]

    async def load_from_cosmos(self) -> None:
        """Load conversation history from Cosmos DB into memory (used when this
        context is first created on a fresh server instance)."""
        conversation = await self.cosmos.get_conversation(self.conversation_id, self.user_id)
        if conversation is None:
            return
        self.messages = conversation.get("messages", [])
        self.summary = conversation.get("summary", "")
