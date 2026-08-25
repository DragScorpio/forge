"""Policy layer: intercept the agent's actions and enforce configurable guardrails.

The policy sits between the agent's proposed patch and the workspace mutation. It answers one question:
"is this patch allowed?" If not, it refuses and logs the violation so the eval can report a safety signal.

Config-driven: load from a ``forge_policy.json`` file or pass a :class:`Policy` directly. An absent config
means "allow everything" (v0.1 behavior, backward compatible).
"""

from .engine import Policy, PolicyVerdict, Violation, check_patch, load_policy

__all__ = ["Policy", "PolicyVerdict", "Violation", "check_patch", "load_policy"]
