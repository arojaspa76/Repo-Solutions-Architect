# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for src/core/router.py intent classification
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.router import classify_intent


def _kernel_returning(payload: dict) -> MagicMock:
    """Build a fake Kernel whose 'orchestrator' service returns the given JSON payload."""
    service = MagicMock()
    service.get_chat_message_content = AsyncMock(return_value=json.dumps(payload))
    kernel = MagicMock()
    kernel.get_service.return_value = service
    return kernel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "domain", ["REFINACION", "COMBUSTIBLES", "CRUDOS", "GAS", "LICUADOS", "GENERAL"]
)
async def test_route_to_domain(domain: str) -> None:
    """The classifier should return the domain declared by the LLM when confidence is high."""
    kernel = _kernel_returning(
        {"target_agent": domain, "confidence": 0.9, "reasoning": "test", "requires_multi_agent": False}
    )
    decision = await classify_intent(kernel, "some message")
    assert decision.target_agent == domain


@pytest.mark.asyncio
async def test_low_confidence_fallback() -> None:
    """Low-confidence classifications must fall back to GENERAL."""
    kernel = _kernel_returning(
        {"target_agent": "REFINACION", "confidence": 0.3, "reasoning": "unsure"}
    )
    decision = await classify_intent(kernel, "ambiguous message")
    assert decision.target_agent == "GENERAL"


@pytest.mark.asyncio
async def test_multi_agent_routing() -> None:
    """requires_multi_agent should be preserved and additional_agents propagated."""
    kernel = _kernel_returning(
        {
            "target_agent": "GAS",
            "confidence": 0.8,
            "requires_multi_agent": True,
            "additional_agents": ["LICUADOS"],
        }
    )
    decision = await classify_intent(kernel, "cross-domain question")
    assert decision.requires_multi_agent is True
    assert decision.additional_agents == ["LICUADOS"]


@pytest.mark.asyncio
async def test_unparseable_response_falls_back_to_general() -> None:
    """A non-JSON LLM response must not raise — it should fall back to GENERAL."""
    service = MagicMock()
    service.get_chat_message_content = AsyncMock(return_value="not json")
    kernel = MagicMock()
    kernel.get_service.return_value = service

    decision = await classify_intent(kernel, "message")
    assert decision.target_agent == "GENERAL"
    assert decision.confidence == 0.0
