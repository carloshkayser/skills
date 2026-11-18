# Benchmarks, performance, and simulations

Extra checks on top of the core protocol.

- **Warm-up and repetitions**: discard warm-up iterations and repeat enough times to see variance. Record the repetition count, and report median and spread (IQR or min/max) rather than a single mean.
- **Noise control**: record CPU model and core count, frequency governor or power mode, background load, thermal state, and whether the machine is shared. Run baseline and candidate **interleaved or back to back on the same machine**, never on different hosts or days.
- **Pinned inputs**: use fixed inputs, workload sizes, and data files; record their hashes. Use the same build flags and compiler/runtime versions (the environment snapshot captures the interpreter and lockfiles; add compiler, JVM, and build flags to `--observed` or the config).
- **Build state**: benchmark the committed code in the intended build configuration (release, optimizations on). Record the exact build command as part of the run command or a script committed beforehand.
- **Simulations**: record RNG seeds, time step, domain/grid size, solver tolerances, and the version of any external model or input data. For stochastic simulations, treat one seed as one sample and run multiple seeds.
- **Parameter sweeps**: either create one run per configuration, or run one sweep command that writes every configuration's result to `$EXP_RUN_DIR`. Keep a table of configurations and results in `--observed`, and never report only the best configuration without the rest.
- **Units and metrics**: state units (ms, ops/s, MB) and what is measured (latency percentile, throughput, memory peak). Declare the metric and the threshold in the success criterion before running.
- **Claims**: a difference smaller than the measured run-to-run variation is `unclear`, not `met`.
