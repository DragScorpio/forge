"""Forge CLI: solve one task, or eval the whole mini-bench.

  * ``forge solve <task_id>`` — localize, patch, apply, verify; print solved / not-solved with evidence.
  * ``forge eval``            — run the mini-bench; report solve-rate + failure-mode breakdown.
  * ``forge list``            — list the available mini-bench tasks.

The active LLM provider is chosen by ``FORGE_LLM_PROVIDER`` (default auto: a key if present, else the
deterministic offline fixture-replay agent).
"""

from __future__ import annotations

import argparse
import sys

from . import evaluation
from .agent import get_agent
from .sandbox.runner import DEFAULT_TIMEOUT_SECONDS
from .solve import SOLVED, solve
from .tasks import load_mini_bench, load_task

_OUTPUT_TAIL_LINES = 25


def _print_solve(result) -> None:
    """Print a readable summary of a single solve attempt."""
    mark = "SOLVED" if result.solved else f"NOT SOLVED ({result.outcome})"
    print(f"task:    {result.task_id}")
    print(f"agent:   {result.agent}")
    print(f"result:  {mark}")
    if result.localized:
        print(f"localized: {', '.join(result.localized)}")
    if result.plan:
        print("plan:")
        for step in result.plan:
            print(f"  - {step}")
    if result.apply_message:
        print(f"apply:   {result.apply_message}")
    if result.test_status != "skipped":
        print(f"tests:   {result.test_status}")
    if result.test_output and not result.solved:
        tail = "\n".join(result.test_output.strip().splitlines()[-_OUTPUT_TAIL_LINES:])
        print("--- test output (tail) ---")
        print(tail)


def cmd_solve(args: argparse.Namespace) -> int:
    """Solve a single mini-bench task and print the outcome with evidence."""
    task = load_task(args.task_id, root=args.tasks)
    result = solve(task, agent=get_agent(), timeout=args.timeout, top_k=args.top_k)
    _print_solve(result)
    return 0 if result.outcome == SOLVED else 1


def cmd_eval(args: argparse.Namespace) -> int:
    """Run the whole mini-bench and report solve-rate + failure-mode breakdown."""
    tasks = load_mini_bench(root=args.tasks)
    report, _ = evaluation.evaluate(tasks, agent=get_agent(), timeout=args.timeout)
    path = evaluation.save_report(report, out_dir=args.out_dir)

    print(f"agent:      {report.agent}")
    print(f"tasks:      {report.total}")
    print(f"solved:     {report.solved}")
    print(f"solve-rate: {report.solve_rate * 100:.1f}%")
    print("failure modes:")
    for mode, count in evaluation.failure_breakdown(report).items():
        print(f"  {mode:<16} {count}")
    print("per task:")
    for row in report.tasks:
        print(f"  {row['task_id']:<24} {row['outcome']}")
    print(f"\nsaved -> {path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List the available mini-bench tasks."""
    for task in load_mini_bench(root=args.tasks):
        print(f"{task.task_id:<24} {task.description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Define the solve / eval / list subcommands and their flags."""
    parser = argparse.ArgumentParser(prog="forge", description="Agentic SWE harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_solve = sub.add_parser("solve", help="solve one task and verify with its tests")
    p_solve.add_argument("task_id", help="mini-bench task id (see `forge list`)")
    p_solve.add_argument("--tasks", default="data/mini_bench", help="mini-bench root")
    p_solve.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    p_solve.add_argument("--top-k", type=int, default=5, help="localizer candidate count")
    p_solve.set_defaults(func=cmd_solve)

    p_eval = sub.add_parser("eval", help="run the mini-bench and report solve-rate")
    p_eval.add_argument("--tasks", default="data/mini_bench", help="mini-bench root")
    p_eval.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    p_eval.add_argument("--out-dir", default=evaluation.DEFAULT_RESULTS_DIR)
    p_eval.set_defaults(func=cmd_eval)

    p_list = sub.add_parser("list", help="list mini-bench tasks")
    p_list.add_argument("--tasks", default="data/mini_bench", help="mini-bench root")
    p_list.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args and dispatch to the chosen subcommand."""
    # Reports use a few non-ASCII glyphs; Windows consoles default to cp1252 and would crash.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):  # pragma: no cover - stream without reconfigure
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
