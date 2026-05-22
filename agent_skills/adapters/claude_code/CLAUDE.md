# Claude Code adapter for the agent_skills harness

This file tells Claude Code how to operate the `agent_skills/` harness. It is the
Claude Code-specific layer over the agnostic contract in `core/AGENTS.md`; read
that contract first, then this. Project routing is in
`project/prompts/use_skill_pack.md`.

## Use the skills as the source of truth

- Use the YAML skills in `agent_skills/skills/` as the source of truth for how each
  workflow runs. Do not infer missing commands from general domain knowledge.
- Read the pack `README.md`, then `core/AGENTS.md`, then the relevant skill, before
  acting.
- The local repository is authoritative. External/upstream references (in
  `agent_skills/references/`) are for comparison only; never substitute an upstream
  command for a local one.

## Operating rules

1. Route the request to a single skill; if none fits, say so rather than forcing one.
2. Run the skill's `pre_hooks` (`core/hooks/preflight.py`) against the user's real
   inputs, databases, and tools before building commands.
3. Validate parameters with `command_builder.validate_required_parameters`. Ask for
   missing required parameters. Never fill an unprovided value, and never accept a
   parameter the skill does not declare.
4. Build commands with `command_builder.build_commands_for_skill`. Present them; do
   not execute destructive commands without explicit confirmation.
5. Parse outputs with the declared `post_hooks` — generic in `core/hooks/parsers.py`,
   project tool-specific in `project/hooks/parsers_genomics.py`. (The legacy facade
   `agent_skills.hooks.parsers` still works and re-exports both.)
6. Run the declared `validation_hooks` (`core/hooks/validation.py` +
   `project/hooks/validation_genomics.py`) and report every flag.
7. Write an audit log (`core/hooks/audit.py`) including `source_files` and
   `external_references`, and distil the run into memory with
   `audit.append_run_record('agent_skills/memory', skill_name, summary, ...)`.
8. Treat outputs as suggestions, not biological, clinical, regulatory, or diagnostic
   conclusions.

## Memory

The harness memory store lives at `agent_skills/memory/` (format spec:
`core/memory/README.md`). It maps directly onto Claude Code's native memory
convention — `MEMORY.md` index plus one fact per file with frontmatter — so you can
read and write it the same way you handle `~/.claude` memory: read `MEMORY.md` at
the start of a task, open the relevant fact files, and add a pointer line when you
write a new memory. `append_run_record` handles `type: run` entries automatically.

## When editing or adding skills

- Do not overwrite source docs unless explicitly asked.
- Prefer small, traceable changes.
- Keep `source_files`, `external_references`, `external_reference_notes`, and
  `needs_review` up to date; escape literal shell braces (e.g. `awk`) as `{{`/`}}`.
- Follow `core/prompts/extract_new_skill.md` to add a skill and
  `core/prompts/validate_skill.md` to check it. Run
  `python agent_skills/evals/run_benchmarks.py` after changes.

## Installing this adapter in another project

See `adapters/claude_code/README.md` for wiring the harness into a different
repository's `.claude/` (settings hooks + memory directory).
