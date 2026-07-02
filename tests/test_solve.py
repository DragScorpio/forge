"""End-to-end solve loop with the offline agent: every mini-bench task is solved, outcomes classify."""

from __future__ import annotations

from forge.agent import OfflineAgent
from forge.solve import BAD_PATCH, NO_LOCALIZATION, SOLVED, solve
from forge.tasks import Task


def test_offline_solves_every_task(all_tasks):
    agent = OfflineAgent()
    for task in all_tasks:
        result = solve(task, agent=agent)
        assert result.solved, f"{task.task_id}: {result.outcome}\n{result.test_output}"
        assert result.outcome == SOLVED
        assert result.test_status == "passed"
        assert task.module in result.localized


def test_bad_patch_outcome(mean_task):
    class BadAgent:
        name = "bad"

        def propose(self, task, test_source, file_contents):
            from forge.agent.core import Proposal

            return Proposal(plan=[], patch="not a diff at all", source=self.name)

    result = solve(mean_task, agent=BadAgent())
    assert result.outcome == BAD_PATCH
    assert not result.solved


def test_no_localization_outcome(tmp_path):
    # A task whose description/test share no salient terms with the source => nothing localizes.
    (tmp_path / "zzz.py").write_text("qqq = 1\n", encoding="utf-8")
    (tmp_path / "test_zzz.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    (tmp_path / "gold.patch").write_text("diff --git a/zzz.py b/zzz.py\n", encoding="utf-8")
    (tmp_path / "task.json").write_text("{}", encoding="utf-8")
    task = Task(
        task_id="empty",
        description="quartz obsidian granite",
        module="zzz.py",
        test_file="test_zzz.py",
        repo_dir=tmp_path,
    )
    result = solve(task, agent=OfflineAgent())
    assert result.outcome == NO_LOCALIZATION
