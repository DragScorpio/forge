"""The mini-bench task adapter.

A mini-bench task is a tiny, self-authored Python repo with one seeded bug and a test that fails on the
buggy code and passes once the bug is fixed. Each task lives in its own directory::

    data/mini_bench/<task_id>/
        task.json          # metadata (id, description, module, test file)
        <module>.py        # the buggy source
        test_<module>.py   # the failing test
        gold.patch         # the known-correct unified diff (fixture for the offline agent)

The mini-bench is committed on purpose: it is fully controlled, fast, needs no Docker, and its gold patch
gives the offline-deterministic path a known-correct fixture. Public benchmarks (SWE-bench-lite) come
later behind this same :class:`Task` interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MINI_BENCH = "data/mini_bench"
_META_FILE = "task.json"
_GOLD_FILE = "gold.patch"


@dataclass(frozen=True)
class Task:
    """One bug-fix task. ``repo_dir`` holds the committed buggy repo snapshot (never mutated)."""

    task_id: str
    description: str
    module: str
    test_file: str
    repo_dir: Path

    @property
    def gold_patch_path(self) -> Path:
        """Path to the committed known-correct unified diff for this task."""
        return self.repo_dir / _GOLD_FILE

    def gold_patch(self) -> str:
        """Read the known-correct patch. The offline agent replays this; the eval never shows it to a model."""
        return self.gold_patch_path.read_text(encoding="utf-8")

    def repo_files(self) -> list[str]:
        """Source files a solver may read/patch: the repo's ``.py`` files minus the tests."""
        files = []
        for path in sorted(self.repo_dir.glob("*.py")):
            name = path.name
            if name.startswith("test_") or name == "conftest.py":
                continue
            files.append(name)
        return files


def load_task(task_id: str, root: str | Path = DEFAULT_MINI_BENCH) -> Task:
    """Load a single mini-bench task by id."""
    task_dir = Path(root) / task_id
    if not task_dir.is_dir():
        raise FileNotFoundError(f"no mini-bench task {task_id!r} under {root}")
    return _load_dir(task_dir)


def load_mini_bench(root: str | Path = DEFAULT_MINI_BENCH) -> list[Task]:
    """Load every mini-bench task under ``root`` (any subdir with a task.json), sorted by id."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"mini-bench root not found: {root}")
    tasks = [_load_dir(d) for d in sorted(root.iterdir()) if (d / _META_FILE).is_file()]
    if not tasks:
        raise FileNotFoundError(f"no tasks (no */task.json) under {root}")
    return tasks


def _load_dir(task_dir: Path) -> Task:
    """Build a :class:`Task` from a task directory, validating that its files exist."""
    meta = json.loads((task_dir / _META_FILE).read_text(encoding="utf-8"))
    task = Task(
        task_id=meta["id"],
        description=meta["description"],
        module=meta["module"],
        test_file=meta["test_file"],
        repo_dir=task_dir,
    )
    for required in (task.module, task.test_file, _GOLD_FILE):
        if not (task_dir / required).is_file():
            raise FileNotFoundError(f"task {task.task_id!r} missing {required}")
    return task
