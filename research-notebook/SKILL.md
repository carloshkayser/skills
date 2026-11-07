---
name: research-notebook
version: 1.0.0
description: >-
  Preserve investigation evidence across agent sessions. Use when debugging, researching root causes, testing hypotheses, comparing solutions, or running experiments. Consulte o arquivo HYPOTHESES.md antes de novas tentativas de depuração, pesquisa ou experimentação; registre hipóteses, testes e resultados para evitar repetição de abordagens já avaliadas.
---

# Research Notebook

Maintain a durable, evidence-based research history shared by future agents. The notebook is **not** a to-do list or an unverified collection of ideas: it connects hypotheses, concrete attempts, observations, and decisions.

## Canonical file

- Use `<repository-root>/HYPOTHESES.md` as the **single source of truth**. Determine the root with `git rev-parse --show-toplevel` when available; otherwise use the project's working root.
- **At the beginning of an investigation**, read the notebook's index and the full records relevant to the current problem. Search by keywords, affected component, error signature, approach, and IDs.
- If the file does not exist, create it from `assets/HYPOTHESES.template.md`. Never overwrite an existing notebook. If the file already uses another structure, preserve its content and integrate these principles rather than replacing it.
- Keep the notebook in the repository so it survives agent/session changes and can be tracked by version control. Do not rely on conversation memory or local scratch files for the canonical record.

## Mandatory workflow

### 1. Consult before testing

Before changing code, running a diagnostic experiment, or repeating a candidate fix:

1. Identify the question, target component, expected outcome, relevant environment, and intended method.
2. Check the index and related hypothesis records in `HYPOTHESES.md`.
3. Compare the new attempt with existing ones by **hypothesis, method, parameters, baseline/code state, environment, and success criterion**.
4. If an equivalent attempt already has a trustworthy result under comparable conditions, **do not repeat it**. Reuse its evidence and choose a genuinely new approach, unless a retest is justified.
5. Retesting is allowed when an identified condition materially changed (code, dependency, configuration, data, hardware, assumptions, or measurement method), prior evidence was unreliable, or reproducibility is explicitly required. Explain the difference and link the previous attempt ID **before** running it.
6. A result marked *inconclusive* does not establish failure. Prefer resolving the missing evidence before repeating the same experiment unchanged.

### 2. Register the hypothesis before execution

- Find an existing hypothesis ID (`H-001`, `H-002`, ...) if the claim is the same. Otherwise add a new entry and index row with a unique sequential ID.
- Specify a falsifiable claim, scope, rationale, predicted observation, and a measurable success/failure criterion.
- For every distinct experiment create an attempt (`T-001`, `T-002`, ... **within its hypothesis**) **before execution**. Mark it `in-progress`, including intended steps, relevant configuration/baseline, and why it is not a redundant repeat.
- If interrupted, leave the entry so the next agent knows the attempt was started but not completed; never assume it succeeded.

### 3. Record what actually happened

Immediately after running a test, update its attempt with:

- Date/time (ISO 8601 with timezone if available), agent/session identifier when available, relevant commit/branch, and other conditions needed to interpret the result.
- Actual commands, code/config changes, inputs, and measurement procedure (or references to them).
- **Observed** output/measurements, including failures, error codes, logs, and artifact paths or links.
- Comparison against the predeclared criterion; distinguish observed facts from interpretation.
- One attempt status: `completed`, `inconclusive`, `blocked`, or `interrupted`.
- A concise next step: what not to try again, what new approach is justified, or what evidence is missing.

Then update the hypothesis status and the notebook index. Use the hypothesis statuses:

| Status | Meaning |
|---|---|
| `proposed` | Not tested yet. |
| `investigating` | At least one attempt is in progress, or evidence collection continues. |
| `supported` | Evidence favors the claim **under recorded conditions**; not universal proof. |
| `refuted` | Evidence contradicts the claim **under recorded conditions**; not a universal ban. |
| `inconclusive` | Available evidence cannot resolve the claim. |
| `superseded` | Replaced by a newer, linked hypothesis or materially changed context. |

**Do not** label a hypothesis `refuted` merely because a test failed to run. A blocked or flawed test is `blocked`/`inconclusive` and needs an appropriate hypothesis status.

### 4. Preserve provenance and history

- Never erase failed attempts just because they did not work. Append a correction or mark a record `superseded`, linking the replacement.
- Never fabricate commands, metrics, dates, IDs, agent identities, results, or evidence. Use `not recorded` for missing information.
- Separate observation from inference. Cite repo paths, test commands, logs, diffs, issue links, or commit IDs where possible.
- Avoid secrets, API keys, tokens, private data, and excessively long logs. Prefer short excerpts plus safe artifact references.
- Re-read the notebook before saving if another agent may have changed it; merge entries and avoid overwriting concurrent edits.
- Keep summaries short enough to scan. Put details in the hypothesis/attempt record, not only in the index.

### 5. Hand off to future agents

Before concluding the investigation:

1. Ensure each experiment performed has a documented outcome, including unsuccessful experiments.
2. Ensure the index matches the detailed records.
3. In the final user-facing summary, cite the affected IDs (`H-...` / `T-...`), the strongest findings, approaches already tried, and the next untested direction.

## Record format

Use the heading and field structure in `assets/HYPOTHESES.template.md`. Each hypothesis gets one `H-...` section, containing zero or more `T-...` attempts. Prefer editing the existing hypothesis over creating duplicates for the same claim. Preserve historical records when formatting evolves.

### Decision example

If `H-003 / T-002` already tested a cache flush on the same version/configuration and it did not fix the observed symptom, **do not rerun the same cache flush**. Instead, link `H-003 / T-002` in a new hypothesis or attempt and test a different cause. If the cache implementation changed in a new commit, a retest may be useful: record the changed commit and the reason for reconsidering the result first.
