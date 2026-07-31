# Project:     GenAIDemo
# Component:   Agent base class
# Description: Abstract base for all domain sub-agents; wraps a Semantic Kernel
#              ChatCompletionAgent configured with the domain's system prompt
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent

if TYPE_CHECKING:
    from src.core.context_manager import ConversationContext


@dataclass
class AgentResponse:
    """Result of a domain agent invocation."""

    domain: str
    content: str
    sources: list[str] = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)


class BaseGenAIDemoAgent(ABC):
    """Abstract base class for all domain-specific sub-agents."""

    def __init__(
        self,
        kernel: Kernel,
        domain: str,
        system_prompt: str,
        tools: list | None = None,
    ) -> None:
        self.domain = domain
        self.kernel = kernel
        for tool in tools or []:
            self.kernel.add_plugin(tool, plugin_name=type(tool).__name__)
        self.agent = ChatCompletionAgent(
            kernel=kernel,
            service_id=f"agent-{domain.lower()}",
            name=f"{domain}Agent",
            instructions=system_prompt,
        )

    async def invoke(self, message: str, context: "ConversationContext") -> AgentResponse:
        """Invoke the agent with the user message and windowed conversation context."""
        messages = context.get_windowed_messages(max_tokens=12000)
        messages.append({"role": "user", "content": message})
        response = await self.agent.invoke(messages)
        return AgentResponse(
            domain=self.domain,
            content=response.content,
            sources=[],
            token_usage=(response.metadata or {}).get("usage", {}),
        )
