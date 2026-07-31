# Project:     GenAIDemo
# Component:   Intent router
# Description: LLM-based intent classifier — decides which domain sub-agent handles a query
# Owner:       Andrés Felipe Rojas Parra
# Created:     2026-07

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory

ROUTER_PROMPT_PATH = Path("configs/prompts/router.yaml")
VALID_DOMAINS = {"REFINACION", "COMBUSTIBLES", "CRUDOS", "GAS", "LICUADOS", "GENERAL"}
CONFIDENCE_FALLBACK_THRESHOLD = 0.5


@dataclass
class RoutingDecision:
    """Result of classifying a user message into a target domain."""

    target_agent: str
    confidence: float
    reasoning: str = ""
    requires_multi_agent: bool = False
    additional_agents: list[str] = field(default_factory=list)


def _load_router_prompt() -> str:
    with ROUTER_PROMPT_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)["system_prompt"]


async def classify_intent(
    kernel: Kernel, message: str, conversation_summary: str = ""
) -> RoutingDecision:
    """Classify a user message into a target domain using the orchestrator's GPT-4o service."""
    system_prompt = _load_router_prompt()
    history = ChatHistory(system_message=system_prompt)
    if conversation_summary:
        history.add_system_message(f"Conversation summary so far: {conversation_summary}")
    history.add_user_message(message)

    service = kernel.get_service("orchestrator")
    response = await service.get_chat_message_content(chat_history=history)

    try:
        payload = json.loads(str(response))
    except (json.JSONDecodeError, TypeError):
        return RoutingDecision(target_agent="GENERAL", confidence=0.0, reasoning="parse_error")

    target_agent = payload.get("target_agent", "GENERAL")
    confidence = float(payload.get("confidence", 0.0))
    if target_agent not in VALID_DOMAINS or confidence < CONFIDENCE_FALLBACK_THRESHOLD:
        target_agent = "GENERAL"

    return RoutingDecision(
        target_agent=target_agent,
        confidence=confidence,
        reasoning=payload.get("reasoning", ""),
        requires_multi_agent=bool(payload.get("requires_multi_agent", False)),
        additional_agents=payload.get("additional_agents", []),
    )
