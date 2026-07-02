# Data

## `mini_bench/` — the self-authored benchmark (committed)

A handful of tiny, fully controlled Python repos, each with **one seeded bug** and a test that fails on the
buggy code and passes once the bug is fixed. This is the v0.1 benchmark: fast, deterministic, needs no
Docker, and clean-room (nothing here comes from any real codebase).

Each task is one directory:

```
mini_bench/<task_id>/
  task.json          # id, description, module, test file
  <module>.py        # the buggy source
  test_<module>.py   # the failing test
  gold.patch         # the known-correct unified diff (git apply -p1 compatible)
```

`gold.patch` is committed on purpose. It is the fixture the deterministic `OfflineAgent` replays, so the
whole harness — localization, patch application, sandbox verification, and the eval — runs and is tested
with no API key. A real solve-rate (a model actually *finding* the fix) needs a real provider behind the
`LLMClient`; the gold patch is never shown to that model.

Current tasks:

| task_id | bug |
|---------|-----|
| `mean_off_by_one` | mean divides by `len(xs) - 1` |
| `fizzbuzz_order` | the `% 15` check is unreachable (ordered after `% 3` / `% 5`) |
| `parse_kv_maxsplit` | `split("=")` breaks on values containing `=` (missing `maxsplit=1`) |
| `dedupe_order` | `sorted(set(...))` loses first-seen order |

## `swebench_lite/` — real benchmark (v0.3, not committed)

A small slice of the public SWE-bench-lite dataset will be downloaded here behind the same task adapter in
v0.3, and run in Docker sandboxes. Download is scripted; raw data is never committed (see `.gitignore`).
