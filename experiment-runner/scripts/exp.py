#!/usr/bin/env python3
"""exp.py - reproducible experiment runner (companion to the experiment-runner skill).

Deterministic half of the protocol. It NEVER commits, stashes, or discards anything and
never prompts: the agent asks the user and performs those git actions itself.

Subcommands:
  check   inspect git state (read-only)            exit 0 clean, 10 dirty, 11 no repo,
                                                   12 detached HEAD, 13 submodule out of sync
  start   register a run as in-progress            requires a clean tree
  run     execute one command and capture it       requires clean tree and unmoved HEAD
                                                   (exit 20 HEAD moved, 21 already ran)
  finish  close the run, tag the commit
  list    list runs from the index
  show    print one run record

Python 3.8+, standard library only.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

E_OK, E_DIRTY, E_NOREPO, E_DETACHED, E_SUBMODULE = 0, 10, 11, 12, 13
E_HEAD_MOVED, E_ALREADY_RAN, E_NO_ATTEMPT, E_USAGE, E_NOT_FOUND = 20, 21, 22, 23, 24

RUN_STATUSES = ("completed", "inconclusive", "blocked", "interrupted")
CRITERION_RESULTS = ("met", "not-met", "unclear", "n/a")
ATTEMPT_RE = re.compile(r"^(H-\d+)\s*/\s*(T-\d+)$")
LOCKFILES = ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.txt", "environment.yml",
             "conda-lock.yml", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
             "Cargo.lock", "go.sum", "Gemfile.lock", "composer.lock")
ASSETS = Path(__file__).resolve().parent.parent / "assets"


class ExpError(Exception):
    def __init__(self, message, code=E_USAGE):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------- helpers
def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sh(args, cwd=None, check=False):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise ExpError("command failed: %s\n%s" % (shlex.join(args), r.stderr.strip()))
    return r


def one_line(s):
    return re.sub(r"\s+", " ", str(s)).strip() or "not recorded"


def cell(s):
    return one_line(s).replace("|", "\\|")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_root():
    r = sh(["git", "rev-parse", "--show-toplevel"])
    if r.returncode != 0:
        raise ExpError("not inside a git repository", E_NOREPO)
    return Path(r.stdout.strip())


class Ctx:
    def __init__(self, exp_dir):
        self.root = repo_root()
        self.exp_rel = exp_dir.strip("/") or "experiments"
        self.exp = self.root / self.exp_rel
        self.log = self.exp / "LOG.md"
        self.runs = self.exp / "runs"

    def run_dir(self, run_id):
        d = self.runs / run_id
        if not (d / "RUN.md").is_file():
            raise ExpError("unknown run: %s" % run_id, E_NOT_FOUND)
        return d


def git_state(ctx):
    """Read-only snapshot of the repository state."""
    head = sh(["git", "rev-parse", "HEAD"], cwd=ctx.root)
    branch = sh(["git", "symbolic-ref", "--short", "-q", "HEAD"], cwd=ctx.root)
    subject = sh(["git", "log", "-1", "--format=%s"], cwd=ctx.root)
    status = sh(["git", "status", "--porcelain=v1", "-uall", "--ignore-submodules=none",
                 "--", ".", ":(exclude)%s" % ctx.exp_rel], cwd=ctx.root)
    dirty = [l for l in status.stdout.splitlines() if l.strip()]
    stashes = [l for l in sh(["git", "stash", "list"], cwd=ctx.root).stdout.splitlines() if l]
    subs = [l for l in sh(["git", "submodule", "status"], cwd=ctx.root).stdout.splitlines()
            if l[:1] in "+-U"]
    br = branch.stdout.strip() if branch.returncode == 0 else None
    if br is None:
        state, code = "detached-head", E_DETACHED
    elif dirty:
        state, code = "dirty", E_DIRTY
    elif subs:
        state, code = "submodule-out-of-sync", E_SUBMODULE
    else:
        state, code = "clean", E_OK
    return {"state": state, "exit": code, "branch": br, "head": head.stdout.strip(),
            "head_subject": subject.stdout.strip(), "on_exp_branch": bool(br and br.startswith("exp/")),
            "dirty_files": dirty, "stashes": stashes, "submodule_issues": subs,
            "experiments_dir": ctx.exp_rel}


def require_clean(ctx):
    st = git_state(ctx)
    if st["state"] != "clean":
        raise ExpError("working tree is not clean (%s). Run `exp.py check`, ask the user what to do "
                       "(commit / stash / discard / cancel) and retry." % st["state"], st["exit"])
    return st


# --------------------------------------------------------------- markdown record editing
def get_field(text, key):
    m = re.search(r"^- \*\*%s\*\*: (.*)$" % re.escape(key), text, re.M)
    return m.group(1) if m else None


def set_field(text, key, value):
    pat = re.compile(r"^(- \*\*%s\*\*: ).*$" % re.escape(key), re.M)
    if not pat.search(text):
        raise ExpError("field %r missing in RUN.md" % key)
    return pat.sub(lambda m: m.group(1) + one_line(value), text, count=1)


def get_section(text, heading):
    m = re.search(r"^## %s\n(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    return m.group(1).strip("\n") if m else ""


def set_section(text, heading, body):
    pat = re.compile(r"(^## %s\n)(.*?)(?=^## |\Z)" % re.escape(heading), re.M | re.S)
    if not pat.search(text):
        raise ExpError("section %r missing in RUN.md" % heading)
    return pat.sub(lambda m: m.group(1) + "\n" + body.strip("\n") + "\n\n", text, count=1)


def load_template(name, **values):
    p = ASSETS / name
    if not p.is_file():
        raise ExpError("missing template: %s" % p)
    text = p.read_text()
    for k, v in values.items():
        text = text.replace("{{%s}}" % k, str(v))
    return text


def split_row(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def ensure_log(ctx):
    ctx.exp.mkdir(parents=True, exist_ok=True)
    if not ctx.log.exists():
        ctx.log.write_text(load_template("LOG.template.md"))


def update_log_row(ctx, run_id, **cols):
    header = ["Run", "Date", "Commit", "Attempt", "Title", "Status", "Criterion", "Key result"]
    lines = ctx.log.read_text().splitlines()
    for i, line in enumerate(lines):
        cells = split_row(line) if line.startswith("|") else []
        if cells and cells[0] == run_id:
            for key, val in cols.items():
                cells[header.index(key)] = cell(val)
            lines[i] = "| " + " | ".join(cells) + " |"
            ctx.log.write_text("\n".join(lines) + "\n")
            return
    raise ExpError("run %s not found in %s" % (run_id, ctx.log))


# ------------------------------------------------------------------- environment capture
def env_snapshot(ctx, extra_env):
    out, summary = [], {}

    def section(title, body):
        out.append("### %s\n%s\n" % (title, body.strip() or "(empty)"))

    section("platform", "%s\n%s" % (platform.platform(), platform.machine()))
    py, ver = sys.executable, None
    for cand in ("python3", "python"):  # first interpreter on PATH that actually works (pyenv shims may not)
        path = shutil.which(cand)
        if path:
            r = sh([path, "--version"])
            if r.returncode == 0:
                py, ver = path, r
                break
    ver = ver or sh([py, "--version"])
    summary["python"] = (ver.stdout or ver.stderr).strip() + " (%s)" % py
    section("python", summary["python"])
    pip = sh([py, "-m", "pip", "freeze"])
    section("pip freeze", pip.stdout if pip.returncode == 0 else "unavailable")
    if shutil.which("nvidia-smi"):
        g = sh(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"])
        summary["gpu"] = g.stdout.strip().replace("\n", "; ") or "none"
        section("gpu", g.stdout)
    else:
        summary["gpu"] = "none detected"
    locks = []
    for name in LOCKFILES:
        p = ctx.root / name
        if p.is_file():
            locks.append("%s  sha256:%s" % (name, sha256(p)[:16]))
    section("lockfiles", "\n".join(locks) or "none found")
    summary["lockfiles"] = ", ".join(l.split("  ")[0] for l in locks) or "none found"
    sub = sh(["git", "submodule", "status"], cwd=ctx.root).stdout
    if sub.strip():
        section("submodules", sub)
    if extra_env:
        section("requested environment variables",
                "\n".join("%s=%s" % (v, os.environ.get(v, "<unset>")) for v in extra_env))
    return "\n".join(out), summary


# ------------------------------------------------------------------------------ artifacts
def record_artifacts(paths, run_dir, max_copy):
    rows = []
    adir = run_dir / "artifacts"
    for p in paths:
        pth = Path(p)
        if not pth.is_file():
            rows.append("| `%s` | - | - | not a file (record files individually) |" % cell(p))
            continue
        size = pth.stat().st_size
        digest = sha256(pth)
        if size <= max_copy:
            adir.mkdir(exist_ok=True)
            name, n = pth.name, 1
            while (adir / name).exists():
                name, n = "%d_%s" % (n, pth.name), n + 1
            shutil.copy2(pth, adir / name)
            copy = "artifacts/%s" % name
        else:
            copy = "not copied (> %d bytes)" % max_copy
        rows.append("| `%s` | %d | `%s` | %s |" % (cell(p), size, digest, copy))
    return rows


def flatten(d, prefix=""):
    for k, v in d.items():
        key = "%s%s" % (prefix, k)
        if isinstance(v, dict):
            yield from flatten(v, key + ".")
        else:
            yield key, v


def metrics_table(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return "_metrics file %s could not be read: %s_" % (path, e)
    if not isinstance(data, dict):
        return "_metrics file %s is not a JSON object_" % path
    rows = ["| Metric | Value |", "|---|---|"]
    rows += ["| %s | %s |" % (cell(k), cell(json.dumps(v) if isinstance(v, (list, tuple)) else v))
             for k, v in flatten(data)]
    return "\n".join(rows)


# ---------------------------------------------------------------------------- subcommands
def next_run_id(ctx):
    day = dt.date.today().strftime("%Y%m%d")
    existing = [p.name for p in ctx.runs.glob("R-%s-*" % day)] if ctx.runs.exists() else []
    n = max([int(x.rsplit("-", 1)[1]) for x in existing] + [0]) + 1
    return "R-%s-%03d" % (day, n)


def cmd_check(ctx, a):
    st = git_state(ctx)
    if a.json:
        print(json.dumps(st, indent=2))
    else:
        print("STATE: %s (exit %d)" % (st["state"], st["exit"]))
        print("branch: %s   head: %s %s" % (st["branch"], st["head"][:12], st["head_subject"]))
        print("on exp/* branch: %s" % ("yes" if st["on_exp_branch"] else "no"))
        print("stashes: %d" % len(st["stashes"]))
        if st["dirty_files"]:
            print("uncommitted changes (%d, excluding %s/):" % (len(st["dirty_files"]), st["experiments_dir"]))
            print("\n".join("  " + l for l in st["dirty_files"]))
        if st["submodule_issues"]:
            print("submodules out of sync:")
            print("\n".join("  " + l for l in st["submodule_issues"]))
    return st["exit"]


def check_attempt(ctx, a):
    if a.exploratory:
        return "exploratory (no registered hypothesis)"
    if not a.attempt:
        raise ExpError("--attempt H-xxx/T-xxx is required (or --exploratory)", E_NO_ATTEMPT)
    m = ATTEMPT_RE.match(a.attempt.strip())
    if not m:
        raise ExpError("--attempt must look like H-003/T-002", E_NO_ATTEMPT)
    h, t = m.groups()
    nb = ctx.root / "HYPOTHESES.md"
    if not nb.is_file():
        raise ExpError("HYPOTHESES.md not found; register the attempt with the research-notebook "
                       "skill first (or use --exploratory)", E_NO_ATTEMPT)
    text = nb.read_text()
    if h not in text or t not in text:
        raise ExpError("%s / %s not found in HYPOTHESES.md; register the attempt BEFORE running" % (h, t),
                       E_NO_ATTEMPT)
    return "%s / %s" % (h, t)


def cmd_start(ctx, a):
    st = require_clean(ctx)
    attempt = check_attempt(ctx, a)
    if a.baseline:
        ctx.run_dir(a.baseline)
    ensure_log(ctx)
    run_id = next_run_id(ctx)
    run_dir = ctx.runs / run_id
    run_dir.mkdir(parents=True)
    env_text, env = env_snapshot(ctx, a.env)
    (run_dir / "env.txt").write_text(env_text)
    dirty = a.dirty_action + (" (%s)" % a.stash_ref if a.stash_ref else "")
    text = load_template(
        "RUN.template.md", run_id=run_id, title=one_line(a.title), started=now(), attempt=attempt,
        baseline=a.baseline or "none", commit=st["head"], branch=st["branch"], dirty_action=dirty,
        criterion=one_line(a.criterion), host=platform.node(), platform=platform.platform(),
        python=env["python"], gpu=env["gpu"], lockfiles=env["lockfiles"])
    (run_dir / "RUN.md").write_text(text)
    with open(ctx.log, "a") as f:
        f.write("| %s | %s | `%s` | %s | %s | in-progress | pending | not recorded |\n" % (
            run_id, dt.date.today().isoformat(), st["head"][:12], cell(attempt), cell(a.title)))
    if not st["on_exp_branch"]:
        print("warning: branch %r is not exp/*; make sure the user chose it deliberately" % st["branch"],
              file=sys.stderr)
    print("RUN_ID=%s\nCOMMIT=%s\nRECORD=%s" % (run_id, st["head"], (run_dir / "RUN.md").relative_to(ctx.root)))
    return E_OK


class Tee(threading.Thread):
    def __init__(self, src, path, sink):
        super().__init__(daemon=True)
        self.src, self.path, self.sink = src, path, sink

    def run(self):
        with open(self.path, "wb") as f:
            for chunk in iter(lambda: self.src.readline(), b""):
                f.write(chunk)
                f.flush()
                self.sink.write(chunk)
                self.sink.flush()


def cmd_run(ctx, a):
    cmd = a.command
    if not cmd:
        raise ExpError("no command given: exp.py run <run-id> -- <command...>")
    run_dir = ctx.run_dir(a.run_id)
    rec = (run_dir / "RUN.md").read_text()
    if get_field(rec, "Status") != "in-progress":
        raise ExpError("run %s is already %s" % (a.run_id, get_field(rec, "Status")), E_ALREADY_RAN)
    if get_field(rec, "Command") not in (None, "not run yet"):
        raise ExpError("run %s already has a command; a run is one command. Start a new run." % a.run_id,
                       E_ALREADY_RAN)
    st = require_clean(ctx)
    if st["head"] != get_field(rec, "Commit"):
        raise ExpError("HEAD moved since `start` (%s -> %s). Start a new run." % (
            get_field(rec, "Commit")[:12], st["head"][:12]), E_HEAD_MOVED)

    config_note = "none"
    if a.config:
        cp = Path(a.config)
        if cp.is_file():
            config_note = "`%s` sha256:%s" % (a.config, sha256(cp))
        else:
            config_note = "`%s` (file not found)" % a.config

    start = time.time()
    started = now()
    code, interrupted = None, False
    try:
        child_env = dict(os.environ, EXP_RUN_ID=a.run_id, EXP_RUN_DIR=str(run_dir),
                         EXP_COMMIT=get_field(rec, "Commit"))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child_env)
    except OSError as e:
        raise ExpError("could not execute %s: %s (nothing was recorded; fix and retry)" % (cmd[0], e))
    threads = [Tee(proc.stdout, run_dir / "stdout.log", sys.stdout.buffer),
               Tee(proc.stderr, run_dir / "stderr.log", sys.stderr.buffer)]
    for t in threads:
        t.start()
    try:
        code = proc.wait()
    except KeyboardInterrupt:
        interrupted = True
        proc.terminate()
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = proc.wait()
    for t in threads:
        t.join()
    duration = time.time() - start

    rec = set_field(rec, "Command", "`%s`" % shlex.join(cmd))
    exec_body = "\n".join([
        "- **Command**: `%s`" % shlex.join(cmd),
        "- **Working directory**: `%s`" % Path.cwd(),
        "- **Seed(s)**: %s" % (a.seed or "not recorded"),
        "- **Config**: %s" % config_note,
        "- **Command started**: %s" % started,
        "- **Exit code**: %s%s" % (code, " (interrupted by user)" if interrupted else ""),
        "- **Duration**: %.2f s" % duration,
        "- **Logs**: `stdout.log`, `stderr.log`",
        "- **Reproduce**: `git checkout %s` then run the command above from the same directory"
        % get_field(rec, "Commit"),
    ])
    rec = set_section(rec, "Execution", exec_body)
    if a.metrics:
        rec = set_section(rec, "Metrics", metrics_table(a.metrics))
    to_record = []  # config + metrics + outputs, each recorded exactly once
    for path in ([a.config] if a.config else []) + ([a.metrics] if a.metrics else []) + a.artifact:
        if path not in to_record:
            to_record.append(path)
    if to_record:
        rec = set_section(rec, "Artifacts", get_section(rec, "Artifacts") + "\n" +
                          "\n".join(record_artifacts(to_record, run_dir, a.max_copy_bytes)))
    (run_dir / "RUN.md").write_text(rec)
    print("\nEXIT_CODE=%s DURATION=%.2fs RUN_ID=%s" % (code, duration, a.run_id), file=sys.stderr)
    return code if a.propagate_exit and code is not None else E_OK


def cmd_finish(ctx, a):
    run_dir = ctx.run_dir(a.run_id)
    rec = (run_dir / "RUN.md").read_text()
    if get_field(rec, "Status") != "in-progress":
        raise ExpError("run %s is already closed (%s); records are append-only. Start a new run or "
                       "add a correction note by hand." % (a.run_id, get_field(rec, "Status")))
    ran = get_field(rec, "Command") not in (None, "not run yet")
    if a.status == "completed" and not ran:
        raise ExpError("cannot mark a run that never executed as completed")
    rec = set_field(rec, "Status", a.status)
    rec = set_field(rec, "Finished", now())
    rec = set_field(rec, "Criterion result", a.criterion)
    rec = set_section(rec, "Observed results", a.observed or "not recorded")
    rec = set_section(rec, "Interpretation", a.interpretation or "not recorded")
    rec = set_section(rec, "Next steps", a.next or "not recorded")
    if a.artifact:
        rec = set_section(rec, "Artifacts", get_section(rec, "Artifacts") + "\n" +
                          "\n".join(record_artifacts(a.artifact, run_dir, a.max_copy_bytes)))
    commit = get_field(rec, "Commit")
    tag = "exp-%s" % a.run_id
    if sh(["git", "rev-parse", "-q", "--verify", "refs/tags/%s" % tag], cwd=ctx.root).returncode != 0:
        r = sh(["git", "tag", tag, commit], cwd=ctx.root)
        tag_note = tag if r.returncode == 0 else "not created (%s)" % r.stderr.strip()
    else:
        tag_note = tag
    rec = set_field(rec, "Tag", tag_note)
    (run_dir / "RUN.md").write_text(rec)
    update_log_row(ctx, a.run_id, Status=a.status, Criterion=a.criterion,
                   **{"Key result": a.key_result or "not recorded"})
    attempt = get_field(rec, "Attempt")
    print("Closed %s as %s (criterion: %s), tag %s" % (a.run_id, a.status, a.criterion, tag_note))
    print("TODO: update %s in HYPOTHESES.md (run %s, commit %s)" % (attempt, a.run_id, commit[:12]))
    print("TODO: commit the log separately:  git add %s && git commit -m \"log: %s\"" % (ctx.exp_rel, a.run_id))
    return E_OK


def cmd_list(ctx, a):
    if not ctx.log.exists():
        print("no runs recorded")
        return E_OK
    for line in ctx.log.read_text().splitlines():
        cells = split_row(line) if line.startswith("| R-") else None
        if not cells:
            continue
        if a.status and cells[5] != a.status:
            continue
        if a.attempt and a.attempt.replace(" ", "") not in cells[3].replace(" ", ""):
            continue
        if a.commit and not cells[2].strip("`").startswith(a.commit):
            continue
        print(line)
    return E_OK


def cmd_show(ctx, a):
    print((ctx.run_dir(a.run_id) / "RUN.md").read_text())
    return E_OK


def build_parser():
    p = argparse.ArgumentParser(prog="exp.py", description=__doc__.split("\n")[0])
    p.add_argument("--exp-dir", default="experiments", help="experiments directory, relative to repo root")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="inspect git state (read-only)")
    c.add_argument("--json", action="store_true")

    s = sub.add_parser("start", help="register a run (requires clean tree)")
    s.add_argument("--title", required=True)
    s.add_argument("--attempt", help="research-notebook attempt, e.g. H-003/T-002")
    s.add_argument("--exploratory", action="store_true", help="no registered hypothesis (flagged in the log)")
    s.add_argument("--criterion", required=True, help="success criterion, declared BEFORE running")
    s.add_argument("--baseline", help="run id to compare against")
    s.add_argument("--dirty-action", default="none",
                   choices=["none", "committed", "stashed", "discarded"],
                   help="what the user chose when the tree was dirty")
    s.add_argument("--stash-ref", help="stash reference when --dirty-action stashed")
    s.add_argument("--env", action="append", default=[], metavar="VAR",
                   help="environment variable to record (explicit allowlist; never dumps the environment)")

    r = sub.add_parser("run", help="execute one command and capture it")
    r.add_argument("run_id")
    r.add_argument("--seed", help="seed(s) used, free text")
    r.add_argument("--config", help="config file to hash and copy")
    r.add_argument("--metrics", help="JSON file written by the experiment; rendered in RUN.md")
    r.add_argument("--artifact", action="append", default=[], help="output file to record (repeatable)")
    r.add_argument("--max-copy-bytes", type=int, default=1 << 20,
                   help="copy artifacts up to this size into the run dir (default 1 MiB)")
    r.add_argument("--propagate-exit", action="store_true", help="exit with the command's exit code")

    f = sub.add_parser("finish", help="close a run")
    f.add_argument("run_id")
    f.add_argument("--status", required=True, choices=RUN_STATUSES)
    f.add_argument("--criterion", default="unclear", choices=CRITERION_RESULTS)
    f.add_argument("--observed", help="observed facts only")
    f.add_argument("--interpretation", help="interpretation, kept separate from the facts")
    f.add_argument("--next", help="next step / what not to retry")
    f.add_argument("--key-result", help="one-line result for the index")
    f.add_argument("--artifact", action="append", default=[])
    f.add_argument("--max-copy-bytes", type=int, default=1 << 20)

    l = sub.add_parser("list", help="list runs")
    l.add_argument("--status")
    l.add_argument("--attempt")
    l.add_argument("--commit", help="commit hash prefix")

    w = sub.add_parser("show", help="print a run record")
    w.add_argument("run_id")
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:  # everything after the first "--" is the experiment command, untouched
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    a = build_parser().parse_args(argv)
    a.command = command
    try:
        ctx = Ctx(a.exp_dir)
        return {"check": cmd_check, "start": cmd_start, "run": cmd_run, "finish": cmd_finish,
                "list": cmd_list, "show": cmd_show}[a.cmd](ctx, a)
    except ExpError as e:
        print("error: %s" % e, file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
