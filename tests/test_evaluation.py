"""Eval harness: solve-rate, failure breakdown, and versioned results."""

from __future__ import annotations

import json

from forge import evaluation
from forge.agent import OfflineAgent
from forge.solve import SOLVED


def test_offline_full_solve_rate(all_tasks):
    report, results = evaluation.evaluate(all_tasks, agent=OfflineAgent())
    assert report.total == len(all_tasks)
    assert report.solved == len(all_tasks)
    assert report.solve_rate == 1.0
    assert report.outcomes[SOLVED] == len(all_tasks)
    assert all(r.solved for r in results)


def test_failure_breakdown_keys(all_tasks):
    report, _ = evaluation.evaluate(all_tasks, agent=OfflineAgent())
    breakdown = evaluation.failure_breakdown(report)
    assert set(breakdown) == {"no_localization", "bad_patch", "tests_failed", "timeout"}
    assert sum(breakdown.values()) == 0  # offline solves everything


def test_save_report_writes_latest(all_tasks, tmp_path):
    report, _ = evaluation.evaluate(all_tasks, agent=OfflineAgent())
    latest = evaluation.save_report(report, out_dir=tmp_path)
    assert latest.name == "latest.json"
    saved = json.loads(latest.read_text(encoding="utf-8"))
    assert saved["solve_rate"] == 1.0
    assert saved["agent"] == "offline"
    # A timestamped snapshot is written alongside latest.json.
    assert len(list(tmp_path.glob("eval_*.json"))) == 1
