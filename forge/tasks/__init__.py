"""Task providers: load a bug-fix task (a repo snapshot + a failing test) behind one interface.

v0.1 ships the self-authored mini-bench adapter. A SWE-bench-lite adapter slots in behind the same
:class:`Task` shape in v0.3 without touching the rest of the harness.
"""

from .minibench import Task, load_mini_bench, load_task

__all__ = ["Task", "load_mini_bench", "load_task"]
