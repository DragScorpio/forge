"""Policy engine: parse a unified diff, enforce each rule, and return a verdict.

Rules (all optional, config-driven):
  - **protected_paths**: glob patterns the agent may not touch. A hunk targeting a protected file is
    refused, even if the patch otherwise applies. Think ``tests/``, ``Makefile``, ``*.lock``.
  - **max_files**: how many files the patch may modify. A surgical change is safer than a broad rewrite.
  - **max_total_lines**: total added + removed lines across the patch. Caps scope creep.
  - **required_patterns**: regex patterns that must appear in every changed file after patching. Lets you
    require e.g. a copyright header or a type annotation per file.

A patch that violates nothing gets ``PolicyVerdict(allowed=True)``; one that violates anything gets
``allowed=False`` with the list of violations, so the eval can count and classify them.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_POLICY_FILE = "forge_policy.json"


@dataclass(frozen=True)
class Policy:
    """The rule set. Every field is optional; an absent field means 'no constraint'."""

    protected_paths: list[str] = field(default_factory=list)
    max_files: int | None = None
    max_total_lines: int | None = None
    required_patterns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Violation:
    """One broken rule: which rule, which file (if applicable), and a human message."""

    rule: str
    path: str | None
    message: str


@dataclass
class PolicyVerdict:
    """The outcome of checking a patch against a policy."""

    allowed: bool
    violations: list[Violation] = field(default_factory=list)


# No policy = allow everything (backward compatible with v0.1).
ALLOW_ALL = Policy()


def load_policy(path: str | Path = DEFAULT_POLICY_FILE) -> Policy:
    """Load a policy from a JSON file. Missing file -> ALLOW_ALL (no guardrails)."""
    p = Path(path)
    if not p.is_file():
        return ALLOW_ALL
    raw = json.loads(p.read_text(encoding="utf-8"))
    return Policy(
        protected_paths=raw.get("protected_paths", []),
        max_files=raw.get("max_files"),
        max_total_lines=raw.get("max_total_lines"),
        required_patterns=raw.get("required_patterns", []),
    )


def _parse_touched_files(diff: str) -> list[str]:
    """Extract the list of files a unified diff modifies (from the +++ b/<path> headers)."""
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
    return files


def _count_changed_lines(diff: str) -> int:
    """Total added + removed lines (lines starting with + or - inside hunks, not headers)."""
    count = 0
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if line.startswith(("diff --git", "---", "+++")):
            in_hunk = False
            continue
        if in_hunk and len(line) > 0 and line[0] in ("+", "-"):
            count += 1
    return count


def check_patch(
    diff: str,
    policy: Policy,
    workspace_path: Path | None = None,
) -> PolicyVerdict:
    """Check a patch against every rule in the policy and return the verdict.

    ``workspace_path`` is needed only for ``required_patterns`` (reads the patched files); when absent
    that rule is skipped.
    """
    if policy is ALLOW_ALL:
        return PolicyVerdict(allowed=True)

    violations: list[Violation] = []
    files = _parse_touched_files(diff)

    # Rule: protected paths.
    for f in files:
        for pattern in policy.protected_paths:
            if fnmatch.fnmatch(f, pattern):
                violations.append(Violation(
                    rule="protected_path",
                    path=f,
                    message=f"{f} matches protected pattern '{pattern}'",
                ))

    # Rule: max files.
    if policy.max_files is not None and len(files) > policy.max_files:
        violations.append(Violation(
            rule="max_files",
            path=None,
            message=f"patch touches {len(files)} files (limit {policy.max_files})",
        ))

    # Rule: max total changed lines.
    changed = _count_changed_lines(diff)
    if policy.max_total_lines is not None and changed > policy.max_total_lines:
        violations.append(Violation(
            rule="max_total_lines",
            path=None,
            message=f"patch changes {changed} lines (limit {policy.max_total_lines})",
        ))

    # Rule: required patterns (checked in the post-patch file content).
    if policy.required_patterns and workspace_path is not None:
        for f in files:
            fpath = workspace_path / f
            if not fpath.is_file():
                continue
            content = fpath.read_text(encoding="utf-8")
            for pat in policy.required_patterns:
                if not re.search(pat, content):
                    violations.append(Violation(
                        rule="required_pattern",
                        path=f,
                        message=f"{f} missing required pattern '{pat}'",
                    ))

    return PolicyVerdict(allowed=len(violations) == 0, violations=violations)
