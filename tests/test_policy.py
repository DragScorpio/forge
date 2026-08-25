"""Policy engine: rule enforcement, config loading, and integration with the solve loop."""

from __future__ import annotations

import json

from forge.agent import OfflineAgent
from forge.policy import Policy, check_patch, load_policy
from forge.policy.engine import ALLOW_ALL, _count_changed_lines, _parse_touched_files
from forge.solve import POLICY_VIOLATION, solve

# ------------------------------------------------------------------- diff parsing


SAMPLE_DIFF = """\
diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 def greet():
-    return "hello"
+    return "hi"
"""

TWO_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,3 @@
 def greet():
-    return "hello"
+    return "hi"
diff --git a/bar.py b/bar.py
--- a/bar.py
+++ b/bar.py
@@ -1,2 +1,3 @@
 x = 1
+y = 2
"""


def test_parse_touched_files_single():
    assert _parse_touched_files(SAMPLE_DIFF) == ["foo.py"]


def test_parse_touched_files_multi():
    assert _parse_touched_files(TWO_FILE_DIFF) == ["foo.py", "bar.py"]


def test_count_changed_lines_single():
    # One removed line + one added line = 2.
    assert _count_changed_lines(SAMPLE_DIFF) == 2


def test_count_changed_lines_multi():
    # foo: 1 removed + 1 added; bar: 1 added = 3.
    assert _count_changed_lines(TWO_FILE_DIFF) == 3


# ------------------------------------------------------------------- rule enforcement


def test_allow_all_permits_everything():
    assert check_patch(SAMPLE_DIFF, ALLOW_ALL).allowed


def test_protected_path_blocks():
    policy = Policy(protected_paths=["foo.py"])
    verdict = check_patch(SAMPLE_DIFF, policy)
    assert not verdict.allowed
    assert verdict.violations[0].rule == "protected_path"
    assert "foo.py" in verdict.violations[0].message


def test_protected_path_glob():
    policy = Policy(protected_paths=["*.py"])
    verdict = check_patch(TWO_FILE_DIFF, policy)
    assert not verdict.allowed
    assert len(verdict.violations) == 2


def test_max_files_blocks():
    policy = Policy(max_files=1)
    verdict = check_patch(TWO_FILE_DIFF, policy)
    assert not verdict.allowed
    assert verdict.violations[0].rule == "max_files"


def test_max_files_allows():
    policy = Policy(max_files=2)
    assert check_patch(TWO_FILE_DIFF, policy).allowed


def test_max_total_lines_blocks():
    policy = Policy(max_total_lines=1)
    verdict = check_patch(SAMPLE_DIFF, policy)
    assert not verdict.allowed
    assert verdict.violations[0].rule == "max_total_lines"


def test_max_total_lines_allows():
    policy = Policy(max_total_lines=10)
    assert check_patch(SAMPLE_DIFF, policy).allowed


def test_required_pattern_blocks(tmp_path):
    (tmp_path / "foo.py").write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
    policy = Policy(required_patterns=[r"# Copyright"])
    verdict = check_patch(SAMPLE_DIFF, policy, workspace_path=tmp_path)
    assert not verdict.allowed
    assert verdict.violations[0].rule == "required_pattern"


def test_required_pattern_allows(tmp_path):
    (tmp_path / "foo.py").write_text("# Copyright 2026\ndef greet():\n    return 'hi'\n", encoding="utf-8")
    policy = Policy(required_patterns=[r"# Copyright"])
    assert check_patch(SAMPLE_DIFF, policy, workspace_path=tmp_path).allowed


def test_multiple_violations():
    policy = Policy(protected_paths=["foo.py"], max_files=0)
    verdict = check_patch(SAMPLE_DIFF, policy)
    assert not verdict.allowed
    rules = {v.rule for v in verdict.violations}
    assert "protected_path" in rules
    assert "max_files" in rules


# ------------------------------------------------------------------- config loading


def test_load_policy_missing_file_returns_allow_all(tmp_path):
    p = load_policy(tmp_path / "nope.json")
    assert p is ALLOW_ALL


def test_load_policy_from_file(tmp_path):
    config = {"protected_paths": ["*.lock"], "max_files": 3, "max_total_lines": 50}
    (tmp_path / "policy.json").write_text(json.dumps(config), encoding="utf-8")
    p = load_policy(tmp_path / "policy.json")
    assert p.protected_paths == ["*.lock"]
    assert p.max_files == 3
    assert p.max_total_lines == 50


# ------------------------------------------------------------------- solve integration


def test_policy_violation_outcome(mean_task):
    # The gold patch touches meanstat.py; block it with a protected path.
    policy = Policy(protected_paths=["meanstat.py"])
    result = solve(mean_task, agent=OfflineAgent(), policy=policy)
    assert result.outcome == POLICY_VIOLATION
    assert not result.solved
    assert any("meanstat.py" in v for v in result.policy_violations)


def test_no_policy_still_solves(all_tasks):
    # v0.1 behavior: no policy = ALLOW_ALL = everything passes.
    agent = OfflineAgent()
    for task in all_tasks:
        result = solve(task, agent=agent)
        assert result.solved, f"{task.task_id}: {result.outcome}"


def test_permissive_policy_still_solves(mean_task):
    policy = Policy(max_files=10, max_total_lines=100)
    result = solve(mean_task, agent=OfflineAgent(), policy=policy)
    assert result.solved
