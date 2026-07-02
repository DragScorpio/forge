"""Keyword localizer: ranking, empty-query handling, and the no-match signal."""

from __future__ import annotations

from forge.localize import localize
from forge.localize.keyword import query_terms, tokenize


def test_tokenize_drops_stopwords():
    tokens = tokenize("def return the value")
    assert "def" not in tokens and "return" not in tokens and "value" not in tokens


def test_localizes_the_buggy_module(mean_task):
    test_source = (mean_task.repo_dir / mean_task.test_file).read_text(encoding="utf-8")
    candidates = localize(
        mean_task.repo_dir, mean_task.repo_files(), mean_task.description, test_source
    )
    assert candidates, "expected the buggy module to be localized"
    assert candidates[0].path == "meanstat.py"
    assert 0.0 < candidates[0].score <= 1.0


def test_no_overlap_returns_empty(tmp_path):
    (tmp_path / "unrelated.py").write_text("zzz = 1\n", encoding="utf-8")
    assert localize(tmp_path, ["unrelated.py"], "quartz obsidian granite", "") == []


def test_empty_query_returns_empty(mean_task):
    assert localize(mean_task.repo_dir, mean_task.repo_files(), "", "") == []


def test_query_terms_union():
    terms = query_terms("compute mean", "assert average works")
    assert "compute" in terms and "average" in terms
