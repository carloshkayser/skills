---
name: kanban
version: 1.0.0
description: >-
  Manage project tasks using a simple file-based Kanban system in markdown. Use when tracking tasks, creating task cards, listing board status (todo, doing, done), or handling task dependencies within a kanban/ directory.
---

# Kanban Skill

## Purpose

Manage project tasks using a simple file-based Kanban system.

All tasks must be stored inside a `kanban/` directory. Each task must be represented by its own Markdown (`.md`) file.

## Directory Structure

```text
kanban/
├── task1.md
├── task2.md
└── task3.md
```

## Task Format

Every task file must begin with YAML front matter containing the following fields:

```yaml
---
title: Task title
status: todo
depend: task1.md, task2.md
---
```

After the front matter, the task body must be written in Markdown.

Example:

```markdown
---
title: Lorem
status: todo
depend: task1.md, task2.md
---

# Lorem

Lorem ipsum dolor sit amet.
```

## Fields

### `title`

A short, human-readable name for the task.

Example:

```yaml
title: Implement authentication
```

### `status`

The current Kanban state of the task.

Allowed values:

- `todo` — the task has not started yet.
- `doing` — the task is currently being worked on.
- `done` — the task has been completed.

Example:

```yaml
status: doing
```

### `depend`

A comma-separated list of task filenames that must be completed before this task can be considered unblocked.

Example:

```yaml
depend: database.md, api.md
```

If the task has no dependencies, use an empty value:

```yaml
depend:
```

## Rules

1. Store every task as a separate `.md` file inside the `kanban/` directory.
2. Use only `todo`, `doing`, or `done` as the task status.
3. Dependencies must reference filenames that exist inside the same `kanban/` directory.
4. A task is blocked when at least one file listed in `depend` has a status other than `done`.
5. Before changing a task to `doing`, check whether all of its dependencies are `done`.
6. Before changing a task to `done`, ensure the work described in the task body is complete.
7. When creating a new task, use a short, descriptive, lowercase filename with hyphens when needed.

Example:

```text
implement-authentication.md
```

8. Do not rename or delete a task file without updating every `depend` field that references it.
9. Preserve existing task notes and history when updating status or dependencies unless explicitly asked to rewrite them.

## Creating a Task

When creating a new task:

1. Choose a descriptive filename.
2. Create the file inside `kanban/`.
3. Add the required YAML front matter.
4. Set the initial status to `todo` unless another status is explicitly requested.
5. Add dependencies when applicable.
6. Write a clear Markdown description of the work to be completed.

Example:

```markdown
---
title: Build login endpoint
status: todo
depend: setup-database.md
---

# Build login endpoint

Create the API endpoint used to authenticate users.

## Acceptance Criteria

- Validate email and password.
- Return an authentication token on success.
- Return an appropriate error for invalid credentials.
```

## Updating a Task

When updating a task:

- Modify only the fields or content required by the requested change.
- Keep the YAML front matter valid.
- Keep dependency filenames synchronized with the files in `kanban/`.
- Verify dependencies before moving a task to `doing`.

## Listing the Board

When asked to show the Kanban board, read all `.md` files inside `kanban/` and group them by status:

```text
TODO
- task-a.md
- task-b.md

DOING
- task-c.md

DONE
- task-d.md
```

For each task, include its title and indicate when it is blocked by unfinished dependencies.

## Dependency Resolution

A dependency is satisfied only when the referenced task exists and has:

```yaml
status: done
```

If a dependency file is missing, treat the task as blocked and report the missing dependency.

Circular dependencies must be reported instead of silently accepted.

Example:

```text
task-a.md -> task-b.md -> task-a.md
```

## Expected Behavior

Use the files in `kanban/` as the source of truth for task state. Do not maintain a separate hidden representation of the board.

Whenever possible, make minimal edits to task files and keep the board consistent after every operation.
