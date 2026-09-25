---
name: backup-raw-chats
description: >-
  Archive and package raw chat databases, transcripts, and session files from OpenCode,
  Claude, Antigravity (AGI / Agy), and Codex directly into compressed ZIP archives.
  Use this skill whenever the user asks to save, export, or create zip files of raw chats
  from their AI coding assistants without preprocessing.
---

# Backup Raw AI Chats

This skill packages pristine, unmodified raw chat histories and databases from **OpenCode**, **Claude**, **Antigravity (AGI / Agy)**, and **Codex** into compressed `.zip` archives.

## When to Use This Skill

Activate this skill when:
- The user requests to save, backup, or export chats from **OpenCode**, **Claude**, or **Antigravity (AGI)**.
- The user specifically instructs **not to preprocess** the data and to keep the original raw files.
- The user asks to generate `.zip` archives of conversation databases and session files.

---

## 🚀 Execution Guide

Run the backup script directly using Python:

```bash
# Backup OpenCode, Claude, and Antigravity into individual ZIPs (default destination: ~/ai_chats_raw_backup)
python3 <skill-dir>/scripts/backup_raw_chats.py

# Custom output directory
python3 <skill-dir>/scripts/backup_raw_chats.py -o /path/to/destination

# Include all assistants (OpenCode, Claude, Antigravity, and Codex)
python3 <skill-dir>/scripts/backup_raw_chats.py -a all

# Create both individual assistant ZIPs and a combined master ZIP
python3 <skill-dir>/scripts/backup_raw_chats.py --combined

# Dry-run preview of files and sizes without creating ZIPs
python3 <skill-dir>/scripts/backup_raw_chats.py --dry-run
```

---

## 📁 Source Locations Discovered & Preserved

| Assistant | Storage Path | Archived Raw Content |
| :--- | :--- | :--- |
| **OpenCode** | `~/.local/share/opencode/`<br>`~/.local/state/opencode/` | • `opencode.db`, `opencode.db-wal`, `opencode.db-shm` (SQLite containing sessions, messages, parts)<br>• `prompt-history.jsonl`, `frecency.jsonl`<br>• `storage/` directory snapshots |
| **Claude** | `~/Library/Application Support/Claude/` | • `local-agent-mode-sessions/**` (full `audit.jsonl` transcripts, session JSON configs, tasks)<br>• `claude-code-sessions/**`<br>• `~/.claude.json` |
| **Antigravity (AGI / Agy)** | `~/.gemini/antigravity/`<br>`~/.gemini/antigravity-cli/` | • `conversations/*.db*` (full SQLite conversation databases)<br>• `conversation_summaries.db*` (session metadata catalog)<br>• `brain/*/.system_generated/logs/transcript*.jsonl` (line-by-line transcripts)<br>• `brain/*/*.md` (plans & walkthroughs)<br>• `history.jsonl` |
| **Codex** *(Optional)* | `~/.codex/` | • `sessions/**/rollout-*.jsonl` (chronological interaction logs)<br>• `archived_sessions/**/rollout-*.jsonl`<br>• `thread_history_*.sqlite*`, `session_index.jsonl` |

---

## 📦 Generated Archive Layout

The script generates timestamped ZIP archives with a built-in `MANIFEST.txt`:

```text
<output-dir>/
├── opencode_chats_raw_<timestamp>.zip
│   ├── MANIFEST.txt
│   ├── data/ (opencode.db, wal, shm)
│   ├── state/ (prompt-history.jsonl, frecency.jsonl)
│   └── storage/
├── claude_chats_raw_<timestamp>.zip
│   ├── MANIFEST.txt
│   ├── local-agent-mode-sessions/ (audit.jsonl, session JSONs, tasks)
│   └── config/claude.json
├── antigravity_chats_raw_<timestamp>.zip
│   ├── MANIFEST.txt
│   ├── antigravity-ide/ (conversations/*.db, summaries, transcripts, plans)
│   └── antigravity-cli/ (conversations/*.db, summaries, history)
└── all_ai_chats_raw_<timestamp>.zip    # Optional when --combined is passed
```

---

## 🔍 Verification Steps

After running the backup script:
1. Confirm that each requested `.zip` file exists in the destination folder.
2. Verify that zip file size is non-zero (typically 10MB to 50MB each).
3. Test archive integrity using standard unzip test:
   ```bash
   unzip -t <path-to-zip>
   ```
4. Check that `MANIFEST.txt` is present and lists all archived files.
