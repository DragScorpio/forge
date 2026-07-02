"""Isolated working copies.

Every solve attempt runs in a throwaway copy of the task repo, so the committed snapshot is never touched
and a bad patch can never corrupt the source of truth. The copy is a context manager that cleans itself
up. ``git init`` runs in the copy so patches apply with ``git apply`` even though the mini-bench repos are
not themselves git repositories.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from types import TracebackType


class Workspace:
    """A disposable copy of a task repo. Use as a context manager; the directory is removed on exit."""

    def __init__(self, path: Path):
        self.path = path

    def read(self, relpath: str) -> str:
        """Read a file inside the workspace."""
        return (self.path / relpath).read_text(encoding="utf-8")

    def reset(self, source: Path) -> None:
        """Discard all changes and restore the pristine copy from ``source``."""
        shutil.rmtree(self.path, ignore_errors=True)
        _copy_tree(source, self.path)
        _git_init(self.path)

    def __enter__(self) -> Workspace:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def checkout(source: Path, prefix: str = "forge-ws-") -> Workspace:
    """Copy ``source`` into a fresh temp directory and return an isolated :class:`Workspace`."""
    dest = Path(tempfile.mkdtemp(prefix=prefix))
    _copy_tree(source, dest)
    _git_init(dest)
    return Workspace(dest)


def _copy_tree(source: Path, dest: Path) -> None:
    """Copy the repo snapshot, skipping caches and any stray git metadata from the source."""
    shutil.copytree(
        source,
        dest,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", ".git", ".pytest_cache", ".ruff_cache"),
    )


def _git_init(path: Path) -> None:
    """Make the copy a git repo so ``git apply`` has a work tree; harmless if git is unavailable."""
    try:
        subprocess.run(
            ["git", "init", "-q"],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # git apply can still work outside a repo in modern git; don't fail the run over init.
        pass
