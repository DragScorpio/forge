"""Agent: the offline fixture-replay double and the provider factory."""

from __future__ import annotations

import pytest

from forge.agent import LLMAgent, OfflineAgent, get_agent
from forge.agent.core import Proposal


def test_offline_agent_replays_gold(mean_task):
    agent = OfflineAgent()
    proposal = agent.propose(mean_task, test_source="", file_contents={})
    assert proposal.source == "offline"
    assert proposal.patch == mean_task.gold_patch()


def test_get_agent_defaults_to_offline(monkeypatch):
    monkeypatch.delenv("FORGE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_agent(), OfflineAgent)


def test_get_agent_selects_provider(monkeypatch):
    monkeypatch.setenv("FORGE_LLM_PROVIDER", "anthropic")
    agent = get_agent()
    assert isinstance(agent, LLMAgent)
    assert agent.name == "anthropic"


def test_get_agent_rejects_unknown(monkeypatch):
    monkeypatch.setenv("FORGE_LLM_PROVIDER", "banana")
    with pytest.raises(ValueError):
        get_agent()


def test_llm_agent_builds_proposal_from_client(mean_task):
    # A fake client standing in for a real provider: returns a structured {plan, patch}.
    class FakeClient:
        def complete(self, messages, schema=None):
            return {"plan": ["fix it"], "patch": mean_task.gold_patch()}

    agent = LLMAgent(FakeClient(), name="fake")
    proposal = agent.propose(mean_task, test_source="", file_contents={"meanstat.py": "x"})
    assert isinstance(proposal, Proposal)
    assert proposal.plan == ["fix it"]
    assert proposal.source == "fake"
