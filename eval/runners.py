"""Convenience runner: evaluate the mini-bench and save results.

Equivalent to ``forge eval`` but importable/scriptable. Run with ``python -m eval.runners`` from the repo
root, or call :func:`run` from a notebook or test.
"""

from __future__ import annotations

from pathlib import Path

from forge import evaluation
from forge.agent import get_agent
from forge.tasks import load_mini_bench

MINI_BENCH = "data/mini_bench"


def run(tasks_root: str = MINI_BENCH, out_dir: str = evaluation.DEFAULT_RESULTS_DIR) -> Path:
    """Run the full mini-bench eval and write the report; return the latest.json path."""
    tasks = load_mini_bench(root=tasks_root)
    report, _ = evaluation.evaluate(tasks, agent=get_agent())
    return evaluation.save_report(report, out_dir=out_dir)


if __name__ == "__main__":
    print(f"saved -> {run()}")
