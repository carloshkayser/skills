# Experiment Runner Skill

Skill for running experiments reproducibly: code is committed before every run, the commit hash, command, environment, and results go into an append-only log, and each run is linked to its hypothesis in `HYPOTHESES.md` (see the [`research-notebook`](../research-notebook/) skill).

- **Version**: `1.0.0`
- **Specification**: Agent Skills compatible
- **Requirements**: `git`, Python 3.8+ (standard library only) for `scripts/exp.py`

See [`SKILL.md`](./SKILL.md) for the full protocol and agent workflow.

## Install

```bash
npx skills add https://github.com/carloshkayser/skills --skill experiment-runner
```

## Files included

```text
experiment-runner/
├── README.md
├── SKILL.md
├── scripts/
│   └── exp.py                       # check / start / run / finish / list / show
├── assets/
│   ├── AGENTS.snippet.md
│   ├── LOG.template.md              # experiments/LOG.md index
│   └── RUN.template.md              # experiments/runs/<run-id>/RUN.md record
└── references/
    ├── ml.md
    ├── benchmarks-simulations.md
    └── software.md
```

## Installation and use

1. Install the skill in the agent's skills directory (for example `~/.agents/skills/experiment-runner/` or `.agents/skills/experiment-runner/` in the project). Installing `research-notebook` alongside it is recommended.
2. Optionally add [`assets/AGENTS.snippet.md`](./assets/AGENTS.snippet.md) to the repository's `AGENTS.md`.
3. When an experiment is about to run, the agent follows `SKILL.md`: asks which branch to use (suggesting `exp/<slug>`), requires a clean tree (asking you what to do with pending changes), registers the run, executes the command through `exp.py run`, and closes the record.

## Quick example

```bash
exp.py check                                   # exit 10 => dirty: the agent asks you what to do
exp.py start --title "lr 0.01 vs 0.1" --attempt H-003/T-002 --criterion "val_acc >= 0.90"
exp.py run R-20261118-001 --seed 42 -- python train.py     # writes to $EXP_RUN_DIR
exp.py finish R-20261118-001 --status completed --criterion met --observed "val_acc 0.912" --key-result "val_acc=0.912"
git add experiments && git commit -m "log: R-20261118-001"
```

`exp.py` never commits, stashes, or discards anything and never prompts; those decisions belong to you and are executed by the agent.
