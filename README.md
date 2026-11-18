# Custom Agent Skills

Personal repository of custom skills for AI coding agents (compatible with the Agent Skills specification).

## Installation

Install a single skill:

```bash
npx skills add https://github.com/carloshkayser/skills --skill <skill-name>
```

Or list and choose from every skill in the repository:

```bash
npx skills add https://github.com/carloshkayser/skills
```

The `research-notebook` and `experiment-runner` skills are designed to work together: install both for hypothesis tracking plus reproducible, commit-linked experiment runs.

## Skills Catalog & Attribution

| Skill | Version | Purpose |
|---|---|---|
| [`paper-draft-writer`](#1-paper-draft-writer) | `1.0.0` | Evidence-grounded academic paper drafts |
| [`backup-raw-chats`](#2-backup-raw-chats) | `1.0.0` | Raw AI chat backups into ZIP files |
| [`kanban`](#3-kanban) | `1.0.0` | File-based Kanban task tracking |
| [`research-notebook`](#4-research-notebook) | `1.0.0` | Hypotheses and evidence across sessions |
| [`experiment-runner`](#5-experiment-runner) | `1.0.0` | Reproducible, commit-linked experiment runs |

---

### 1. `paper-draft-writer`
- **Version**: `1.0.0`
- **Description**: Generates complete, evidence-grounded academic paper drafts from an annotated bibliography, structured outline, and argument blueprint.
- **Path**: [`paper-draft-writer/`](./paper-draft-writer/)
- **Install**:
  ```bash
  npx skills add https://github.com/carloshkayser/skills --skill paper-draft-writer
  ```
- **Credits & Attribution**:
  - Adapted from: [`academic-paper/agents/draft_writer_agent.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper/agents/draft_writer_agent.md)
  - Original Repository: [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills)

---

### 2. `backup-raw-chats`
- **Version**: `1.0.0`
- **Description**: Archives and packages raw conversation databases, transcripts, and session files from OpenCode, Claude, Antigravity (AGI / Agy), and Codex directly into compressed ZIP files without preprocessing.
- **Path**: [`backup-raw-chats/`](./backup-raw-chats/)
- **Install**:
  ```bash
  npx skills add https://github.com/carloshkayser/skills --skill backup-raw-chats
  ```

---

### 3. `kanban`
- **Version**: `1.0.0`
- **Description**: Manages project tasks and workflows using a simple file-based Kanban system in Markdown with dependency tracking (`todo`, `doing`, `done`).
- **Path**: [`kanban/`](./kanban/)
- **Install**:
  ```bash
  npx skills add https://github.com/carloshkayser/skills --skill kanban
  ```

---

### 4. `research-notebook`
- **Version**: `1.0.0`
- **Description**: Preserves investigation evidence, falsifiable hypotheses, experiment attempts, and results across agent sessions in a canonical `HYPOTHESES.md` notebook to prevent repeating already-evaluated approaches.
- **Path**: [`research-notebook/`](./research-notebook/)
- **Install**:
  ```bash
  npx skills add https://github.com/carloshkayser/skills --skill research-notebook
  ```

---

### 5. `experiment-runner`
- **Version**: `1.0.0`
- **Description**: Runs experiments reproducibly: requires a clean (committed) working tree before every run, logs the commit hash, command, environment, and results in an append-only `experiments/` log, and links each run to its `research-notebook` hypothesis and attempt. Requires `git` and Python 3.8+.
- **Path**: [`experiment-runner/`](./experiment-runner/)
- **Install**:
  ```bash
  npx skills add https://github.com/carloshkayser/skills --skill experiment-runner
  ```

## License

Released under the [MIT License](./LICENSE).
