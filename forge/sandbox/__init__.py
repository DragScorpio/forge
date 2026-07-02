"""Sandbox executor: the verification gate. The tests decide, not the model."""

from .runner import SandboxResult, run_tests

__all__ = ["SandboxResult", "run_tests"]
