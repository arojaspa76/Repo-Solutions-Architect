# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for src/core/context_manager.py ConversationContext
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.context_manager import ConversationContext


def _make_context(summarizer_kernel=None) -> ConversationContext:
    cosmos = MagicMock()
    cosmos.append_message = AsyncMock()
    cosmos.get_conversation = AsyncMock()
    return ConversationContext(
        conversation_id="conv-1",
        user_id="user-1",
        cosmos_repo=cosmos,
        summarizer_kernel=summarizer_kernel,
    )


def test_get_windowed_messages_respects_token_limit() -> None:
    """Only the newest messages that fit the token budget should be returned."""
    context = _make_context()
    context.messages = [{"role": "user", "content": "word " * 2000} for _ in range(5)]
    windowed = context.get_windowed_messages(max_tokens=500)
    assert len(windowed) < len(context.messages)


def test_summary_injected_as_system_message() -> None:
    """When a summary exists, it must be prepended as a system message."""
    context = _make_context()
    context.summary = "Previous discussion about crude oil grades."
    context.messages = [{"role": "user", "content": "hi"}]
    windowed = context.get_windowed_messages()
    assert windowed[0]["role"] == "system"
    assert windowed[0]["content"] == context.summary


def test_total_tokens_counting() -> None:
    """_total_tokens should sum token counts across all in-memory messages."""
    context = _make_context()
    context.messages = [{"role": "user", "content": "hello world"}]
    single = context._count_tokens("hello world")
    assert context._total_tokens() == single


@pytest.mark.asyncio
async def test_add_message_triggers_summarization_at_threshold() -> None:
    """Crossing SUMMARY_THRESHOLD tokens must trigger _summarize_older_messages."""
    summarizer_service = MagicMock()
    summarizer_service.get_chat_message_content = AsyncMock(return_value="resumen breve")
    summarizer_kernel = MagicMock()
    summarizer_kernel.get_service.return_value = summarizer_service

    context = _make_context(summarizer_kernel=summarizer_kernel)
    context.SUMMARY_THRESHOLD = 5
    context.messages = [{"role": "user", "content": "word " * 10}]

    await context.add_message("user", "another message")

    summarizer_service.get_chat_message_content.assert_awaited_once()
    assert context.summary == "resumen breve"
