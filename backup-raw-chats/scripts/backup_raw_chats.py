#!/usr/bin/env python3
"""
backup_raw_chats.py

Collects and archives raw chat databases, transcripts, and session files from:
- OpenCode (~/.local/share/opencode)
- Claude (~/Library/Application Support/Claude/local-agent-mode-sessions)
- Antigravity / AGI (~/.gemini/antigravity and ~/.gemini/antigravity-cli)
- Codex / ChatGPT Codex (~/.codex)

Preserves exact raw format without preprocessing or loss of data, packing them
into compressed ZIP archives with metadata manifests.
"""

import argparse
import datetime
import glob
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path


def format_bytes(size: int) -> str:
    """Format bytes into human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def sha256_file(filepath: str) -> str:
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def get_opencode_files() -> list[tuple[str, str]]:
    """
    Returns list of (absolute_source_path, relative_archive_path) for OpenCode.
    """
    files: list[tuple[str, str]] = []
    base_share = os.path.expanduser("~/.local/share/opencode")
    base_state = os.path.expanduser("~/.local/state/opencode")

    # opencode.db and sqlite wal/shm files
    for p in glob.glob(os.path.join(base_share, "opencode.db*")):
        if os.path.isfile(p):
            rel = os.path.join("opencode", "data", os.path.basename(p))
            files.append((p, rel))

    # storage subfolder
    storage_dir = os.path.join(base_share, "storage")
    if os.path.isdir(storage_dir):
        for root, _, filenames in os.walk(storage_dir):
            for fn in filenames:
                fp = os.path.join(root, fn)
                rel = os.path.join("opencode", "storage", os.path.relpath(fp, storage_dir))
                files.append((fp, rel))

    # state logs (prompt history, frecency)
    for name in ["prompt-history.jsonl", "frecency.jsonl"]:
        p = os.path.join(base_state, name)
        if os.path.isfile(p):
            rel = os.path.join("opencode", "state", name)
            files.append((p, rel))

    return sorted(files)


def get_claude_files() -> list[tuple[str, str]]:
    """
    Returns list of (absolute_source_path, relative_archive_path) for Claude.
    """
    files: list[tuple[str, str]] = []
    app_support = os.path.expanduser("~/Library/Application Support/Claude")

    # Local agent mode sessions (audit.jsonl, local_*.json, task artifacts)
    agent_sessions = os.path.join(app_support, "local-agent-mode-sessions")
    if os.path.isdir(agent_sessions):
        for root, _, filenames in os.walk(agent_sessions):
            for fn in filenames:
                fp = os.path.join(root, fn)
                rel = os.path.join("claude", "local-agent-mode-sessions", os.path.relpath(fp, agent_sessions))
                files.append((fp, rel))

    # Claude code sessions
    code_sessions = os.path.join(app_support, "claude-code-sessions")
    if os.path.isdir(code_sessions):
        for root, _, filenames in os.walk(code_sessions):
            for fn in filenames:
                fp = os.path.join(root, fn)
                rel = os.path.join("claude", "claude-code-sessions", os.path.relpath(fp, code_sessions))
                files.append((fp, rel))

    # Global config
    claude_json = os.path.expanduser("~/.claude.json")
    if os.path.isfile(claude_json):
        files.append((claude_json, os.path.join("claude", "config", "claude.json")))

    return sorted(files)


def get_antigravity_files() -> list[tuple[str, str]]:
    """
    Returns list of (absolute_source_path, relative_archive_path) for Antigravity (AGI / Agy).
    """
    files: list[tuple[str, str]] = []
    targets = [
        ("~/.gemini/antigravity", "antigravity-ide"),
        ("~/.gemini/antigravity-cli", "antigravity-cli"),
    ]

    for base_path, prefix in targets:
        exp_base = os.path.expanduser(base_path)
        if not os.path.isdir(exp_base):
            continue

        # Conversations SQLite databases (*.db, *.db-wal, *.db-shm)
        conv_dir = os.path.join(exp_base, "conversations")
        if os.path.isdir(conv_dir):
            for p in glob.glob(os.path.join(conv_dir, "*.db*")):
                if os.path.isfile(p):
                    rel = os.path.join("antigravity", prefix, "conversations", os.path.basename(p))
                    files.append((p, rel))

        # Summaries databases
        for p in glob.glob(os.path.join(exp_base, "conversation_summaries.db*")):
            if os.path.isfile(p):
                rel = os.path.join("antigravity", prefix, os.path.basename(p))
                files.append((p, rel))

        # History log
        history_file = os.path.join(exp_base, "history.jsonl")
        if os.path.isfile(history_file):
            rel = os.path.join("antigravity", prefix, "history.jsonl")
            files.append((history_file, rel))

        # Transcripts and plan documents from brain directory
        brain_dir = os.path.join(exp_base, "brain")
        if os.path.isdir(brain_dir):
            # Transcripts
            for p in glob.glob(os.path.join(brain_dir, "*", ".system_generated", "logs", "transcript*.jsonl")):
                if os.path.isfile(p):
                    conv_id = Path(p).parent.parent.parent.name
                    rel = os.path.join("antigravity", prefix, "transcripts", conv_id, os.path.basename(p))
                    files.append((p, rel))

            # Markdown plans and walkthroughs
            for p in glob.glob(os.path.join(brain_dir, "*", "*.md")):
                if os.path.isfile(p):
                    conv_id = Path(p).parent.name
                    rel = os.path.join("antigravity", prefix, "artifacts", conv_id, os.path.basename(p))
                    files.append((p, rel))

    return sorted(files)


def get_codex_files() -> list[tuple[str, str]]:
    """
    Returns list of (absolute_source_path, relative_archive_path) for Codex / ChatGPT Codex.
    """
    files: list[tuple[str, str]] = []
    base_codex = os.path.expanduser("~/.codex")
    if not os.path.isdir(base_codex):
        return files

    # Sessions rollouts
    sessions_dir = os.path.join(base_codex, "sessions")
    if os.path.isdir(sessions_dir):
        for root, _, filenames in os.walk(sessions_dir):
            for fn in filenames:
                if fn.endswith(".jsonl"):
                    fp = os.path.join(root, fn)
                    rel = os.path.join("codex", "sessions", os.path.relpath(fp, sessions_dir))
                    files.append((fp, rel))

    # Archived sessions rollouts
    archived_dir = os.path.join(base_codex, "archived_sessions")
    if os.path.isdir(archived_dir):
        for fn in os.listdir(archived_dir):
            if fn.endswith(".jsonl"):
                fp = os.path.join(archived_dir, fn)
                rel = os.path.join("codex", "archived_sessions", fn)
                files.append((fp, rel))

    # SQLite thread history and session index
    for p in glob.glob(os.path.join(base_codex, "thread_history_*.sqlite*")):
        if os.path.isfile(p):
            rel = os.path.join("codex", "database", os.path.basename(p))
            files.append((p, rel))

    session_index = os.path.join(base_codex, "session_index.jsonl")
    if os.path.isfile(session_index):
        rel = os.path.join("codex", "session_index.jsonl")
        files.append((session_index, rel))

    return sorted(files)


COLLECTORS = {
    "opencode": ("OpenCode", get_opencode_files),
    "claude": ("Claude", get_claude_files),
    "antigravity": ("Antigravity (AGI)", get_antigravity_files),
    "codex": ("Codex / ChatGPT", get_codex_files),
}


def build_manifest(file_list: list[tuple[str, str]]) -> str:
    """Build a manifest string with original paths, archive paths, sizes, and timestamps."""
    lines = [
        "# AI Chats Raw Backup Manifest",
        f"# Generated: {datetime.datetime.now().isoformat()}",
        f"# Total Files: {len(file_list)}",
        "# -----------------------------------------------------------------------------",
        "# Archive Path | Source Path | Size (Bytes) | Last Modified",
        "# -----------------------------------------------------------------------------",
    ]
    for src, arc in file_list:
        try:
            stat = os.stat(src)
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            lines.append(f"{arc}\t{src}\t{stat.st_size}\t{mtime}")
        except Exception as e:
            lines.append(f"{arc}\t{src}\tERROR: {e}")
    return "\n".join(lines) + "\n"


def create_zip(zip_path: str, file_list: list[tuple[str, str]], assistant_name: str) -> None:
    """Create a compressed zip file from the list of files."""
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)
    manifest_content = build_manifest(file_list)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Add manifest
        zf.writestr("MANIFEST.txt", manifest_content)

        # Add files
        for src, arc in file_list:
            if os.path.isfile(src):
                zf.write(src, arcname=arc)


def main():
    parser = argparse.ArgumentParser(
        description="Backup raw chat databases and transcripts from OpenCode, Claude, Antigravity, and Codex."
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=os.path.expanduser("~/ai_chats_raw_backup"),
        help="Target directory to save the zip files (default: ~/ai_chats_raw_backup)",
    )
    parser.add_argument(
        "-a", "--assistants",
        default="opencode,claude,antigravity,codex",
        help="Comma-separated list of assistants to backup: opencode,claude,antigravity,codex,all",
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        help="Create a single combined zip containing all selected assistants.",
    )
    parser.add_argument(
        "--separate",
        action="store_true",
        help="Create separate zip files for each assistant (default behavior).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show files and sizes without creating zip files.",
    )

    args = parser.parse_args()

    # Determine which assistants to include
    if "all" in [x.strip().lower() for x in args.assistants.split(",")]:
        selected_keys = list(COLLECTORS.keys())
    else:
        selected_keys = [x.strip().lower() for x in args.assistants.split(",") if x.strip().lower() in COLLECTORS]

    if not selected_keys:
        print("Error: No valid assistants selected. Choose from: opencode, claude, antigravity, codex, all", file=sys.stderr)
        sys.exit(1)

    # By default, create separate zips unless only --combined is specified
    do_separate = args.separate or (not args.combined)
    do_combined = args.combined

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.abspath(args.output_dir)

    print("=================================================================")
    print(" 📦 AI CHATS RAW BACKUP PIPELINE")
    print(f" Timestamp:  {timestamp}")
    print(f" Output Dir: {out_dir}")
    print(f" Assistants: {', '.join([COLLECTORS[k][0] for k in selected_keys])}")
    print(f" Mode:       {'DRY RUN' if args.dry_run else 'ACTIVE BACKUP'}")
    print("=================================================================\n")

    all_files: list[tuple[str, str]] = []
    summary_stats = []

    for key in selected_keys:
        name, collector_fn = COLLECTORS[key]
        files = collector_fn()
        total_size = sum(os.path.getsize(f[0]) for f in files if os.path.isfile(f[0]))
        summary_stats.append((key, name, len(files), total_size, files))
        all_files.extend(files)

        print(f"▶ {name}:")
        print(f"  • Files found: {len(files):,}")
        print(f"  • Total raw size: {format_bytes(total_size)}")

    grand_total_size = sum(s[3] for s in summary_stats)
    print("\n-----------------------------------------------------------------")
    print(f"Total raw chat files to archive: {len(all_files):,} ({format_bytes(grand_total_size)})")
    print("-----------------------------------------------------------------\n")

    if args.dry_run:
        print("[DRY RUN] No zip files were created.")
        return

    os.makedirs(out_dir, exist_ok=True)
    created_archives = []

    # 1. Create separate archives
    if do_separate:
        for key, name, count, raw_size, files in summary_stats:
            if not files:
                print(f"Skipping {name}: no files to archive.")
                continue

            zip_filename = f"{key}_chats_raw_{timestamp}.zip"
            zip_dest = os.path.join(out_dir, zip_filename)
            print(f"Creating {zip_filename} ...", end="", flush=True)

            t0 = datetime.datetime.now()
            create_zip(zip_dest, files, name)
            elapsed = (datetime.datetime.now() - t0).total_seconds()
            zip_size = os.path.getsize(zip_dest)

            created_archives.append((zip_filename, zip_dest, count, raw_size, zip_size, elapsed))
            print(f" Done! ({format_bytes(zip_size)}, {elapsed:.2f}s)")

    # 2. Create combined archive
    if do_combined and all_files:
        zip_filename = f"all_ai_chats_raw_{timestamp}.zip"
        zip_dest = os.path.join(out_dir, zip_filename)
        print(f"Creating combined archive {zip_filename} ...", end="", flush=True)

        t0 = datetime.datetime.now()
        create_zip(zip_dest, all_files, "All Assistants")
        elapsed = (datetime.datetime.now() - t0).total_seconds()
        zip_size = os.path.getsize(zip_dest)

        created_archives.append((zip_filename, zip_dest, len(all_files), grand_total_size, zip_size, elapsed))
        print(f" Done! ({format_bytes(zip_size)}, {elapsed:.2f}s)")

    # Print summary
    print("\n=================================================================")
    print(" ✅ BACKUP COMPLETED SUCCESSFULLY")
    print("=================================================================")
    for fname, fpath, count, r_size, z_size, dur in created_archives:
        ratio = (1.0 - (z_size / r_size)) * 100.0 if r_size > 0 else 0
        print(f"📁 {fname}")
        print(f"   Location:    {fpath}")
        print(f"   Files:       {count:,}")
        print(f"   Raw Size:    {format_bytes(r_size)}")
        print(f"   Zip Size:    {format_bytes(z_size)} (saved {ratio:.1f}%)")
        print(f"   Time taken:  {dur:.2f}s\n")


if __name__ == "__main__":
    main()
