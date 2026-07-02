"""Shared fixtures and helpers for the Forge test suite."""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from forge.tasks import Task, load_mini_bench, load_task

MINI_BENCH_ROOT = Path(__file__).resolve().parents[1] / "data" / "mini_bench"


@pytest.fixture
def mini_bench_root() -> Path:
    """Absolute path to the committed mini-bench, independent of the test's cwd."""
    return MINI_BENCH_ROOT


@pytest.fixture
def all_tasks(mini_bench_root: Path) -> list[Task]:
    """Every mini-bench task."""
    return load_mini_bench(root=mini_bench_root)


@pytest.fixture
def mean_task(mini_bench_root: Path) -> Task:
    """The off-by-one mean task, used as the representative single task in several tests."""
    return load_task("mean_off_by_one", root=mini_bench_root)


def _make_diff(module: str, original: str, modified: str) -> str:
    """Build a git-apply-compatible unified diff between two versions of one file."""
    body = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=f"a/{module}",
            tofile=f"b/{module}",
            lineterm="\n",
        )
    )
    return f"diff --git a/{module} b/{module}\n{body}"


@pytest.fixture
def make_diff():
    """Expose the diff builder as a fixture so tests don't need a package-relative import."""
    return _make_diff
