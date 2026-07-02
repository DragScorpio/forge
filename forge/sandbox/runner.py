"""Run a task's tests in an isolated subprocess with a timeout — the verification gate.

This is the load-bearing idea of the whole harness: a patch is "solved" only if the repo's own tests
actually pass. v0.1 runs ``python -m pytest`` in a subprocess rooted at the workspace copy, with a wall
clock timeout. The mini-bench repos are self-authored and dependency-free, so a subprocess is safe enough
here; running arbitrary public repos (SWE-bench-lite) upgrades this to a container in v0.3. The interface
stays the same, so that swap does not touch the rest of the harness.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class SandboxResult:
    """Outcome of the test run. ``passed`` is the single source of truth for 'solved'."""

    passed: bool
    returncode: int | None
    timed_out: bool
    output: str

    @property
    def status(self) -> str:
        """A short label for reports: passed / failed / timeout."""
        if self.timed_out:
            return "timeout"
        return "passed" if self.passed else "failed"


def run_tests(
    workspace_path,
    test_file: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    python: str | None = None,
) -> SandboxResult:
    """Run ``test_file`` under pytest inside ``workspace_path`` and report pass/fail/timeout.

    The subprocess inherits a clean-ish environment (no bytecode writes, unbuffered) and is hard-killed at
    ``timeout`` seconds so a runaway or hanging patch cannot stall the harness.
    """
    interpreter = python or sys.executable
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.run(
            [interpreter, "-m", "pytest", test_file, "-q", "-p", "no:cacheprovider"],
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        captured = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(captured, bytes):
            captured = captured.decode("utf-8", errors="replace")
        return SandboxResult(False, None, True, captured + f"\n[forge] timed out after {timeout}s")

    return SandboxResult(
        passed=proc.returncode == 0,
        returncode=proc.returncode,
        timed_out=False,
        output=(proc.stdout or "") + (proc.stderr or ""),
    )
