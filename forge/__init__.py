"""Forge — an agentic software-engineering harness.

Give it a bug (a failing test in a repo) and it localizes the code, proposes a patch, applies it in an
isolated workspace, and proves the fix by running the repo's own tests in a sandbox. Nothing is reported
solved unless the tests actually pass. The LLM is one component; the value is the verification-first
harness around it.
"""

__version__ = "0.0.1"
