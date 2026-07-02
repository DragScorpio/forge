"""Workspace isolation: attempts run on a copy, never the committed task repo."""

from __future__ import annotations

from forge.workspace import checkout


def test_checkout_copies_files(mean_task):
    with checkout(mean_task.repo_dir) as ws:
        assert (ws.path / "meanstat.py").is_file()
        assert ws.read("meanstat.py") == (mean_task.repo_dir / "meanstat.py").read_text(
            encoding="utf-8"
        )


def test_edits_do_not_touch_source(mean_task):
    original = (mean_task.repo_dir / "meanstat.py").read_text(encoding="utf-8")
    with checkout(mean_task.repo_dir) as ws:
        (ws.path / "meanstat.py").write_text("# clobbered\n", encoding="utf-8")
    # The committed task repo is unchanged after the workspace is used and torn down.
    assert (mean_task.repo_dir / "meanstat.py").read_text(encoding="utf-8") == original


def test_workspace_cleaned_up(mean_task):
    with checkout(mean_task.repo_dir) as ws:
        path = ws.path
        assert path.exists()
    assert not path.exists()
