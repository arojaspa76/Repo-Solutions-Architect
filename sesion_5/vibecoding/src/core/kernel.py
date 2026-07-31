# Project:     GenAIDemo
# Component:   Semantic Kernel factory
# Description: Builds Kernel instances for the orchestrator (gpt-4o) and domain sub-agents (gpt-4o-mini)
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from src.config.settings import Settings

ORCHESTRATOR_DEPLOYMENT = "gpt-4o"
AGENT_DEPLOYMENT = "gpt-4o-mini"


def create_orchestrator_kernel(settings: Settings) -> Kernel:
    """Create a Kernel backed by GPT-4o for the orchestrator's intent classification."""
    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            service_id="orchestrator",
            deployment_name=ORCHESTRATOR_DEPLOYMENT,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
        )
    )
    return kernel


def create_agent_kernel(settings: Settings, domain: str) -> Kernel:
    """Create a Kernel backed by GPT-4o-mini for a domain sub-agent."""
    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            service_id=f"agent-{domain.lower()}",
            deployment_name=AGENT_DEPLOYMENT,
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
        )
    )
    return kernel
