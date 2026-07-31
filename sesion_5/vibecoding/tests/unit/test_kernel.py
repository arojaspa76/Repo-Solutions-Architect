# Project:     GenAIDemo
# Component:   Tests
# Description: Unit tests for src/core/kernel.py Kernel factories
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from src.config.settings import Settings
from src.core.kernel import create_agent_kernel, create_orchestrator_kernel


def _settings() -> Settings:
    return Settings(azure_openai_endpoint="https://example.openai.azure.com/", azure_openai_key="fake-key")


def test_create_orchestrator_kernel_registers_gpt4o_service() -> None:
    """The orchestrator kernel must expose a service registered as 'orchestrator'."""
    kernel = create_orchestrator_kernel(_settings())
    assert kernel.get_service("orchestrator") is not None


def test_create_agent_kernel_registers_domain_service() -> None:
    """A domain kernel must expose a service registered as 'agent-{domain}'."""
    kernel = create_agent_kernel(_settings(), "GAS")
    assert kernel.get_service("agent-gas") is not None
