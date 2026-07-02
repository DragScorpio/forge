"""The eval harness: run the task set, report solve-rate and a failure-mode breakdown.

Results are versioned under ``eval/results/`` (a stable ``latest.json`` plus timestamped snapshots) so
solve-rate and the failure taxonomy show up in diffs and regressions are visible across commits. Every
non-solve is classified, which is the whole point — you learn why the harness missed, not just that it did.
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .agent import Agent, get_agent
from .solve import FAILURE_MODES, OUTCOMES, SOLVED, SolveResult, solve
from .tasks import Task

DEFAULT_RESULTS_DIR = "eval/results"


@dataclass
class EvalReport:
    """Aggregate result of an eval run: solve-rate plus the per-outcome counts."""

    agent: str
    total: int
    solved: int
    solve_rate: float
    outcomes: dict[str, int]
    tasks: list[dict] = field(default_factory=list)
    generated_at: str = ""
    python: str = ""


def _summarize_task(result: SolveResult) -> dict:
    """One compact row per task for the report (drops the bulky raw test output)."""
    return {
        "task_id": result.task_id,
        "outcome": result.outcome,
        "localized": result.localized,
        "apply_message": result.apply_message,
        "test_status": result.test_status,
    }


def evaluate(
    tasks: list[Task], agent: Agent | None = None, timeout: int | None = None
) -> tuple[EvalReport, list[SolveResult]]:
    """Run every task and aggregate into an :class:`EvalReport`. Returns the report and raw results."""
    agent = agent or get_agent()
    kwargs = {"timeout": timeout} if timeout is not None else {}
    results = [solve(task, agent=agent, **kwargs) for task in tasks]

    counts = {outcome: 0 for outcome in OUTCOMES}
    for r in results:
        counts[r.outcome] += 1
    solved = counts[SOLVED]
    total = len(results)

    report = EvalReport(
        agent=agent.name,
        total=total,
        solved=solved,
        solve_rate=(solved / total) if total else 0.0,
        outcomes=counts,
        tasks=[_summarize_task(r) for r in results],
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python=platform.python_version(),
    )
    return report, results


def failure_breakdown(report: EvalReport) -> dict[str, int]:
    """Just the failure modes (drops the solved count), for a quick "why did we miss" view."""
    return {mode: report.outcomes.get(mode, 0) for mode in FAILURE_MODES}


def save_report(report: EvalReport, out_dir: str | Path = DEFAULT_RESULTS_DIR) -> Path:
    """Write ``latest.json`` (canonical, versioned) plus a timestamped snapshot; return latest.json path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)

    stamp = report.generated_at.replace(":", "").replace("-", "")
    (out / f"eval_{stamp}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = out / "latest.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return latest
