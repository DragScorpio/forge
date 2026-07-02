"""The solve loop: localize -> propose -> apply -> verify, with a classified outcome.

This is the spine of Forge. Every attempt runs in an isolated workspace and ends in exactly one outcome
from a small taxonomy, so a failure tells you *why* it failed, not just that it did. The sandbox — not the
model — decides ``solved``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Agent, get_agent
from .localize import localize
from .sandbox import run_tests
from .sandbox.runner import DEFAULT_TIMEOUT_SECONDS
from .tasks import Task
from .tools import apply_patch
from .workspace import checkout

# The outcome taxonomy. Exactly one is assigned per attempt.
SOLVED = "solved"
NO_LOCALIZATION = "no_localization"
BAD_PATCH = "bad_patch"
TESTS_FAILED = "tests_failed"
TIMEOUT = "timeout"

FAILURE_MODES = (NO_LOCALIZATION, BAD_PATCH, TESTS_FAILED, TIMEOUT)
OUTCOMES = (SOLVED, *FAILURE_MODES)


@dataclass
class SolveResult:
    """The full record of one solve attempt, enough to explain and reproduce the outcome."""

    task_id: str
    outcome: str
    agent: str
    localized: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    patch: str = ""
    apply_message: str = ""
    test_status: str = "skipped"
    test_output: str = ""

    @property
    def solved(self) -> bool:
        return self.outcome == SOLVED


def solve(
    task: Task,
    agent: Agent | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    top_k: int = 5,
) -> SolveResult:
    """Attempt one task end to end and return a classified :class:`SolveResult`."""
    agent = agent or get_agent()
    test_source = (task.repo_dir / task.test_file).read_text(encoding="utf-8")
    files = task.repo_files()

    with checkout(task.repo_dir) as ws:
        candidates = localize(ws.path, files, task.description, test_source, top_k=top_k)
        if not candidates:
            return SolveResult(task.task_id, NO_LOCALIZATION, agent.name)

        localized = [c.path for c in candidates]
        file_contents = {c.path: ws.read(c.path) for c in candidates}
        proposal = agent.propose(task, test_source, file_contents)

        applied = apply_patch(ws, proposal.patch)
        if not applied.applied:
            return SolveResult(
                task.task_id,
                BAD_PATCH,
                agent.name,
                localized=localized,
                plan=proposal.plan,
                patch=proposal.patch,
                apply_message=applied.message,
            )

        verdict = run_tests(ws.path, task.test_file, timeout=timeout)
        if verdict.passed:
            outcome = SOLVED
        elif verdict.timed_out:
            outcome = TIMEOUT
        else:
            outcome = TESTS_FAILED

        return SolveResult(
            task.task_id,
            outcome,
            agent.name,
            localized=localized,
            plan=proposal.plan,
            patch=proposal.patch,
            apply_message=applied.message,
            test_status=verdict.status,
            test_output=verdict.output,
        )
