---
name: experiment-runner
version: 1.0.0
description: >-
  Run experiments reproducibly. Use whenever you are about to execute an experiment, training run, benchmark, simulation, performance test, or any measurement whose result will be compared or reported: commit the code first, record the commit hash, command, environment, and results in an append-only experiment log, and link every run to its hypothesis in HYPOTHESES.md. Never run an experiment on uncommitted code.
---

# Experiment Runner

Every experiment run must be traceable to **one exact commit** and **one log record**. Anyone must be able to run `git checkout <hash>`, execute the recorded command, and reproduce the setup. This skill covers *how* a run is executed and logged. The `research-notebook` skill covers *why* (hypotheses, attempts, decisions); the two are linked by `H-xxx / T-xxx` IDs.

## Iron rules

1. **Never run an experiment on uncommitted code.** The working tree must be clean at start, and `HEAD` must not move between `start` and `run`.
2. **Never decide what to do with uncommitted changes yourself.** Ask the user (see step 3). Approval for one run does not carry over to the next.
3. **Log before and after.** The record exists as `in-progress` before the command executes, and is closed with facts after.
4. **Append-only.** Never delete, rewrite, or hide runs, including failed, interrupted, and inconclusive ones.
5. **Observation and interpretation are kept separate.** Never fabricate commands, metrics, hashes, dates, or results; write `not recorded` when unknown.
6. **No secrets in the log.** Do not record tokens, keys, or private data; environment variables are recorded only when explicitly allowlisted with `--env`.

## Layout

```text
experiments/
├── LOG.md                    # index: one row per run
└── runs/<run-id>/            # run-id = R-YYYYMMDD-NNN
    ├── RUN.md                # full record (metadata, command, results, interpretation)
    ├── env.txt               # environment snapshot (platform, pip freeze, GPU, lockfile hashes)
    ├── stdout.log / stderr.log
    └── artifacts/            # small outputs and configs (<= 1 MiB); larger ones are hash-only
```

`experiments/` is excluded from the clean-tree check, so writing the log never makes the tree dirty. Do **not** put it in `.gitignore`: the log is committed (step 7). If raw logs get large, ignore `experiments/runs/*/stdout.log` selectively.

## Tool: `scripts/exp.py`

Standard-library Python, no prompts. It never commits, stashes, or discards; you do those after the user decides. Resolve its path relative to this skill's directory.

| Command | Purpose | Notable exit codes |
|---|---|---|
| `exp.py check [--json]` | Read-only git state | `0` clean, `10` dirty, `11` no repo, `12` detached HEAD, `13` submodule out of sync |
| `exp.py start --title T --criterion C (--attempt H-001/T-001 \| --exploratory) [--baseline R-…] [--dirty-action …] [--env VAR]` | Register run as `in-progress`; captures commit, branch, environment | `10`…`13` as above, `22` attempt not registered |
| `exp.py run <run-id> [--seed S] [--config F] [--metrics M.json] [--artifact P]… -- <command…>` | Execute exactly one command and capture it | `20` HEAD moved, `21` run already executed |
| `exp.py finish <run-id> --status … [--criterion …] [--observed …] [--interpretation …] [--next …] [--key-result …]` | Close the run, tag the commit `exp-<run-id>` | |
| `exp.py list [--status S] [--attempt H-001/T-001] [--commit HASH]` / `exp.py show <run-id>` | Query the log | |

`run` exports `EXP_RUN_ID`, `EXP_RUN_DIR`, and `EXP_COMMIT` to the experiment. **Make the experiment write its outputs into `$EXP_RUN_DIR`** (or a gitignored directory); outputs written to tracked or untracked paths elsewhere make the tree dirty and block the next run.

If the script cannot be used (no Python, unusual setup), follow the same protocol by hand and fill `assets/RUN.template.md` and `assets/LOG.template.md` manually.

## Workflow

### 0. Once per series: choose the branch

At the start of a series of experiments, **ask the user** which branch to use, suggesting a dedicated `exp/<short-slug>` branch (for example `exp/lr-sweep`). Offer the current branch as an alternative. Do not ask again for each run in the series; ask again only if the series changes or the branch changes. Never force-push, rebase, or rewrite history on experiment branches.

Activate the environment the experiment will use (venv, conda, container) **before** `start`; the snapshot records the interpreter found on `PATH`.

### 1. Consult before running

Read `HYPOTHESES.md` (see `research-notebook`) and `experiments/LOG.md` (`exp.py list`). If an equivalent run (same hypothesis, method, parameters, commit or equivalent code state) already has a trustworthy result, do not repeat it unless something material changed (code, data, dependencies, hardware, measurement method) or reproducibility is the goal. State what differs and link the earlier run as `--baseline`.

### 2. Register the attempt

Using `research-notebook`, make sure the hypothesis (`H-xxx`) and the attempt (`T-xxx`) exist and are `in-progress`, with a falsifiable claim and a **success criterion written before any result is seen**. `exp.py start` refuses an attempt it cannot find in `HYPOTHESES.md`. Use `--exploratory` only for genuinely unplanned exploration; it is flagged in the log, and the findings should be turned into a hypothesis afterwards.

### 3. Get a clean tree

Run `exp.py check`. If the exit code is `10` (dirty), **stop and ask the user** (use `AskUserQuestion` when available). Show `git status --short` and `git diff --stat`, then offer:

| Choice | Action |
|---|---|
| **Commit** | Stage only the files the user approves; commit with a message like `exp: <short description>` (user may edit it). |
| **Move (stash)** | `git stash push -u -m "pre-exp <slug>"`; remember the stash ref for `--stash-ref`. |
| **Discard** | Destructive. Only after the user explicitly confirms the list of files that will be lost: `git restore` / `git clean`. |
| **Cancel** | Do not run anything. |

Rules: never choose for the user, never reuse an earlier answer, never discard without explicit confirmation. In non-interactive contexts (cron, batch, no user to ask), **abort with an error** instead of deciding. If `check` reports `11`, `12`, or `13`, report it and ask how to proceed (init repo, switch to a branch, sync submodules). After acting, run `exp.py check` again; it must exit `0`. Pass what the user chose to `start` with `--dirty-action committed|stashed|discarded` (and `--stash-ref`).

Changes that belong to the experiment (new parameters, instrumentation) must be committed **before** `start`, so the recorded hash contains exactly the code that runs. Commit large datasets and checkpoints with the project's usual mechanism (Git LFS, DVC), or leave them out and let the log record their hash.

### 4. Start

```bash
exp.py start --title "<what is being tested>" --attempt H-003/T-002 \
  --criterion "<measurable success criterion>" [--baseline R-20261118-001] \
  [--dirty-action committed] [--env CUDA_VISIBLE_DEVICES]
```

It prints `RUN_ID` and the commit. The record now exists as `in-progress`; if the run is interrupted, that is how the next agent knows it was started but never completed.

### 5. Run

```bash
exp.py run R-20261118-002 --seed 42 --config configs/exp.yaml --metrics "$EXP_RUN_DIR/metrics.json" -- python train.py --config configs/exp.yaml
```

One run is exactly one command. For several configurations or seeds, create one run per configuration (or have a single command execute the sweep and write all results to `$EXP_RUN_DIR`). The command's exit code, duration, and stdout/stderr are captured. A non-zero exit code is a recorded fact, not an error of the tool.

Do not edit tracked files while a run is in progress. If `run` fails with `20` (HEAD moved) or `10`, start a new run.

### 6. Finish

```bash
exp.py finish R-20261118-002 --status completed --criterion met \
  --observed "val acc 0.912 (seed 42); training diverged after epoch 8 in 1 of 3 runs" \
  --interpretation "Likely caused by ..." --next "Repeat with 3 seeds; do not retry lr=0.1" \
  --key-result "val_acc=0.912"
```

- `--status`: `completed` (the command ran to a result), `inconclusive`, `blocked`, or `interrupted`. These match the research-notebook attempt statuses. A crash is `blocked` or `inconclusive` unless the failure itself is the finding; never record a failed or unreliable measurement as evidence against a hypothesis.
- `--criterion`: `met`, `not-met`, `unclear`, or `n/a`, judged against the criterion declared in step 2, not a new one.
- `--observed` holds facts only (numbers, errors, paths); `--interpretation` holds inference.

`finish` also creates the tag `exp-<run-id>` on the recorded commit so it survives branch cleanup.

### 7. Commit the log

The script prints the exact command. Commit the log **separately** from the code, so the experiment commit stays exactly the code that ran:

```bash
git add experiments && git commit -m "log: R-20261118-002"
```

### 8. Update the research notebook

Update `T-xxx` in `HYPOTHESES.md` with the run ID, commit hash, and result; update the hypothesis status and the notebook index as `research-notebook` describes. In the final summary to the user, cite run IDs, commit hashes, what was learned, and the next untested direction.

## Scientific hygiene

- Change **one factor at a time** between comparable runs; always compare against a named baseline run.
- Fix the success criterion and the metric before looking at results. Do not tune on the test or evaluation set used for the final claim.
- A single run, seed, or measurement is an anecdote. Prefer several seeds/repetitions and report spread before claiming an improvement; say so explicitly when only one was run.
- Record negative and failed results with the same care as successes.
- Keep a `supported` hypothesis scoped to the recorded conditions.

## Domain notes (load only when relevant)

- Machine learning / training: [`references/ml.md`](references/ml.md)
- Benchmarks, performance, and simulations: [`references/benchmarks-simulations.md`](references/benchmarks-simulations.md)
- Software experiments (A/B of code variants, regressions, flaky tests): [`references/software.md`](references/software.md)
