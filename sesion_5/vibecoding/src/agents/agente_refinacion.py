# Project:     GenAIDemo
# Component:   Domain agent
# Description: REFINACION domain sub-agent — refinery operations, yields, margins
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

from pathlib import Path

import yaml
from semantic_kernel import Kernel

from src.agents.base import BaseGenAIDemoAgent

PROMPT_PATH = Path("configs/prompts/agents/refinacion.yaml")


class AgenteRefinacion(BaseGenAIDemoAgent):
    """REFINACION domain sub-agent."""

    def __init__(self, kernel: Kernel, tools: list | None = None) -> None:
        with PROMPT_PATH.open(encoding="utf-8") as f:
            config = yaml.safe_load(f)
        super().__init__(kernel, domain=config["name"], system_prompt=config["system_prompt"], tools=tools)
