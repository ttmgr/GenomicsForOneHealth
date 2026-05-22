# Claude Code adapter

This adapter wires the project-agnostic harness (`agent_skills/core/`) into Claude
Code. It is the only Claude-specific part of the pack; everything it relies on
(`core/hooks/`, `core/AGENTS.md`, `core/memory/`) is portable.

## What it contains

- `CLAUDE.md` — Claude Code operating rules over the agnostic `core/AGENTS.md`
  contract, including how the harness memory store maps onto Claude Code's native
  `MEMORY.md` + per-fact memory convention.
- `settings.hooks.sample.json` — a sample `.claude/settings.json` fragment showing
  how to surface the harness rules and keep the offline checks green. Copy the keys
  you want into the target project's `.claude/settings.json`; it is a template, not
  an active config.

## Installing in another project

The harness core has no dependency on this repository's content, so lifting it is a
copy plus three small wirings:

1. Copy `agent_skills/core/` and `agent_skills/adapters/` into the target repo
   (keep the `agent_skills/` package path so `from agent_skills.core.hooks import …`
   resolves, or adjust imports to your package root).
2. Add the target repo's own skill YAMLs under `agent_skills/skills/` and any
   project-specific parsers/validators under `agent_skills/project/hooks/`. The core
   never imports the project layer, so it works with an empty project layer too.
3. Create a memory directory (e.g. `agent_skills/memory/`) seeded with a `MEMORY.md`
   index per `core/memory/README.md`, and point `audit.append_run_record` at it.

Then merge `settings.hooks.sample.json` into the target's `.claude/settings.json`
and adapt `CLAUDE.md`'s project-routing references.
