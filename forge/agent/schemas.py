"""JSON schema for the agent's structured output.

Forcing the model to return a ``{plan, patch}`` object (not free text) keeps the harness vendor-neutral
and lets the loop feed ``patch`` straight into ``git apply``. The patch is a plain unified diff so the
verification gate — not the model — decides whether it is any good.
"""

from __future__ import annotations

from typing import Any

PATCH_PROPOSAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "plan": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short ordered steps describing the intended fix.",
        },
        "patch": {
            "type": "string",
            "description": (
                "A unified diff that fixes the bug, compatible with `git apply -p1` "
                "(use a/<file> and b/<file> headers). Edit only the provided source files."
            ),
        },
    },
    "required": ["plan", "patch"],
}
