# Prompt: use the GenomicsForOneHealth skill pack

Use this repository as a coding-agent skill pack for One Health genomics
workflows. Read `agent_skills/README.md`, then inspect the relevant YAML skills in
`agent_skills/skills/`. Select the appropriate skill for the user's request,
validate inputs, build commands only from the skill's declared `command_templates`,
parse outputs where possible, run the declared validation hooks, and produce a
caveated report. Do not invent unsupported workflow behavior.

## Operating procedure

1. Route the request to a single skill by matching the user's molecule type
   (DNA/RNA), sample type, and goal against each skill's `domain`, `description`,
   and `supported_input_types`. If nothing fits, say so; do not force a match.
2. Load the skill with `hooks/command_builder.load_skill_yaml`.
3. Run the skill's `pre_hooks` (functions in `hooks/preflight.py`) against the
   user's actual inputs, databases, and tools. Report any failures and stop before
   building commands that would fail.
4. Validate parameters with `command_builder.validate_required_parameters`. If a
   required parameter is missing, ask for it. Never fill in a value the user did
   not provide, and never accept a parameter the skill does not declare.
5. Build commands with `command_builder.build_commands_for_skill`. Present the
   built command strings to the user. Do not execute destructive commands without
   explicit confirmation; the hooks build commands, they do not run them.
6. After the user runs a step (or provides outputs), parse results with the
   declared `post_hooks` (functions in `hooks/parsers.py`).
7. Run the declared `validation_hooks` (functions in `hooks/validation.py`) and
   include every raised flag in the report, with its severity.
8. Write an audit log with `hooks/audit.write_audit_log`, including the skill's
   `source_files` and `external_references`.
9. Produce a human-readable report: what was run, key parsed metrics, validation
   flags, and explicit caveats.

## Hard rules

- The local repository is the source of truth. Use only commands, parameters,
  tools, and databases that the selected skill declares.
- If repository-derived behavior is ambiguous, surface the skill's `needs_review`
  notes rather than guessing.
- Upstream EPI2ME / Nanopore references (in `agent_skills/references/`) are for
  comparison only; never substitute an upstream command for a local one.
- Treat all model outputs as suggestions, not biological, clinical, regulatory, or
  diagnostic conclusions. Say this in the report.
