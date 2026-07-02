"""Build the agent's prompt: the task, the failing test, and the localized source it may edit.

The prompt grounds the model in exactly the files the localizer surfaced, and asks for a unified diff so
the output can be fed straight to ``git apply``. Only real providers ever see this prompt; the offline
path replays a fixture and never calls a model.
"""

from __future__ import annotations

from ..tasks import Task

_SYSTEM = (
    "You are a careful software engineer fixing a bug in a small Python repository. You are given the "
    "task, the failing test, and the source files most likely responsible. Find the smallest change that "
    "makes the failing test pass without breaking anything else.\n\n"
    "Hard rules:\n"
    "- Return a PLAN (a few short steps) and a PATCH.\n"
    "- The PATCH must be a unified diff compatible with `git apply -p1`: use `--- a/<file>` and "
    "`+++ b/<file>` headers and correct `@@` hunks.\n"
    "- Edit ONLY the source files provided. Do not modify the test.\n"
    "- Keep the change minimal and targeted at the bug."
)


def _render_files(file_contents: dict[str, str]) -> str:
    """Lay out each candidate file with a header and a fenced body for the model to read."""
    blocks = []
    for path, body in file_contents.items():
        blocks.append(f"--- FILE: {path} ---\n```python\n{body}\n```")
    return "\n\n".join(blocks)


def build_messages(
    task: Task, test_source: str, file_contents: dict[str, str]
) -> list[dict[str, str]]:
    """Assemble the system + user messages for a patch-proposal request."""
    user = (
        f"TASK: {task.description}\n\n"
        f"FAILING TEST ({task.test_file}):\n```python\n{test_source}\n```\n\n"
        f"SOURCE FILES YOU MAY EDIT:\n{_render_files(file_contents)}\n\n"
        "Return the plan and the unified-diff patch that makes the failing test pass."
    )
    return [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}]
