# Claude Code instructions for this skill pack

This file tells Claude Code how to operate the `agent_skills/` pack. It mirrors the
agent-agnostic rules in `agent_skills/AGENTS.md`, with Claude Code specifics.

## Use the skills as the source of truth

- Use the YAML skills in `agent_skills/skills/` as the source of truth for how each
  workflow runs. Do not infer missing commands from general bioinformatics
  knowledge.
- Read `agent_skills/README.md`, then the relevant skill, before acting.
- The local repository is authoritative. Upstream Nanopore/EPI2ME references (in
  `agent_skills/references/`) are for comparison only; never substitute an upstream
  command for a local one.

## Operating rules

1. Route the request to a single skill; if none fits, say so rather than forcing one.
2. Run the skill's `pre_hooks` (`hooks/preflight.py`) against the user's real inputs,
   databases, and tools before building commands.
3. Validate parameters with `command_builder.validate_required_parameters`. Ask for
   missing required parameters. Never fill an unprovided value, and never accept a
   parameter the skill does not declare.
4. Build commands with `command_builder.build_commands_for_skill`. Present them; do
   not execute destructive commands without explicit confirmation.
5. Parse outputs with the declared `post_hooks` (`hooks/parsers.py`).
6. Run the declared `validation_hooks` (`hooks/validation.py`) and report every flag.
7. Write an audit log (`hooks/audit.py`) including `source_files` and
   `external_references`.
8. Treat outputs as suggestions, not biological, clinical, regulatory, or diagnostic
   conclusions.

## When editing or adding skills

- Do not overwrite source docs unless explicitly asked.
- Prefer small, traceable changes.
- Keep `source_files`, `external_references`, `external_reference_notes`, and
  `needs_review` up to date; escape literal shell braces (e.g. `awk`) as `{{`/`}}`.
- Follow `prompts/extract_new_skill.md` to add a skill and `prompts/validate_skill.md`
  to check it. Run `python agent_skills/evals/run_benchmarks.py` after changes.
