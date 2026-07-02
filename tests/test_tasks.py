"""Task adapter: loading, metadata, and the files a solver may touch."""

from __future__ import annotations

import pytest

from forge.tasks import load_mini_bench, load_task


def test_load_all_tasks(all_tasks):
    ids = {t.task_id for t in all_tasks}
    assert {"mean_off_by_one", "fizzbuzz_order", "parse_kv_maxsplit", "dedupe_order"} <= ids


def test_task_fields_and_files(mean_task):
    assert mean_task.module == "meanstat.py"
    assert mean_task.test_file == "test_meanstat.py"
    # repo_files excludes the test file.
    assert mean_task.repo_files() == ["meanstat.py"]


def test_gold_patch_readable(mean_task):
    patch = mean_task.gold_patch()
    assert patch.startswith("diff --git")
    assert "len(xs)" in patch


def test_missing_task_raises(mini_bench_root):
    with pytest.raises(FileNotFoundError):
        load_task("does_not_exist", root=mini_bench_root)


def test_missing_root_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_mini_bench(root=tmp_path / "nope")
