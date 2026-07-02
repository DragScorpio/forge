"""Provider-agnostic LLM interface for the agent.

Rule (initiative-wide): never import a vendor SDK outside its adapter. Choose the backend with
``FORGE_LLM_PROVIDER`` ("anthropic" | "openai"); the default ``auto`` picks whichever key is present. A
schema-carrying call returns a dict conforming to the schema, so the agent stays vendor-neutral. Responses
are cached on disk so re-runs are cheap and reproducible.

There is no offline branch here on purpose: the deterministic path is the :class:`~forge.agent.core.
OfflineAgent`, which replays a committed fixture patch rather than pretending to be a model. This module
is only the real-provider transport.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Protocol

DEFAULT_CACHE_DIR = "data/.llm_cache"
_TOOL_NAME = "emit_patch"


class LLMClient(Protocol):
    """The only model contract the agent depends on."""

    def complete(
        self, messages: list[dict[str, str]], schema: dict[str, Any] | None = None
    ) -> dict[str, Any] | str: ...


# --------------------------------------------------------------------------- response cache


def _cache_key(provider: str, model: str, messages: list[dict], schema: dict | None) -> str:
    """Hash the whole request into one stable filename, so identical calls reuse the cached answer."""
    blob = json.dumps(
        {"provider": provider, "model": model, "messages": messages, "schema": schema},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cached(
    cache_dir: str | None,
    provider: str,
    model: str,
    messages: list[dict],
    schema: dict | None,
    call: Callable[[], dict | str],
) -> dict | str:
    """Return a cached response if present, else call the model and cache the result."""
    if not cache_dir:
        return call()
    key = _cache_key(provider, model, messages, schema)
    path = Path(cache_dir) / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    result = call()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"response": result}, indent=2), encoding="utf-8")
    return result


def _split_system(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """Anthropic takes ``system`` as a top-level argument, not a message role."""
    system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    rest = [m for m in messages if m.get("role") != "system"]
    return system, rest


# --------------------------------------------------------------------------- adapters


class AnthropicAdapter:
    """Structured output via a forced tool call whose ``input_schema`` is our JSON schema."""

    def __init__(self, model: str = "claude-sonnet-4-6", cache_dir: str | None = DEFAULT_CACHE_DIR):
        self.model = model
        self.cache_dir = cache_dir

    def complete(self, messages, schema=None):
        """Send the messages to Anthropic and return the structured patch (or plain text); cached on disk."""

        def call() -> dict | str:
            import anthropic  # imported only inside the adapter

            client = anthropic.Anthropic()
            system, convo = _split_system(messages)
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 4096,
                "system": system or anthropic.NOT_GIVEN,
                "messages": convo,
            }
            if schema is not None:
                kwargs["tools"] = [
                    {
                        "name": _TOOL_NAME,
                        "description": "Emit the plan and unified-diff patch.",
                        "input_schema": schema,
                    }
                ]
                kwargs["tool_choice"] = {"type": "tool", "name": _TOOL_NAME}
            resp = client.messages.create(**kwargs)
            if schema is not None:
                for block in resp.content:
                    if block.type == "tool_use" and block.name == _TOOL_NAME:
                        return dict(block.input)
                raise RuntimeError("Anthropic response contained no tool_use block")
            return "".join(b.text for b in resp.content if b.type == "text").strip()

        return _cached(self.cache_dir, "anthropic", self.model, messages, schema, call)


class OpenAIAdapter:
    """Structured output via the ``json_schema`` response format."""

    def __init__(self, model: str = "gpt-4o", cache_dir: str | None = DEFAULT_CACHE_DIR):
        self.model = model
        self.cache_dir = cache_dir

    def complete(self, messages, schema=None):
        """Send the messages to OpenAI and return the structured patch (or plain text); cached on disk."""

        def call() -> dict | str:
            import openai  # imported only inside the adapter

            client = openai.OpenAI()
            kwargs: dict[str, Any] = {"model": self.model, "messages": messages}
            if schema is not None:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "patch_proposal", "schema": schema},
                }
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            return json.loads(content) if schema is not None else content.strip()

        return _cached(self.cache_dir, "openai", self.model, messages, schema, call)
