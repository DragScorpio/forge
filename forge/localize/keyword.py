"""Keyword localization: a deterministic lexical ranker over the repo's source files.

Score each candidate file by the overlap between its tokens and the task's query terms (drawn from the
description plus the failing test). It is deliberately simple; the point of v0.1 is the verified loop, and
a keyword baseline both grounds the agent and gives a semantic ranker something to beat later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")
# Terms too generic to help localization; ignored when building the query and when scoring.
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "def",
        "return",
        "import",
        "from",
        "self",
        "test",
        "assert",
        "true",
        "false",
        "none",
        "value",
        "result",
        "with",
        "that",
        "this",
        "should",
        "when",
        "then",
        "into",
    }
)


@dataclass(frozen=True)
class Candidate:
    """A ranked source file. ``score`` is the fraction of query terms found in the file."""

    path: str
    score: float
    matched: tuple[str, ...]


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, minus stopwords and pure-noise short tokens."""
    return [t for t in (m.group().lower() for m in _TOKEN.finditer(text)) if t not in _STOPWORDS]


def query_terms(description: str, test_source: str) -> set[str]:
    """Salient terms that describe the bug: the union of description and failing-test tokens."""
    return set(tokenize(description)) | set(tokenize(test_source))


def localize(
    repo_dir: Path, files: list[str], description: str, test_source: str, top_k: int = 5
) -> list[Candidate]:
    """Rank ``files`` (repo-relative) by lexical overlap with the query; most relevant first.

    Files with zero overlap are dropped, so an empty result is a real "could not localize" signal that the
    eval can classify, not a silently mis-ranked list.
    """
    query = query_terms(description, test_source)
    if not query:
        return []
    scored: list[Candidate] = []
    for rel in files:
        tokens = set(tokenize((repo_dir / rel).read_text(encoding="utf-8")))
        # Score = share of the query's terms this file contains. A file with no overlap is not a
        # candidate at all, so it is dropped rather than ranked last.
        matched = query & tokens
        if not matched:
            continue
        scored.append(
            Candidate(path=rel, score=len(matched) / len(query), matched=tuple(sorted(matched)))
        )
    # Best score first; break ties by path so the ranking is stable and reproducible.
    scored.sort(key=lambda c: (-c.score, c.path))
    return scored[:top_k]
