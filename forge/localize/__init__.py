"""Localization: rank the repo files most likely relevant to a task, to ground the agent.

v0.1 ships a keyword/lexical ranker — deterministic, dependency-free, and reproducible with no model. It
scores each source file by how many of the task's salient terms (from the description and the failing
test) it contains. A semantic ranker (sentence-transformers, reusing the Lens patterns) slots in behind
the same :func:`localize` signature in a later version.
"""

from .keyword import Candidate, localize

__all__ = ["Candidate", "localize"]
