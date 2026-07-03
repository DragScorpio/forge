"""The agent core: propose a patch for a grounded task.

:class:`LLMAgent` asks a real provider for a ``{plan, patch}`` object. :class:`OfflineAgent` replays the
committed gold patch — a fixture-replay test double that lets the harness run without a key. Both return a
:class:`Proposal`, so the solve loop does not care which one it is holding.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from ..tasks import Task
from . import prompt
from .llm import AnthropicAdapter, LLMClient, OpenAIAdapter
from .schemas import PATCH_PROPOSAL_SCHEMA


@dataclass(frozen=True)
class Proposal:
    """What an agent hands back: an ordered plan, a unified-diff patch, and which agent produced it."""

    plan: list[str]
    patch: str
    source: str


class Agent(Protocol):
    """The contract the solve loop depends on."""

    name: str

    def propose(self, task: Task, test_source: str, file_contents: dict[str, str]) -> Proposal: ...


class LLMAgent:
    """Real-provider agent: prompt a model for a plan + unified-diff patch."""

    def __init__(self, client: LLMClient, name: str):
        self.client = client
        self.name = name

    def propose(self, task: Task, test_source: str, file_contents: dict[str, str]) -> Proposal:
        """Ask the model for a structured patch proposal over the localized source."""
        messages = prompt.build_messages(task, test_source, file_contents)
        result = self.client.complete(messages, PATCH_PROPOSAL_SCHEMA)
        if not isinstance(result, dict):
            raise RuntimeError("LLM did not return a structured patch proposal")
        # Be defensive: default the fields rather than crash if a provider omits one.
        return Proposal(
            plan=list(result.get("plan", [])),
            patch=str(result.get("patch", "")),
            source=self.name,
        )


class OfflineAgent:
    """Deterministic fixture-replay double: return the task's committed gold patch (no model, no key).

    This exercises the whole harness reproducibly. It is honest about what it is — it does not measure a
    model's ability to *find* a fix; it replays a known-correct one so localization, patch application,
    the sandbox gate, and the eval can all be tested with no provider.
    """

    name = "offline"

    def propose(self, task: Task, test_source: str, file_contents: dict[str, str]) -> Proposal:
        """Replay the committed gold patch for this task."""
        return Proposal(
            plan=["replay the committed gold patch (offline fixture)"],
            patch=task.gold_patch(),
            source=self.name,
        )


def get_agent() -> Agent:
    """Factory selected by FORGE_LLM_PROVIDER (default: auto-detect from available keys)."""
    provider = os.environ.get("FORGE_LLM_PROVIDER", "auto").lower()
    if provider == "auto":
        # Prefer a real provider when its key is set, else the deterministic offline double.
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            provider = "offline"
    if provider == "offline":
        return OfflineAgent()
    if provider == "anthropic":
        return LLMAgent(AnthropicAdapter(), name="anthropic")
    if provider == "openai":
        return LLMAgent(OpenAIAdapter(), name="openai")
    raise ValueError(
        f"Unknown FORGE_LLM_PROVIDER: {provider!r} (expected 'anthropic', 'openai', or 'offline')"
    )
