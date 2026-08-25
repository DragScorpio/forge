"""The solve loop: localize -> propose -> apply -> verify, with a classified outcome.

This is the spine of Forge. Every attempt runs in an isolated workspace and ends in exactly one outcome
from a small taxonomy, so a failure tells you *why* it failed, not just that it did. The sandbox — not the
model — decides ``solved``.

v0.2 adds a policy check between propose and apply: a patch that violates a guardrail is refused before
it touches the workspace, and the violation is its own classified outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Agent, get_agent
from .localize import localize
from .policy import Policy, check_patch
from .policy.engine import ALLOW_ALL
from .sandbox import run_tests
from .sandbox.runner import DEFAULT_TIMEOUT_SECONDS
from .tasks import Task
from .tools import apply_patch
from .workspace import checkout

# The outcome taxonomy. Exactly one is assigned per attempt.
SOLVED = "solved"
NO_LOCALIZATION = "no_localization"
POLICY_VIOLATION = "policy_violation"
BAD_PATCH = "bad_patch"
TESTS_FAILED = "tests_failed"
TIMEOUT = "timeout"

FAILURE_MODES = (NO_LOCALIZATION, POLICY_VIOLATION, BAD_PATCH, TESTS_FAILED, TIMEOUT)
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
    policy_violations: list[str] = field(default_factory=list)

    @property
    def solved(self) -> bool:
        return self.outcome == SOLVED


def solve(
    task: Task,
    agent: Agent | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    top_k: int = 5,
    policy: Policy | None = None,
) -> SolveResult:
    """Attempt one task end to end and return a classified :class:`SolveResult`."""
    agent = agent or get_agent()
    policy = policy or ALLOW_ALL
    test_source = (task.repo_dir / task.test_file).read_text(encoding="utf-8")
    files = task.repo_files()

    with checkout(task.repo_dir) as ws:
        # 1) Ground the agent: rank the source files likely to hold the bug. No candidate ranks
        #    means nowhere to point the agent, so it is its own outcome (not a patch failure).
        candidates = localize(ws.path, files, task.description, test_source, top_k=top_k)
        if not candidates:
            return SolveResult(task.task_id, NO_LOCALIZATION, agent.name)

        # 2) Ask the agent for a patch, showing it only the localized files.
        localized = [c.path for c in candidates]
        file_contents = {c.path: ws.read(c.path) for c in candidates}
        proposal = agent.propose(task, test_source, file_contents)

        # 2.5) Policy check: refuse the patch before it touches the workspace if it violates a rule.
        verdict_policy = check_patch(proposal.patch, policy)
        if not verdict_policy.allowed:
            return SolveResult(
                task.task_id,
                POLICY_VIOLATION,
                agent.name,
                localized=localized,
                plan=proposal.plan,
                patch=proposal.patch,
                policy_violations=[v.message for v in verdict_policy.violations],
            )

        # 3) Apply the patch in the throwaway copy. One that won't apply never reaches the tests.
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

        # 4) The gate: the tests decide. Pass -> solved, hang -> timeout, else -> tests_failed.
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
