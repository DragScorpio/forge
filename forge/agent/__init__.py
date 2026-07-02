"""The agent: turn a grounded task into a proposed patch, behind a provider-agnostic interface.

Two agent kinds share one :class:`Agent` shape:

* :class:`LLMAgent` wraps a provider-agnostic :class:`LLMClient` (Anthropic / OpenAI). It reads the task,
  the failing test, and the localized source, and asks the model for a plan plus a unified diff.
* :class:`OfflineAgent` is an honest **fixture-replay** test double: it replays the committed gold patch
  for a known mini-bench task. It exists so the whole harness — localization, patch application, sandbox
  verification, and the eval — runs and is tested with no API key. It does not measure a model's real
  solving ability; a genuine solve-rate needs a real provider behind :class:`LLMClient`.
"""

from .core import Agent, OfflineAgent, LLMAgent, Proposal, get_agent
from .llm import LLMClient

__all__ = ["Agent", "OfflineAgent", "LLMAgent", "Proposal", "get_agent", "LLMClient"]
