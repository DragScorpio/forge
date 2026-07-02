"""The agent's tool interface: a small, explicit set of actions over a workspace.

Read-only tools (:func:`read_file`, :func:`search`) and the mutating tool (:func:`apply_patch`) are kept
separate by design — that boundary is what the policy layer will guard in v0.2. Test execution is the
sandbox's job and lives in :mod:`forge.sandbox`, so the mutating surface here is exactly one action:
applying a patch.
"""

from .tools import ApplyResult, apply_patch, read_file, search

__all__ = ["ApplyResult", "apply_patch", "read_file", "search"]
