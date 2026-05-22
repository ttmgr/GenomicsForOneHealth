# Agent instructions (agent-agnostic harness contract)

These rules apply to any coding agent (Codex, Cursor, Continue, and others) using
this harness, in any project. They are the portable contract; Claude Code has an
equivalent, Claude-specific file at `adapters/claude_code/CLAUDE.md`. Project-
specific routing lives in the project layer (here:
`project/prompts/use_skill_pack.md`).

1. Read the pack `README.md` first.
2. Read the relevant skill YAML (here, `skills/*.yaml`) for the task before acting.
3. Prefer declared skills over invented workflows. If no skill fits, say so.
4. Never invent unsupported parameters, tools, databases, or commands.
5. Validate inputs (the skill's `pre_hooks`, in `core/hooks/preflight.py`) before
   constructing commands.
6. Build commands only from a skill's declared `command_templates`, via
   `core/hooks/command_builder.py`. Supply only declared parameters.
7. Do not execute destructive commands without explicit user confirmation. The
   hooks build command strings; they do not run them.
8. Parse outputs using the declared `post_hooks` where available — generic parsers
   in `core/hooks/parsers.py`, project tool-specific parsers in the project hook
   layer (here, `project/hooks/parsers_genomics.py`).
9. Run the declared `validation_hooks` (generic in `core/hooks/validation.py`,
   project-specific in `project/hooks/validation_genomics.py`) and produce a
   caveated report that includes every raised flag.
10. Write an audit log (`core/hooks/audit.py`) for proposed or executed workflows,
    including `source_files` and `external_references`. Where the project keeps a
    memory store, distil the run with `audit.append_run_record` (see
    `core/memory/README.md`).
11. Treat all model outputs as suggestions, not biological, clinical, regulatory,
    or diagnostic conclusions.
12. Preserve traceability to the local source repository files (`source_files`).
13. Preserve traceability to external/upstream references where used
    (`external_references`).
14. If repository-derived behavior is ambiguous, surface the skill's `needs_review`
    notes instead of guessing.
15. If an external/upstream source conflicts with local documentation, keep the
    local behavior and flag the conflict; never substitute an upstream command for
    a local one. The local repository is the source of truth.

When editing or adding a skill, follow `core/prompts/extract_new_skill.md` and
update `source_files`, `external_references`, `external_reference_notes`, and
`needs_review`. Validate with `core/prompts/validate_skill.md`.
