# Prompt: extract a new skill from documentation

Use this prompt to turn newly added workflow documentation (a README, a set of
scripts, or a manual-execution section) into a new YAML skill in
`agent_skills/skills/`. Derive everything from the documentation; invent nothing.

## Steps

1. Read the new documentation and every script it references, in full. Do not
   summarize from memory.
2. Extract, verbatim:
   - the tools invoked (with version pins from the repository's env files);
   - every command, with its exact flags and arguments;
   - input and output file types;
   - required databases and reference resources;
   - caveats, limitations, and troubleshooting notes.
3. Create a YAML file that conforms to `agent_skills/schemas/skill.schema.json`.
   Fill every required field. Use `{placeholder}` only for values that vary per
   run, and declare each placeholder under `parameters` (mark `required` and give a
   documented `default` only when the source documents one). Escape any literal
   shell braces (for example in `awk`) by doubling them: `{{` and `}}`.
4. Set `source_files` to every repository-relative file the skill is derived from.
5. Add `external_references` only if you used an upstream Nanopore/EPI2ME source for
   comparison, and record the comparison in `external_reference_notes`. Never copy
   upstream commands into `command_templates`.
6. Set `needs_review` to a list of specific notes whenever a command is partial,
   ambiguous, conflicts with another source, or could not be confirmed. If a
   command is not documented at all, do not invent it: add a TODO note in
   `needs_review` with the source context instead.
7. Reference the relevant `pre_hooks`, `post_hooks`, and `validation_hooks` from the
   `hooks/` package; add a new hook only if an existing one does not fit.
8. Update the schema if the new skill needs a field the schema lacks.
9. Add an eval task to `agent_skills/evals/benchmark_tasks.yaml` for the new skill
   (at least: routing, missing-input detection, command building).
10. Add a worked example under `agent_skills/examples/` if the workflow is a major
    one.

## Acceptance check

Run the `validate_skill.md` checklist against the new file before committing.
