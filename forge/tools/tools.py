"""Concrete tools over a workspace copy.

``apply_patch`` is the only mutating tool. It applies a unified diff with ``git apply`` inside the
isolated workspace, so a malformed or non-applying patch is caught here and reported as a distinct failure
mode rather than silently corrupting files.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..localize import Candidate, localize
from ..workspace import Workspace


def read_file(workspace: Workspace, relpath: str) -> str:
    """Read-only: return the contents of a file inside the workspace."""
    return workspace.read(relpath)


def search(workspace: Workspace, query: str, files: list[str], top_k: int = 5) -> list[Candidate]:
    """Read-only: rank ``files`` by lexical relevance to ``query`` (reuses the localizer)."""
    return localize(workspace.path, files, query, "", top_k=top_k)


@dataclass(frozen=True)
class ApplyResult:
    """Outcome of applying a patch. ``applied`` is the gate: false means the diff never touched the files."""

    applied: bool
    message: str


def apply_patch(workspace: Workspace, diff: str) -> ApplyResult:
    """Mutating: apply a unified diff inside the workspace with ``git apply``.

    Returns ``applied=False`` (not an exception) for an empty or non-applying patch, so the caller can
    classify it as the ``bad_patch`` failure mode.
    """
    if not diff or not diff.strip():
        return ApplyResult(False, "empty patch")

    # git apply needs the diff to end with a newline, or it rejects the final hunk.
    if not diff.endswith("\n"):
        diff += "\n"

    with tempfile.NamedTemporaryFile(
        "w", suffix=".patch", delete=False, encoding="utf-8", newline="\n"
    ) as fh:
        patch_path = Path(fh.name)
        fh.write(diff)
    try:
        proc = subprocess.run(
            ["git", "apply", "-p1", "--whitespace=nowarn", str(patch_path)],
            cwd=workspace.path,
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # git missing on PATH
        patch_path.unlink(missing_ok=True)
        return ApplyResult(False, f"git apply unavailable: {exc}")
    patch_path.unlink(missing_ok=True)

    if proc.returncode == 0:
        return ApplyResult(True, "patch applied")
    return ApplyResult(False, (proc.stderr or proc.stdout or "git apply failed").strip())
