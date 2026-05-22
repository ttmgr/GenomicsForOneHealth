# Harness memory (format spec)

This is the project-agnostic specification for the harness's durable memory. It
defines the *format*; the live memory store for a given repository lives
elsewhere (in this repo, at `agent_skills/memory/`). Drop the harness into any
project and point the agent at a memory directory shaped like this.

Memory is how the harness persists what is *not* recoverable from the code or
git history: architectural decisions, summaries of agent runs, and operator
preferences. It mirrors the Claude Code memory convention (one fact per file,
frontmatter, a single `MEMORY.md` index, `[[wikilinks]]`), so the Claude Code
adapter can map its native memory onto this store with no translation.

## Layout

```
<memory_dir>/
  MEMORY.md          index — one line per memory, loaded into context each session
  <slug>.md          one memory per file
```

`MEMORY.md` is the only file read in full at the start of a session; keep it to
one line per memory (`- [Title](file.md) — hook`) and never put memory content
in it.

## File format

Each memory is one file holding one fact, with frontmatter:

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary — used to decide relevance during recall>
metadata:
  type: decision | run | preference | reference
---

<the fact. Link related memories with [[their-name]].>
```

## Types

- **decision** — an architectural or design decision and its rationale. In this
  repo these mirror the ADRs under `adr/`; the memory file points to the ADR
  rather than duplicating it.
- **run** — a distilled summary of one agent-assisted workflow run: which skill,
  what it found, which validation flags were raised, which source files it was
  traceable to. Written automatically by
  `core/hooks/audit.append_run_record(memory_dir, skill_name, summary, ...)`,
  which also appends the `MEMORY.md` index line. The full machine-readable
  record stays in the JSON audit log (`audit.write_audit_log`); the memory file
  is the human-scannable distillation.
- **preference** — a durable operating preference or constraint the operator has
  stated (e.g. "commands are built, never executed without confirmation").
- **reference** — a pointer to an external resource (URL, dashboard, ticket).

## Recall

At the start of a task, read `MEMORY.md`, then open the memory files whose
`description` looks relevant. Treat recalled memories as background context that
reflects what was true when written — if a memory names a file, flag, or
threshold, verify it still exists before relying on it.

## Writing

Before saving, check for an existing file that already covers the fact and
update it rather than duplicating; delete memories that turn out to be wrong.
Do not save what the repository already records (code structure, git history,
skill YAMLs). After writing a file, add its one-line pointer to `MEMORY.md`.
