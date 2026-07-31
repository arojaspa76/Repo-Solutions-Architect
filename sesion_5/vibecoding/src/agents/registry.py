# Project:     GenAIDemo
# Component:   Agent registry
# Description: Loads domain configurations from YAML and maps domain names to agent classes
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from dataclasses import dataclass
from pathlib import Path

import yaml
from semantic_kernel import Kernel

from src.agents.agente_combustibles import AgenteCombustibles
from src.agents.agente_crudos import AgenteCrudos
from src.agents.agente_gas import AgenteGas
from src.agents.agente_general import AgenteGeneral
from src.agents.agente_licuados import AgenteLicuados
from src.agents.agente_refinacion import AgenteRefinacion
from src.agents.base import BaseGenAIDemoAgent

_AGENT_CLASSES: dict[str, type[BaseGenAIDemoAgent]] = {
    "GENERAL": AgenteGeneral,
    "REFINACION": AgenteRefinacion,
    "COMBUSTIBLES": AgenteCombustibles,
    "CRUDOS": AgenteCrudos,
    "GAS": AgenteGas,
    "LICUADOS": AgenteLicuados,
}


@dataclass
class DomainConfig:
    """Configuration for a single domain sub-agent, loaded from configs/prompts/agents/*.yaml."""

    name: str
    display_name: str
    description: str
    model: str
    tools: list[str]
    enabled: bool
    max_tokens: int


class AgentRegistry:
    """Loads domain configurations at startup and instantiates domain agents on demand."""

    def __init__(self, config_path: str = "configs/prompts/agents/") -> None:
        self.domains: dict[str, DomainConfig] = {}
        self._load_domains(config_path)

    def _load_domains(self, path: str) -> None:
        for yaml_file in sorted(Path(path).glob("*.yaml")):
            with yaml_file.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            config = DomainConfig(
                name=data["name"],
                display_name=data["display_name"],
                description=data["description"],
                model=data["model"],
                tools=data.get("tools", []),
                enabled=data.get("enabled", True),
                max_tokens=data.get("max_tokens", 4096),
            )
            self.domains[config.name] = config

    def get_domain(self, name: str) -> DomainConfig | None:
        """Return the DomainConfig for a domain name, or None if not registered."""
        return self.domains.get(name)

    def list_enabled(self) -> list[str]:
        """Return the names of all enabled domains."""
        return [name for name, config in self.domains.items() if config.enabled]

    def register_domain(self, config: DomainConfig) -> None:
        """Register a new domain at runtime without restart."""
        self.domains[config.name] = config

    def create_agent(self, domain: str, kernel: Kernel) -> BaseGenAIDemoAgent:
        """Instantiate the agent class for a domain."""
        agent_cls = _AGENT_CLASSES[domain]
        return agent_cls(kernel)
