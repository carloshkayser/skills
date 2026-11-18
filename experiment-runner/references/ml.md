# Machine learning experiments

Extra checks on top of the core protocol.

- **Seeds**: record every seed (Python, NumPy, framework, data-loader workers, data split). Pass them with `--seed` (for example `--seed "global=42 split=7"`). Note whether deterministic mode was enabled (`torch.use_deterministic_algorithms`, `cudnn.deterministic`, `PYTHONHASHSEED`); GPU runs are often not bit-reproducible even with seeds, so say so in the interpretation.
- **Multiple seeds**: claim an improvement only with several seeds. Report mean and spread, and use one run per seed (or one command that writes every seed's metrics to `$EXP_RUN_DIR`).
- **Data**: record dataset name and version, size, and a content hash or the DVC/LFS pointer. Record how train/validation/test splits were produced (seed, file list hash). Never overwrite a split between runs that will be compared.
- **Evaluation discipline**: select hyperparameters, checkpoints, and early stopping on the validation set only. Touch the test set once per final claim, and write that down.
- **Config**: pass the config file with `--config` so its hash and a copy are logged. Prefer configs under version control and committed before `start`; avoid values that exist only on the command line, or they must appear in the recorded command.
- **Checkpoints and large outputs**: keep them out of git, save them under `$EXP_RUN_DIR` or a gitignored directory, and record path, size, and hash via `--artifact` (large files are hash-only).
- **Experiment trackers (W&B, MLflow, TensorBoard)**: put the tracker run URL/ID in `--observed` or `--next`. The tracker complements the log; it does not replace the commit hash and command.
- **Hardware**: the snapshot captures GPU name, driver, and memory. Also note the number of devices, precision (fp32/bf16), and batch size when they affect results.
- **Failure modes worth logging as facts**: divergence/NaN loss, OOM, early stop epoch, wall-clock time, and the step at which it happened.
