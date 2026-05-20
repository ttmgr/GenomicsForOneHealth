# Agent instructions (agent-agnostic)

These rules apply to any coding agent (Codex, Cursor, Continue, and others) using
this skill pack. Claude Code has an equivalent file at `agent_skills/CLAUDE.md`.

1. Read `agent_skills/README.md` first.
2. Read the relevant `agent_skills/skills/*.yaml` for the task before acting.
3. Prefer declared skills over invented workflows. If no skill fits, say so.
4. Never invent unsupported parameters, tools, databases, or commands.
5. Validate inputs (the skill's `pre_hooks`, in `hooks/preflight.py`) before
   constructing commands.
6. Build commands only from a skill's declared `command_templates`, via
   `hooks/command_builder.py`. Supply only declared parameters.
7. Do not execute destructive commands without explicit user confirmation. The
   hooks build command strings; they do not run them.
8. Parse outputs using the declared `post_hooks` (`hooks/parsers.py`) where
   available.
9. Run the declared `validation_hooks` (`hooks/validation.py`) and produce a
   caveated report that includes every raised flag.
10. Write an audit log (`hooks/audit.py`) for proposed or executed workflows,
    including `source_files` and `external_references`.
11. Treat all model outputs as suggestions, not biological, clinical, regulatory,
    or diagnostic conclusions.
12. Preserve traceability to the local source repository files (`source_files`).
13. Preserve traceability to external upstream references where used
    (`external_references`, `references/external_nanopore_epi2me_inventory.md`).
14. If repository-derived behavior is ambiguous, surface the skill's `needs_review`
    notes instead of guessing.
15. If upstream Nanopore/EPI2ME sources conflict with local documentation, keep the
    local behavior and flag the conflict; never substitute an upstream command for
    a local one.

When editing or adding a skill, follow `prompts/extract_new_skill.md` and update
`source_files`, `external_references`, `external_reference_notes`, and
`needs_review`. Validate with `prompts/validate_skill.md`.
