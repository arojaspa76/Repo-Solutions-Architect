# Project:     GenAIDemo
# Component:   Orchestrator
# Description: Routes user messages to domain sub-agents and streams responses via SSE
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel
from semantic_kernel import Kernel

from src.agents.base import AgentResponse
from src.agents.registry import AgentRegistry
from src.core.router import classify_intent

if TYPE_CHECKING:
    from apps.api.src.schemas import User
    from src.core.context_manager import ConversationContext

logger = structlog.get_logger(__name__)


class SSEChunk(BaseModel):
    """A single Server-Sent Event emitted while streaming an agent response."""

    type: str
    data: dict


class GenAIDemoOrchestrator:
    """Classifies intent and dispatches to the appropriate domain sub-agent(s)."""

    def __init__(self, orchestrator_kernel: Kernel, registry: AgentRegistry, agent_kernels: dict[str, Kernel]) -> None:
        self.orchestrator_kernel = orchestrator_kernel
        self.registry = registry
        self.agents = {
            domain: registry.create_agent(domain, agent_kernels[domain])
            for domain in registry.list_enabled()
        }

    async def process(self, message: str, context: "ConversationContext", user: "User") -> AgentResponse:
        """Classify intent, dispatch to one or more domain agents, and return the combined response."""
        decision = await classify_intent(self.orchestrator_kernel, message, context.summary)

        if decision.requires_multi_agent:
            domains = [decision.target_agent, *decision.additional_agents]
            domains = [d for d in dict.fromkeys(domains) if d in self.agents]
            responses = [await self.agents[d].invoke(message, context) for d in domains]
            return AgentResponse(
                domain="MULTI",
                content="\n\n".join(f"[{r.domain}] {r.content}" for r in responses),
                sources=[s for r in responses for s in r.sources],
                token_usage={"agents": [r.domain for r in responses]},
            )

        agent = self.agents.get(decision.target_agent, self.agents["GENERAL"])
        return await agent.invoke(message, context)

    async def process_stream(
        self, message: str, context: "ConversationContext", user: "User"
    ) -> AsyncIterator[SSEChunk]:
        """Stream the orchestrated response as SSEChunk events.

        Catches all exceptions from Semantic Kernel / Azure OpenAI so a downstream
        failure never leaks internal details to the client and always closes the
        stream cleanly with an error event.
        """
        try:
            decision = await classify_intent(self.orchestrator_kernel, message, context.summary)
            target = decision.target_agent if decision.target_agent in self.agents else "GENERAL"
            yield SSEChunk(type="agent", data={"domain": target})

            agent = self.agents[target]
            response = await agent.invoke(message, context)

            for token in response.content.split(" "):
                yield SSEChunk(type="delta", data={"text": f"{token} "})

            yield SSEChunk(type="sources", data={"sources": response.sources})
            yield SSEChunk(type="done", data={})
        except Exception as exc:  # noqa: BLE001 — must never leak SK/Azure internals to the client
            logger.error("orchestrator_stream_failed", error=str(exc))
            yield SSEChunk(type="error", data={"message": "An error occurred. Please try again."})
