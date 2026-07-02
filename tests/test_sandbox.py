"""Sandbox verification gate — the load-bearing test: it must reject a patch that leaves the bug.

A patch that applies cleanly but does not fix the code must NOT be reported as solved. This is what keeps
the harness honest: the tests decide, not the model.
"""

from __future__ import annotations

from forge.sandbox import run_tests
from forge.tools import apply_patch
from forge.workspace import checkout


def test_gate_passes_on_correct_patch(mean_task):
    with checkout(mean_task.repo_dir) as ws:
        assert apply_patch(ws, mean_task.gold_patch()).applied
        verdict = run_tests(ws.path, mean_task.test_file)
        assert verdict.passed
        assert verdict.status == "passed"


def test_gate_rejects_knowingly_wrong_patch(mean_task, make_diff):
    original = (mean_task.repo_dir / "meanstat.py").read_text(encoding="utf-8")
    # Applies cleanly (only edits the docstring) but leaves the off-by-one bug in place.
    wrong = make_diff(
        "meanstat.py",
        original,
        original.replace("non-empty list of numbers", "list of numbers"),
    )
    with checkout(mean_task.repo_dir) as ws:
        assert apply_patch(ws, wrong).applied, "the wrong patch should still apply"
        verdict = run_tests(ws.path, mean_task.test_file)
        assert not verdict.passed, "gate must reject a patch that does not fix the bug"
        assert verdict.status == "failed"


def test_gate_fails_on_untouched_bug(mean_task):
    # No patch at all: the seeded bug means the test fails, proving the task is genuinely broken.
    with checkout(mean_task.repo_dir) as ws:
        verdict = run_tests(ws.path, mean_task.test_file)
        assert not verdict.passed
