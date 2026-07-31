# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for src/core/orchestrator.py GenAIDemoOrchestrator
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentResponse
from src.core.orchestrator import GenAIDemoOrchestrator
from src.core.router import RoutingDecision


def _make_orchestrator() -> GenAIDemoOrchestrator:
    registry = MagicMock()
    registry.list_enabled.return_value = ["GENERAL", "GAS", "LICUADOS"]

    fake_agents = {}
    for domain in ["GENERAL", "GAS", "LICUADOS"]:
        agent = MagicMock()
        agent.invoke = AsyncMock(
            return_value=AgentResponse(domain=domain, content=f"response from {domain}")
        )
        fake_agents[domain] = agent
    registry.create_agent.side_effect = lambda domain, kernel: fake_agents[domain]

    return GenAIDemoOrchestrator(
        orchestrator_kernel=MagicMock(),
        registry=registry,
        agent_kernels={"GENERAL": MagicMock(), "GAS": MagicMock(), "LICUADOS": MagicMock()},
    )


@pytest.mark.asyncio
async def test_process_dispatches_to_single_agent() -> None:
    """process() should invoke only the classified target agent."""
    orchestrator = _make_orchestrator()
    context = MagicMock(summary="")
    with patch(
        "src.core.orchestrator.classify_intent",
        AsyncMock(return_value=RoutingDecision(target_agent="GAS", confidence=0.9)),
    ):
        response = await orchestrator.process("some gas question", context, MagicMock())
    assert response.domain == "GAS"


@pytest.mark.asyncio
async def test_process_multi_agent_combines_responses() -> None:
    """process() should combine responses when requires_multi_agent is True."""
    orchestrator = _make_orchestrator()
    context = MagicMock(summary="")
    decision = RoutingDecision(
        target_agent="GAS", confidence=0.9, requires_multi_agent=True, additional_agents=["LICUADOS"]
    )
    with patch("src.core.orchestrator.classify_intent", AsyncMock(return_value=decision)):
        response = await orchestrator.process("cross domain", context, MagicMock())
    assert response.domain == "MULTI"
    assert "response from GAS" in response.content
    assert "response from LICUADOS" in response.content


@pytest.mark.asyncio
async def test_process_stream_yields_error_event_on_failure() -> None:
    """process_stream() must never raise — a downstream failure yields an error SSE event."""
    orchestrator = _make_orchestrator()
    context = MagicMock(summary="")
    with patch(
        "src.core.orchestrator.classify_intent", AsyncMock(side_effect=RuntimeError("boom"))
    ):
        chunks = [chunk async for chunk in orchestrator.process_stream("msg", context, MagicMock())]
    assert chunks[-1].type == "error"
    assert "internal" not in chunks[-1].data["message"].lower()
    assert "boom" not in chunks[-1].data["message"]


@pytest.mark.asyncio
async def test_process_stream_happy_path_emits_agent_delta_sources_done() -> None:
    """process_stream() should emit agent -> delta(s) -> sources -> done in order."""
    orchestrator = _make_orchestrator()
    context = MagicMock(summary="")
    decision = RoutingDecision(target_agent="GENERAL", confidence=0.9)
    with patch("src.core.orchestrator.classify_intent", AsyncMock(return_value=decision)):
        chunks = [chunk async for chunk in orchestrator.process_stream("hola", context, MagicMock())]
    types = [c.type for c in chunks]
    assert types[0] == "agent"
    assert types[-2] == "sources"
    assert types[-1] == "done"
