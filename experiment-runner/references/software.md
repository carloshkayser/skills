# Software experiments

A/B comparisons of code variants, regression hunting, flaky-test reproduction, and similar.

- **One variant = one commit.** Put each variant on its own commit (or branch) and run the identical command against each, so every run maps to exactly one hash. Do not toggle behavior with uncommitted edits.
- **Feature flags and config**: if a flag selects the variant, commit the flag value or pass it via `--config`/the recorded command, so the log shows which variant ran.
- **Regression hunting**: log each commit probed as its own run, including the ones that pass. Compare against a named baseline run, and record the exact test command and the failure signature.
- **Flaky tests**: run the test many times (use a loop inside one command) and record the pass/fail count in `--observed`, for example `37/200 failed`. A single pass or failure is not evidence.
- **Dependencies**: the environment snapshot records `pip freeze` and lockfile hashes. For other ecosystems (npm, cargo, go), make sure the lockfile is committed and note package manager and runtime versions in the run record.
- **External state**: record anything the result depends on that is outside git: database contents, service versions, network conditions, feature toggles on a remote service, time of day. If it cannot be pinned, say so in the interpretation.
- **Reproducing a bug report**: first run the reported steps on the reported commit as a baseline run; only then run candidate fixes, each on its own commit.
