# Forge

**An agentic software-engineering harness that trusts the tests, not the model.**

Give Forge a bug (a failing test in a repo). It finds the relevant code, proposes a patch, applies it in an
isolated workspace, and then **proves the fix by running the repo's own tests in a sandbox.** Nothing is
reported solved unless the tests actually pass.

The LLM is one component inside a real engineering system. The value is everything around it: the
retrieval that grounds the model, the tools it acts through, the sandbox that verifies its work, and the
eval that measures how often it truly succeeds. That verification-first spine is the whole point.

> Part of a personal, clean-room build initiative. Forge is built only from public agentic-SWE patterns
> (SWE-agent / OpenHands / Aider style) and open benchmarks. No employer code or internal detail.

## The idea in one loop

```
task (failing test)
      │
      ▼
  localize ──►  agent proposes  ──►  apply patch  ──►  run tests in sandbox
 (retrieval)     {plan, patch}      (git apply)          (the verdict)
      │                                                        │
      └──────────────── one classified outcome ◄───────────────┘
        solved · no_localization · bad_patch · tests_failed · timeout
```

The model *proposes*. The tests *decide*. Every attempt ends in exactly one outcome, so a miss tells you
**why** it missed, not just that it did.

## Quickstart

Requires Python 3.11+ and [`uv`](https://github.com/astral-sh/uv). No API key needed to run everything
below.

```bash
uv venv
uv pip install -e ".[dev]"        # add ",anthropic" or ",openai" for a real model
```

```console
$ forge list
dedupe_order        dedupe() should remove duplicates while keeping first-seen order, but it reorders...
fizzbuzz_order      fizzbuzz() ... but fizzbuzz(15) returns the wrong label.
mean_off_by_one     mean() ... the average of [2, 4, 6] should be 4.0.
parse_kv_maxsplit   parse_kv() ... breaks when the value itself contains an '=' character.

$ forge solve fizzbuzz_order
task:    fizzbuzz_order
agent:   offline
result:  SOLVED
localized: fizzbuzz.py
plan:
  - replay the committed gold patch (offline fixture)
apply:   patch applied
tests:   passed

$ forge eval
agent:      offline
tasks:      4
solved:     4
solve-rate: 100.0%
failure modes:
  no_localization  0
  bad_patch        0
  tests_failed     0
  timeout          0
```

## Runs with no API key, honestly

Like the rest of the initiative, Forge runs and is fully tested with no key. The deterministic path is an
`OfflineAgent`: an honest **fixture-replay** test double that replays each mini-bench task's committed gold
patch. It exercises the entire harness — localization, patch application, the sandbox gate, and the eval —
so the whole thing is reproducible offline.

It is honest about what it is. It does not measure a model's ability to *find* a fix; it replays a
known-correct one. A real solve-rate needs a real provider behind the `LLMClient`. Swap it in with a key:

```bash
export ANTHROPIC_API_KEY=...      # or OPENAI_API_KEY
export FORGE_LLM_PROVIDER=anthropic
forge eval
```

The provider is chosen by `FORGE_LLM_PROVIDER` (`anthropic` | `openai` | `offline`; default `auto` picks a
key if present, else offline). No vendor SDK is imported outside its adapter, so the harness stays
vendor-neutral and the eval scores whichever agent runs.

## The verification gate has teeth

A gate that rubber-stamps is worse than none. A dedicated test feeds a patch that **applies cleanly but
leaves the bug in place** and asserts the gate reports *not solved*:

```python
# tests/test_sandbox.py
def test_gate_rejects_knowingly_wrong_patch(mean_task, make_diff):
    # only edits the docstring; the off-by-one bug survives
    ...
    assert not verdict.passed        # the tests, not the model, decide
```

## Architecture — the engineering core, then the AI

| Piece | Module | Job |
|-------|--------|-----|
| Task adapter | `forge/tasks/` | Load a bug (repo snapshot + failing test) behind one `Task` interface. |
| Workspace | `forge/workspace/` | Copy the repo into an isolated, disposable working directory per attempt. |
| Localization | `forge/localize/` | Rank the source files most likely relevant (keyword baseline; grounds the agent). |
| Agent | `forge/agent/` | The loop + provider-agnostic `LLMClient` (Anthropic / OpenAI) + the offline double. |
| Tools | `forge/tools/` | A small, explicit surface: read-only (`read_file`, `search`) vs mutating (`apply_patch`). |
| Sandbox | `forge/sandbox/` | The verification gate: run the tests in a subprocess with a timeout. |
| Solve loop | `forge/solve.py` | Tie it together and classify the outcome. |
| Eval | `forge/evaluation.py` | Solve-rate + failure taxonomy, versioned under `eval/results/`. |

The AI portion is small on purpose, and it is **evaluated**, not trusted. Removing the LLM still leaves a
real system: task loading, isolated workspaces, retrieval, patch application, a sandbox verifier, and an
eval harness.

## The eval is a first-class deliverable

`forge eval` runs the whole task set and reports **solve-rate** plus a **failure-mode breakdown**
(`no_localization` / `bad_patch` / `tests_failed` / `timeout`), saved to `eval/results/latest.json` so the
numbers are versioned and regressions show up in diffs. Classifying *why* each miss happened is the point:
it is the difference between "it broke" and "localization missed the file."

## The mini-bench (clean-room data)

v0.1 ships a small, self-authored benchmark: four tiny Python repos, each with one seeded bug and a test
that fails on the bug and passes once it is fixed. Fast, deterministic, Docker-free, and nothing in it
comes from any real codebase. See [`data/README.md`](data/README.md). A slice of the public
**SWE-bench-lite** benchmark slots in behind the same task adapter in v0.3.

## Roadmap

Forge is built as a ladder; each stage adds one load-bearing idea from modern harness engineering.

- **v0.1 — the verified core loop (shipped).** Localize, patch, sandbox-verify, eval with a failure
  taxonomy. The verification-first spine.
- **v0.2 — guardrails.** A policy layer (protected paths, change-scope limits, required checks) and a
  human-approval gate. Safe at scale.
- **v0.3 — reliability + a real benchmark.** SWE-bench-lite in Docker sandboxes, regression tracking, and a
  calibrated LLM-as-judge for patch quality.
- **v0.4 — orchestration.** Planner / editor / critic personas and bounded self-repair.
- **v0.5 — observability.** Structured run trajectories, a trace critic, and cost caps.

## Development

```bash
python -m pytest -q        # 30 tests, offline, ~30s (some spawn a real pytest subprocess)
ruff check forge eval tests
black --check forge eval tests
```

## License

MIT. See [LICENSE](LICENSE).
