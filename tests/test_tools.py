"""Tools: patch application accepts a valid diff and rejects bad ones."""

from __future__ import annotations

from forge.tools import apply_patch
from forge.workspace import checkout


def test_apply_gold_patch(mean_task):
    with checkout(mean_task.repo_dir) as ws:
        result = apply_patch(ws, mean_task.gold_patch())
        assert result.applied
        assert "len(xs)" in ws.read("meanstat.py")
        assert "len(xs) - 1" not in ws.read("meanstat.py")


def test_empty_patch_rejected(mean_task):
    with checkout(mean_task.repo_dir) as ws:
        result = apply_patch(ws, "")
        assert not result.applied
        assert "empty" in result.message.lower()


def test_nonapplying_patch_rejected(mean_task, make_diff):
    # A diff whose context does not match the file cannot apply cleanly.
    bogus = make_diff(
        "meanstat.py",
        "def other():\n    return 1\n",
        "def other():\n    return 2\n",
    )
    with checkout(mean_task.repo_dir) as ws:
        result = apply_patch(ws, bogus)
        assert not result.applied
